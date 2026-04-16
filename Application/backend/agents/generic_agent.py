"""
Generic Agent — Custom domain
Processes document chunks using a user-defined role and goal via Ollama.
Extracts knowledge graph entities, relationships, and insights.
Communicates with peer agents through AgentMessageBus.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional

from .base import BaseAgent, EventEmitter
from .agent_message_bus import AgentMessageBus
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)

MAX_CHUNKS = 10


class GenericAgent(BaseAgent):
    """Agent driven entirely by user-supplied role/goal text."""

    def __init__(self, session_id: str, emit: EventEmitter,
                 agent_def: Dict[str, Any], model: str = "llama3.2",
                 bus: Optional[AgentMessageBus] = None):
        super().__init__(session_id, emit, model=model)
        self.name         = agent_def["name"]
        self.display_name = agent_def.get("display_name", agent_def["name"])
        self.phase        = agent_def.get("phase", 1)
        self.icon         = agent_def.get("icon", "🤖")
        self._role        = agent_def.get("role", "Research Agent")
        self._goal        = agent_def.get("goal", "Extract and analyze knowledge from documents")
        self._bus         = bus

    async def run(self, chunks: List[str] = None, session_id: str = None, **kwargs):
        ollama = get_ollama()
        neo4j  = get_neo4j()
        chunks = (chunks or [])[:MAX_CHUNKS]
        sid    = session_id or self.session_id

        await self.started()
        await self.thinking(f"Role: {self._role} | Goal: {self._goal}")

        if not chunks:
            await self.thinking("No document chunks provided — nothing to process.")
            await self.completed("No source documents to analyse.")
            return

        await self.thinking(f"Processing {len(chunks)} chunk(s) with role: {self._role}")

        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                f"Starting as {self._role}. Assigned {len(chunks)} chunk(s).",
            )

        for i, chunk in enumerate(chunks):
            if self._cancelled:
                break

            await self.progress(i / len(chunks), f"Chunk {i+1}/{len(chunks)}")
            await self.thinking(f"Reading chunk {i+1}: {chunk[:120].strip()}…")

            peer_context = self._bus.get_context_for(self.name, limit=4) if self._bus else ""

            system_prompt = (
                f"You are a {self._role}. "
                f"Your goal: {self._goal}. "
                "You extract structured knowledge graphs from text and return ONLY valid JSON."
            )

            peer_section = (
                f"\nPeer agent findings (build on these, avoid duplication):\n{peer_context}\n"
            ) if peer_context else ""

            prompt = f"""Analyze the following text as a {self._role}.
Goal: {self._goal}
{peer_section}
Extract entities, relationships, and key insights.
Return ONLY valid JSON — no extra text:
{{
  "entities": [
    {{"id": "snake_case_id", "label": "Human Readable Name",
      "type": "concept|process|variable|entity|metric",
      "description": "One sentence."}}
  ],
  "relationships": [
    {{"from_id": "id1", "to_id": "id2",
      "type": "RELATES_TO|AFFECTS|CAUSES|REQUIRES|PRODUCES|INHIBITS",
      "weight": 0.8, "condition": null}}
  ],
  "insights": ["Key finding or observation from this chunk"]
}}

Text:
{chunk}

JSON:"""

            try:
                raw = await ollama.generate(prompt, model=self.model, system=system_prompt)
            except Exception as e:
                await self.emit("agent.output", {
                    "output_type": "error",
                    "message": f"LLM request failed: {e}",
                    "chunk": i + 1,
                })
                await asyncio.sleep(0.3)
                continue

            result = ollama._parse_json_response(
                raw, default={"entities": [], "relationships": [], "insights": []}
            )
            if not result:
                await asyncio.sleep(0.3)
                continue

            added_labels: List[str] = []
            for ent in result.get("entities", [])[:8]:
                eid = ent.get("id", "").strip()
                if not eid or neo4j.node_exists(eid, sid):
                    continue
                neo4j.create_node(
                    eid, ent.get("label", eid), ent.get("type", "entity"),
                    ent.get("description", ""), 0.85, sid,
                )
                self.stats["nodes_added"] += 1
                added_labels.append(ent.get("label", eid))
                await self.emit("agent.node_added", {
                    "node": {
                        "id": eid, "label": ent.get("label", eid),
                        "type": ent.get("type", "entity"),
                        "description": ent.get("description", ""),
                        "confidence": 0.85,
                    }
                })

            for rel in result.get("relationships", [])[:6]:
                fid = rel.get("from_id", "").strip()
                tid = rel.get("to_id", "").strip()
                if not fid or not tid:
                    continue
                eid = neo4j.create_edge(
                    fid, tid, rel.get("type", "RELATES_TO"),
                    rel.get("weight", 0.8), rel.get("condition"),
                    False, sid,
                )
                if eid:
                    self.stats["edges_added"] += 1
                    await self.emit("agent.edge_added", {
                        "edge": {
                            "id": eid, "from_node": fid, "to_node": tid,
                            "type": rel.get("type", "RELATES_TO"),
                            "weight": rel.get("weight", 0.8),
                        }
                    })

            for insight in result.get("insights", [])[:3]:
                if insight.strip():
                    await self.emit("agent.output", {
                        "output_type": "insight",
                        "message": insight.strip(),
                        "chunk": i + 1,
                    })

            if self._bus:
                insights = result.get("insights", [])
                if insights:
                    summary = "; ".join(s for s in insights[:2] if s.strip())
                    if summary:
                        await self._bus.broadcast(
                            self.name, self.display_name, self.icon,
                            "finding", f"Chunk {i+1}: {summary[:200]}",
                        )
                if added_labels:
                    await self._bus.broadcast(
                        self.name, self.display_name, self.icon,
                        "entities",
                        f"Extracted: {', '.join(added_labels[:4])}",
                    )

            await asyncio.sleep(0.4)

        await self.progress(1.0, "Complete")
        summary = (
            f"Extracted {self.stats['nodes_added']} nodes and "
            f"{self.stats['edges_added']} edges."
        )
        await self.completed(summary)
        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "summary", f"Done. {summary}",
            )
