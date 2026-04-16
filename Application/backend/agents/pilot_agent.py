"""
Pilot Agent — Aviation Digital Twin
Makes flight control decisions using the aero knowledge graph.
Communicates decisions to peers via AgentMessageBus.
Responds to user chat queries as the AI Pilot.
"""
import asyncio
import logging
from typing import Dict, List, Optional

from .base import BaseAgent, EventEmitter
from .agent_message_bus import AgentMessageBus
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)


class PilotAgent(BaseAgent):
    name = "pilot"
    display_name = "Pilot Agent"
    phase = 2
    icon = "✈️"

    def __init__(self, *args, bus: Optional[AgentMessageBus] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._bus = bus

    async def run(self, session_id: str, **kwargs):
        await self.started()
        await self.thinking("Initialising State-Aware Probabilistic Walk engine…")
        await asyncio.sleep(0.6)
        await self.thinking("Loading aerodynamics sub-graph for current flight phase: GROUND → CLIMB")
        await asyncio.sleep(0.5)
        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                "Pilot Agent online. Graph traversal engine active. Awaiting navigator route plan.",
            )
        await self.completed("Pilot Agent online — issuing commands via graph traversal.")

    async def decide_command(self, flight_state: Dict, graph_context: List[Dict],
                             model: str = "llama3.2") -> Dict:
        """Generate a flight command and broadcast it to peers."""
        ollama = get_ollama()

        context_str = "\n".join(
            f"  • {n.get('label')}: {n.get('description', '')}"
            for n in graph_context[:8]
        )
        # Read peer context (navigator/engineer messages)
        peer_ctx = self._bus.get_context_for(self.name, limit=4) if self._bus else ""
        peer_section = f"\nPeer agent communications:\n{peer_ctx}\n" if peer_ctx else ""

        phase = flight_state.get("phase", "cruise")
        alt   = flight_state.get("alt_ft", 35000)
        mach  = flight_state.get("mach", 0.785)
        fuel  = flight_state.get("fuel_kg", 10000)
        oat   = flight_state.get("oat_c", -54)
        turb  = flight_state.get("turb_level", 0)
        pdelta= flight_state.get("pressure_delta", 0)

        prompt = f"""You are the AI Pilot Agent for Boeing 737-800 (JFK→LHR).
Flight state: phase={phase}, alt={alt:.0f}ft, Mach={mach:.3f},
fuel={fuel:.0f}kg, OAT={oat:.1f}°C, turbulence={turb:.2f}, ΔP={pdelta:.3f}
{peer_section}
Knowledge graph context:
{context_str}

Generate a precise flight command. Return ONLY valid JSON:
{{
  "throttle_pct": 85.0,
  "pitch_deg": 2.5,
  "bank_deg": 0.0,
  "target_mach": 0.785,
  "target_alt_ft": 35000,
  "action": "MAINTAIN_CRUISE|STEP_CLIMB|SPEED_REDUCTION|TURBULENCE_AVOID|EMERGENCY_DESCENT",
  "reasoning": "Brief reasoning referencing graph edges",
  "graph_nodes_used": ["node_id1", "node_id2"]
}}
JSON:"""

        raw = await ollama.generate(prompt, model=model)
        result = ollama._parse_json_response(raw, default={
            "throttle_pct": 85.0, "pitch_deg": 2.5, "bank_deg": 0.0,
            "target_mach": 0.785, "target_alt_ft": 35000,
            "action": "MAINTAIN_CRUISE",
            "reasoning": "Graph edge: Mach_number→AFFECTS→SFC (cruise efficiency nominal)",
            "graph_nodes_used": ["mach_number", "sfc", "fuel_efficiency"],
        })
        self.stats["paths_computed"] += 1

        # Broadcast decision to peers
        if self._bus:
            action = result.get("action", "MAINTAIN_CRUISE")
            reasoning = result.get("reasoning", "")
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "decision",
                f"{action} at FL{int(alt/100):03d} M{mach:.3f} — {reasoning[:120]}",
            )
        return result

    async def chat_response(self, message: str, graph_context: List[Dict],
                            model: str = "llama3.2") -> Dict:
        """Respond to a user chat message as the Pilot Agent."""
        ollama = get_ollama()
        context_str = "\n".join(
            f"  • {n.get('label')}: {n.get('description', '')}"
            for n in graph_context[:10]
        )
        peer_ctx = self._bus.get_context_for("user", limit=5) if self._bus else ""
        peer_section = f"\nRecent agent communications:\n{peer_ctx}\n" if peer_ctx else ""

        prompt = f"""You are the AI Pilot Agent for Boeing 737-800 flight JFK→LHR.
You have full situational awareness through the aviation knowledge graph.
You communicate clearly, using precise aviation terminology and referencing graph knowledge.

Aviation Knowledge Graph Context:
{context_str}
{peer_section}
Crew question: {message}

Respond as the Pilot with specific technical detail. Return ONLY valid JSON:
{{
  "answer": "Your detailed pilot response with aviation specifics",
  "reasoning_chain": ["step 1", "step 2", "step 3"],
  "confidence": 0.92,
  "nodes_used": ["node_id1", "node_id2"]
}}
JSON:"""

        raw = await ollama.generate(prompt, model=model)
        result = ollama._parse_json_response(raw, default={
            "answer": (
                f"Flight management is processing your query. "
                f"Based on current graph analysis: the question relates to "
                f"{message.split()[0] if message else 'flight parameters'}. "
                "Refer to the knowledge graph for causal relationships."
            ),
            "reasoning_chain": [
                "Graph traversal initiated from current state vector",
                "Relevant nodes retrieved via probabilistic walk",
                "Response generated from sub-graph context",
            ],
            "confidence": 0.75,
            "nodes_used": ["mach_number", "fuel_efficiency", "sfc"],
        })
        return result

    def get_local_subgraph(self, flight_state: Dict, session_id: str,
                           epsilon: float = 3.0) -> List[Dict]:
        """State-Aware Probabilistic Walk — returns relevant graph nodes."""
        neo4j = get_neo4j()
        all_nodes = neo4j.get_all_nodes(session_id)
        phase  = flight_state.get("phase", "cruise")
        mach   = flight_state.get("mach", 0.785)
        turb   = flight_state.get("turb_level", 0)
        pdelta = flight_state.get("pressure_delta", 0)

        keywords = [phase, "fuel", "sfc", "efficiency"]
        if mach > 0.84:  keywords += ["mach_divergence", "drag", "wave_drag"]
        if turb > 0.4:   keywords += ["turbulence", "sfc", "fuel_burn"]
        if pdelta > 0.04: keywords += ["pressure", "anomaly", "isa_deviation"]

        scored = []
        for node in all_nodes:
            label = node.get("label", "").lower()
            desc  = node.get("description", "").lower()
            nid   = node.get("id", "").lower()
            score = sum(1.5 for kw in keywords if kw in label or kw in nid)
            score += sum(0.5 for kw in keywords if kw in desc)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:10]]
