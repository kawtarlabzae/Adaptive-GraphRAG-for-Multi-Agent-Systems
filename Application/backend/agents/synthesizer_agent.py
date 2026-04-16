"""
Synthesizer Agent — Phase 1
Extracts entities and relationships from document chunks and writes
them to the Neo4j knowledge graph as a High-Fidelity Consensus Graph.
"""
import asyncio
import logging
import uuid
from typing import List, Dict

from .base import BaseAgent, EventEmitter
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)

# Pre-seeded viticulture knowledge for immediate graph population
SEED_NODES = [
    {"id": "anthocyanin",         "label": "Anthocyanin",             "type": "molecule",              "description": "Red/purple pigment responsible for grape colour and quality"},
    {"id": "temperature",         "label": "Temperature",             "type": "variable",              "description": "Ambient and canopy temperature (°C)"},
    {"id": "uv_radiation",        "label": "UV-B Radiation",          "type": "variable",              "description": "UV-B solar radiation (280–315 nm), promoter of flavonoid biosynthesis"},
    {"id": "water_deficit",       "label": "Water Deficit",           "type": "condition",             "description": "Soil moisture below optimal field capacity threshold"},
    {"id": "tannin",              "label": "Tannin",                  "type": "molecule",              "description": "Polyphenol compound contributing to wine structure and astringency"},
    {"id": "berry_development",   "label": "Berry Development",       "type": "process",               "description": "Three-phase grape berry growth from fruit set to harvest"},
    {"id": "photosynthesis",      "label": "Photosynthesis",          "type": "process",               "description": "Light-driven CO₂ fixation process; inhibited by extreme heat"},
    {"id": "vine_transpiration",  "label": "Vine Transpiration",      "type": "process",               "description": "Water vapour loss through stomata; coupled with photosynthesis"},
    {"id": "irrigation",          "label": "Irrigation",              "type": "process",               "description": "Controlled water delivery to vineyard soil"},
    {"id": "drip_irrigation",     "label": "Drip Irrigation",         "type": "technology",            "description": "Precision water delivery at soil level; pre-dawn application maximises efficiency"},
    {"id": "soil_moisture",       "label": "Soil Moisture",           "type": "variable",              "description": "Water content of soil as percentage of field capacity"},
    {"id": "heat_shock_proteins", "label": "Heat Shock Proteins",     "type": "molecule",              "description": "Molecular chaperones upregulated under thermal stress (HSP80)"},
    {"id": "brix",                "label": "Brix",                    "type": "metric",                "description": "Sugar content of grape juice (°Bx); primary harvest indicator"},
    {"id": "canopy_management",   "label": "Canopy Management",       "type": "process",               "description": "Viticultural practice controlling vine architecture and microclimate"},
    {"id": "anthocyanin_degradation", "label": "Anthocyanin Degradation", "type": "process",          "description": "Thermal breakdown of anthocyanin molecules above 42°C"},
    {"id": "berry_quality_index", "label": "Berry Quality Index",     "type": "metric",                "description": "Composite score of colour, sugar, acid and phenolic content"},
    {"id": "vineyard_microclimate","label": "Vineyard Microclimate",  "type": "condition",             "description": "Local temperature, humidity and radiation environment within vine rows"},
    {"id": "root_system",         "label": "Root System",             "type": "biological_component",  "description": "Vine root network supplying water and nutrients from soil"},
    {"id": "veraison",            "label": "Véraison",                "type": "process",               "description": "Phenological stage when berries soften and begin accumulating sugars and pigments"},
]

