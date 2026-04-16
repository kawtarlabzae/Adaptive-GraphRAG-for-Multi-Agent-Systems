"""
Engineer Agent — Phase 2 (Aviation)
Monitors the Pressure Loop: detects deviations between predicted (F_p)
and actual (F_a) fuel burn, triggers targeted graph re-analysis, and
updates edge weights in real-time.

Pressure Signal: if |ΔF| = |F_a - F_p| / F_p > threshold → re-analyse
Communicates critical pressure alerts to Pilot via directed AgentMessageBus messages.
"""
import asyncio
import logging
from typing import List, Dict, Optional

from .base import BaseAgent, EventEmitter
from .agent_message_bus import AgentMessageBus
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)

PRESSURE_THRESHOLD = 0.04   # 4% deviation triggers re-analysis
WEIGHT_DECAY       = 0.92   # edge weight update decay


class EngineerAgent(BaseAgent):
    name = "engineer"
    display_name = "Engineer Agent"
    phase = 2
    icon = "🔧"

    def __init__(self, *args, bus: Optional[AgentMessageBus] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._pressure_history: List[Dict] = []
        self._knowledge_latency_ms: List[float] = []
        self._bus = bus

    async def run(self, session_id: str, **kwargs):
        await self.started()
        await self.thinking(
            f"Pressure Loop engine active. Monitoring |ΔF| threshold = {PRESSURE_THRESHOLD:.0%}"
        )
        await self._sleep(0.6)

        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                f"Engineer Agent online. Pressure Loop armed. "
                f"Will trigger graph re-analysis when |ΔF| > {PRESSURE_THRESHOLD:.0%}.",
            )

        await self.completed("Engineer Agent standing by. Will trigger graph updates on pressure signals.")

    async def evaluate_pressure(
        self,
        flight_state: Dict,
        session_id: str,
        model: str = "llama3.2",
    ) -> Optional[Dict]:
        """
        Evaluate a flight state tick for pressure signals.
        Returns a pressure event dict if triggered, else None.
        Sends directed alert to Pilot via bus when triggered.
        """
        import time
        pressure_delta = flight_state.get("pressure_delta", 0.0)
        if pressure_delta <= PRESSURE_THRESHOLD:
            return None

        anomaly   = flight_state.get("active_anomaly")
        f_pred    = flight_state.get("fuel_predicted", 0)
        f_actual  = flight_state.get("fuel_kg", 0)
        waypoint  = flight_state.get("current_waypoint", {}).get("id", "?")
        wp_name   = flight_state.get("current_waypoint", {}).get("name", waypoint)
        tick      = flight_state.get("tick", 0)
        alt       = flight_state.get("alt_ft", 35000)
        mach      = flight_state.get("mach", 0.785)

        await self.thinking(
            f"⚠️  PRESSURE SIGNAL at {wp_name}: |ΔF|={pressure_delta:.1%} "
            f"(F_p={f_pred:.0f}kg, F_a={f_actual:.0f}kg). "
            f"Anomaly: {anomaly}. Triggering targeted research…"
        )
        await self._sleep(0.4)

        # Immediately alert the Pilot via directed bus message
        if self._bus:
            severity = "CRITICAL" if pressure_delta > 0.10 else "WARNING"
            await self._bus.send(
                self.name, self.display_name, self.icon,
                "pilot",   # directed to pilot
                "alert",
                f"{severity}: Fuel burn deviation {pressure_delta:.1%} at {wp_name} "
                f"(FL{int(alt/100):03d}, M{mach:.3f}). Anomaly: {anomaly}. "
                f"F_predicted={f_pred:.0f}kg, F_actual={f_actual:.0f}kg. "
                f"Recommend {'immediate action' if pressure_delta > 0.10 else 'increased monitoring'}.",
            )
            # Also broadcast to navigator for routing implications
            await self._bus.send(
                self.name, self.display_name, self.icon,
                "navigator",
                "alert",
                f"Fuel deviation {pressure_delta:.1%} due to {anomaly} at {wp_name}. "
                f"Route efficiency impacted. Consider alternate track or altitude.",
            )

        t0 = time.perf_counter()

        # Targeted re-analysis: ask LLM which graph nodes explain the anomaly
        ollama  = get_ollama()
        neo4j   = get_neo4j()
        all_nodes = neo4j.get_all_nodes(session_id)

        nodes_to_update = self._identify_relevant_nodes(anomaly, all_nodes)

        update_prompt = f"""The flight management system detected a {pressure_delta:.1%} fuel burn deviation.
Anomaly type: {anomaly}
Current position: {wp_name} at FL{int(alt/100):03d}, Mach {mach:.3f}
Affected nodes: {[n.get('label') for n in nodes_to_update]}

For each affected graph edge, calculate a new weight (0-1) that better reflects
this anomaly's impact. Return ONLY valid JSON:
{{
  "edge_updates": [
    {{"from": "node_id", "to": "node_id", "new_weight": 0.92,
      "reason": "OAT anomaly strengthens SFC dependency"}}
  ],
  "new_nodes": [
    {{"id": "id", "label": "label", "type": "type", "description": "desc"}}
  ],
  "explanation": "One sentence explanation of the anomaly"
}}
JSON:"""

        raw = await ollama.generate(update_prompt, model=model)
        update_data = ollama._parse_json_response(raw, default={
            "edge_updates": [
                {"from": "oat", "to": "sfc",
                 "new_weight": 0.91,
                 "reason": f"{anomaly} increases SFC dependency on OAT"}
            ],
            "new_nodes": [],
            "explanation": f"Anomaly '{anomaly}' caused {pressure_delta:.1%} deviation — graph weights updated."
        })

        latency_ms = (time.perf_counter() - t0) * 1000
        self._knowledge_latency_ms.append(latency_ms)

        # Apply graph updates
        new_nodes = update_data.get("new_nodes", [])
        for node in new_nodes:
            if node.get("id") and not neo4j.node_exists(node["id"], session_id):
                neo4j.create_node(
                    node_id=node["id"], label=node.get("label", node["id"]),
                    node_type=node.get("type", "variable"),
                    description=node.get("description", ""),
                    confidence=0.85, session_id=session_id,
                )
                self.stats["nodes_added"] += 1
                await self.emit("agent.node_added", {
                    "node": node,
                    "source": "pressure_loop",
                })

        # Build pressure event record
        event = {
            "tick": tick,
            "waypoint": waypoint,
            "waypoint_name": wp_name,
            "pressure_delta": round(pressure_delta, 4),
            "f_predicted": round(f_pred, 1),
            "f_actual": round(f_actual, 1),
            "anomaly": anomaly,
            "edge_updates": update_data.get("edge_updates", []),
            "new_nodes_added": len(new_nodes),
            "explanation": update_data.get("explanation", ""),
            "knowledge_latency_ms": round(latency_ms, 1),
        }
        self._pressure_history.append(event)
        self.stats["paths_computed"] = len(self._pressure_history)

        await self.emit("agent.pressure_event", {
            "event": event,
            "edge_updates": update_data.get("edge_updates", []),
            "avg_latency_ms": round(
                sum(self._knowledge_latency_ms) / len(self._knowledge_latency_ms), 1
            ),
        })

        # Broadcast resolution to all agents
        if self._bus:
            explanation = update_data.get("explanation", "")
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "finding",
                f"Graph re-analysis complete for {anomaly} at {wp_name}. "
                f"{explanation} Knowledge latency: {latency_ms:.0f}ms. "
                f"{len(update_data.get('edge_updates', []))} edge weights updated.",
            )

        return event

    def _identify_relevant_nodes(self, anomaly: Optional[str], all_nodes: List[Dict]) -> List[Dict]:
        """Return graph nodes most relevant to the anomaly type."""
        if not anomaly:
            return all_nodes[:5]
        kw_map = {
            "turbulence":     ["turbulence", "sfc", "fuel", "drag"],
            "isa_deviation":  ["oat", "isa", "temperature", "sfc", "density"],
            "jet_stream_loss":["jet_stream", "wind", "ground_speed", "fuel"],
            "mach_divergence":["mach", "drag", "wave_drag", "divergence"],
        }
        keywords = kw_map.get(anomaly, ["fuel", "sfc"])
        scored = []
        for n in all_nodes:
            score = sum(1 for kw in keywords if kw in n.get("id","").lower()
                        or kw in n.get("label","").lower())
            if score:
                scored.append((score, n))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:6]]

    def avg_knowledge_latency(self) -> float:
        if not self._knowledge_latency_ms:
            return 0.0
        return sum(self._knowledge_latency_ms) / len(self._knowledge_latency_ms)