SEED_EDGES = [
    {"from": "temperature",       "to": "anthocyanin",          "type": "AFFECTS",         "weight": 0.92, "condition": "T > 35°C",              "hard": False},
    {"from": "uv_radiation",      "to": "anthocyanin",          "type": "PROMOTES",        "weight": 0.78, "condition": "UV-B index > 8",         "hard": False},
    {"from": "water_deficit",     "to": "tannin",               "type": "CAUSES",          "weight": 0.81, "condition": "soil moisture < 25%",    "hard": False},
    {"from": "temperature",       "to": "photosynthesis",       "type": "INHIBITS",        "weight": 0.89, "condition": "T > 40°C",              "hard": True},
    {"from": "irrigation",        "to": "soil_moisture",        "type": "CONTROLS",        "weight": 0.95, "condition": None,                    "hard": False},
    {"from": "soil_moisture",     "to": "berry_development",    "type": "AFFECTS",         "weight": 0.74, "condition": "40–60% field capacity",  "hard": False},
    {"from": "temperature",       "to": "heat_shock_proteins",  "type": "INDUCES",         "weight": 0.88, "condition": "T > 38°C",              "hard": False},
    {"from": "vine_transpiration","to": "temperature",          "type": "INCREASES_WITH",  "weight": 0.86, "condition": None,                    "hard": False},
    {"from": "canopy_management", "to": "vineyard_microclimate","type": "CONTROLS",        "weight": 0.82, "condition": "dense canopy",           "hard": False},
    {"from": "drip_irrigation",   "to": "soil_moisture",        "type": "PROMOTES",        "weight": 0.91, "condition": "pre-dawn application",   "hard": False},
    {"from": "berry_development",  "to": "brix",                "type": "PRODUCES",        "weight": 0.82, "condition": "véraison onwards",       "hard": False},
    {"from": "anthocyanin",       "to": "berry_quality_index",  "type": "DETERMINES",      "weight": 0.88, "condition": None,                    "hard": False},
    {"from": "temperature",       "to": "anthocyanin_degradation","type":"CAUSES",         "weight": 0.85, "condition": "T > 42°C sustained",    "hard": True},
    {"from": "anthocyanin_degradation","to":"berry_quality_index","type":"INHIBITS",        "weight": 0.90, "condition": None,                    "hard": False},
    {"from": "water_deficit",     "to": "brix",                 "type": "PROMOTES",        "weight": 0.71, "condition": "mild stress only",       "hard": False},
    {"from": "vineyard_microclimate","to":"anthocyanin",         "type": "AFFECTS",         "weight": 0.68, "condition": None,                    "hard": False},
    {"from": "root_system",       "to": "vine_transpiration",   "type": "CONTROLS",        "weight": 0.87, "condition": None,                    "hard": False},
    {"from": "veraison",          "to": "anthocyanin",          "type": "PROMOTES",        "weight": 0.94, "condition": "temperature < 35°C",     "hard": False},
    {"from": "photosynthesis",    "to": "berry_development",    "type": "REQUIRES",        "weight": 0.95, "condition": None,                    "hard": True},
    {"from": "heat_shock_proteins","to":"anthocyanin",           "type": "INHIBITS",        "weight": 0.76, "condition": "resource competition",   "hard": False},
]


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"
    display_name = "Synthesizer Agent"
    phase = 1
    icon = "🔬"

    async def run(self, chunks: List[str], session_id: str, **kwargs):
        await self.started()
        await self.thinking("Loading domain knowledge and initialising graph construction…")
        await self._sleep(0.8)

        neo4j = get_neo4j()
        ollama = get_ollama()

        # ----------------------------------------------------------------
        # Step 1: Seed base viticulture knowledge graph
        # ----------------------------------------------------------------
        await self.thinking(f"Seeding {len(SEED_NODES)} domain entities into knowledge graph…")
        for i, node in enumerate(SEED_NODES):
            neo4j.create_node(
                node_id=node["id"],
                label=node["label"],
                node_type=node["type"],
                description=node["description"],
                confidence=1.0,
                session_id=session_id,
            )
            self.stats["nodes_added"] += 1
            await self.emit("agent.node_added", {
                "node": {
                    "id": node["id"],
                    "label": node["label"],
                    "type": node["type"],
                    "description": node["description"],
                    "confidence": 1.0,
                }
            })
            await self.progress(i / len(SEED_NODES) * 0.3, f"Seeding node: {node['label']}")
            await self._sleep(0.15)

        await self.thinking(f"Adding {len(SEED_EDGES)} causal edges to graph…")
        for i, edge in enumerate(SEED_EDGES):
            eid = neo4j.create_edge(
                from_id=edge["from"],
                to_id=edge["to"],
                rel_type=edge["type"],
                weight=edge["weight"],
                condition=edge["condition"],
                is_hard_edge=edge.get("hard", False),
                session_id=session_id,
            )
            self.stats["edges_added"] += 1
            await self.emit("agent.edge_added", {
                "edge": {
                    "id": eid,
                    "from_node": edge["from"],
                    "to_node": edge["to"],
                    "type": edge["type"],
                    "weight": edge["weight"],
                    "condition": edge["condition"],
                    "is_hard_edge": edge.get("hard", False),
                }
            })
            await self._sleep(0.12)

        await self.progress(0.35, "Domain knowledge seeded")
        await self._sleep(0.5)

        # ----------------------------------------------------------------
        # Step 2: Extract additional knowledge from uploaded documents
        # ----------------------------------------------------------------
        if chunks:
            await self.thinking(f"Extracting entities and relationships from {len(chunks)} document chunk(s)…")
            for idx, chunk in enumerate(chunks[:8]):   # limit to 8 chunks for demo speed
                if self._cancelled:
                    break
                await self.progress(0.35 + (idx / min(len(chunks), 8)) * 0.6,
                                    f"Synthesising chunk {idx + 1}/{min(len(chunks), 8)}")
                await self.thinking(f"Parsing chunk {idx + 1}: extracting novel entities…")
                await self._sleep(0.4)

                extracted = await ollama.extract_graph(chunk, model=self.model)
                entities = extracted.get("entities", [])
                relationships = extracted.get("relationships", [])

                for ent in entities:
                    eid = ent.get("id", str(uuid.uuid4())[:8])
                    # Skip if already exists
                    if neo4j.node_exists(eid, session_id):
                        continue
                    neo4j.create_node(
                        node_id=eid,
                        label=ent.get("label", eid),
                        node_type=ent.get("type", "entity"),
                        description=ent.get("description", ""),
                        confidence=0.9,
                        session_id=session_id,
                    )
                    self.stats["nodes_added"] += 1
                    await self.emit("agent.node_added", {
                        "node": {
                            "id": eid,
                            "label": ent.get("label", eid),
                            "type": ent.get("type", "entity"),
                            "description": ent.get("description", ""),
                            "confidence": 0.9,
                        }
                    })
                    await self._sleep(0.1)

                for rel in relationships:
                    from_id = rel.get("from_id", "")
                    to_id = rel.get("to_id", "")
                    if not from_id or not to_id:
                        continue
                    # Ensure both endpoints exist
                    if not neo4j.node_exists(from_id, session_id):
                        continue
                    if not neo4j.node_exists(to_id, session_id):
                        continue
                    eid = neo4j.create_edge(
                        from_id=from_id,
                        to_id=to_id,
                        rel_type=rel.get("type", "AFFECTS"),
                        weight=float(rel.get("weight", 0.8)),
                        condition=rel.get("condition"),
                        session_id=session_id,
                    )
                    self.stats["edges_added"] += 1
                    await self.emit("agent.edge_added", {
                        "edge": {
                            "id": eid,
                            "from_node": from_id,
                            "to_node": to_id,
                            "type": rel.get("type", "AFFECTS"),
                            "weight": float(rel.get("weight", 0.8)),
                            "condition": rel.get("condition"),
                            "is_hard_edge": False,
                        }
                    })
                    await self._sleep(0.1)

        await self.progress(1.0, "Synthesis complete")
        await self._sleep(0.5)
        summary = (
            f"High-Fidelity Consensus Graph built: "
            f"{self.stats['nodes_added']} nodes, {self.stats['edges_added']} edges."
        )
        await self.completed(summary)
