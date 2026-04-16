"""
Research Agent — Self-Organizing, Role-Negotiating Knowledge Extractor

Each agent starts with no assigned role. Through communication on the
AgentMessageBus it reads what peers are already covering, samples its
document slice, and uses the LLM to determine the most valuable
contribution it can make to the team's shared goal.

Role negotiation protocol
─────────────────────────
1. Agent announces availability → broadcasts to all peers
2. Reads bus: what focus areas have other agents declared?
3. Asks LLM: "Given peer coverage + document sample, what should I focus on?"
4. Declares focus → peers can adjust their own focus in response
5. Processes chunks through that specialised lens
6. Continuously reads peer context to build on — not duplicate — findings

Aviation Phase-2 contribution
──────────────────────────────
After Phase-1 knowledge build, agents retain their focus areas and
contribute to the flight simulation loop:
  • "flight_control"  focus → produce throttle/pitch/Mach JSON commands
  • "fuel / pressure" focus → evaluate pressure loop anomalies
  • "weather / route" focus → broadcast weather and routing observations
  • "synthesis"       focus → fill graph gaps from cross-agent findings
"""
import asyncio
import logging
import random
from typing import Dict, List, Optional, Any

from .base import BaseAgent, EventEmitter
from .agent_message_bus import AgentMessageBus
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)

MAX_CHUNKS_PER_AGENT = 10

ICONS = ['🔬', '🧠', '📡', '🔍', '💡', '🧩', '📊', '⚡', '🔭', '🌐']


class ResearchAgent(BaseAgent):
    """Self-organizing research agent with emergent role assignment."""

    def __init__(
        self,
        agent_id: int,
        session_id: str,
        emit: EventEmitter,
        model: str = "llama3.2",
        bus: Optional[AgentMessageBus] = None,
        total_agents: int = 4,
        research_goal: str = "Extract and structure knowledge from the provided documents",
    ):
        super().__init__(session_id, emit, model=model)
        self._agent_id    = agent_id
        self._bus         = bus
        self._total       = total_agents
        self._goal        = research_goal
        self._focus: Optional[str] = None        # determined through negotiation
        self._focus_keywords: List[str] = []     # for local subgraph scoring

        # Stable identity
        self.name         = f"research_{agent_id}"
        self.display_name = f"Agent {agent_id}"
        self.icon         = ICONS[agent_id % len(ICONS)]
        self.phase        = 1

    # ─────────────────────────────────────────────────────────────────
    # Phase 1 — Knowledge build
    # ─────────────────────────────────────────────────────────────────

    async def run(self, chunks: List[str] = None, session_id: str = None, **kwargs):
        ollama = get_ollama()
        neo4j  = get_neo4j()
        chunks = (chunks or [])[:MAX_CHUNKS_PER_AGENT]
        sid    = session_id or self.session_id

        await self.started()

        # Slight staggered start so agents don't all negotiate simultaneously
        await asyncio.sleep(self._agent_id * 0.3)

        # ── Step 1: announce presence ──────────────────────────────
        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                f"Agent {self._agent_id} online. Observing team, negotiating focus…",
            )

        # ── Step 2: negotiate role ─────────────────────────────────
        await self.thinking("Reading peer declarations to determine best contribution…")
        self._focus = await self._negotiate_role(chunks, ollama)

        await self.thinking(f"Focus established: {self._focus}")
        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                f"FOCUS DECLARED: {self._focus}",
            )
        # Update display for frontend
        await self.emit("agent.role_assigned", {
            "agent": self.name,
            "focus": self._focus,
        })

        if not chunks:
            await self.thinking("No document chunks assigned — monitoring peer findings.")
            await self.completed(f"Standing by as observer. Focus: {self._focus}")
            return

        # ── Step 3: knowledge extraction ──────────────────────────
        await self.thinking(f"Processing {len(chunks)} chunk(s) as: {self._focus}")

        for i, chunk in enumerate(chunks):
            if self._cancelled:
                break

            await self.progress(i / len(chunks), f"Chunk {i+1}/{len(chunks)}")

            # Read latest peer context before each chunk
            peer_ctx = self._bus.get_context_for(self.name, limit=5) if self._bus else ""
            peer_section = (
                f"\nPeer agent findings so far (do not duplicate, build on these):\n{peer_ctx}\n"
            ) if peer_ctx else ""

            prompt = f"""You are a research agent with this specialisation: {self._focus}

Team goal: {self._goal}
{peer_section}
Analyze the following text through your specialised lens.
Extract entities, relationships, and insights that YOUR focus area contributes.
Avoid duplicating what peers have already found.

Return ONLY valid JSON:
{{
  "entities": [
    {{"id": "snake_case_id", "label": "Human Readable Name",
      "type": "concept|process|variable|entity|metric",
      "description": "One sentence."}}
  ],
  "relationships": [
    {{"from_id": "id1", "to_id": "id2",
      "type": "RELATES_TO|AFFECTS|CAUSES|REQUIRES|PRODUCES|INHIBITS|CONTRADICTS",
      "weight": 0.8, "condition": null}}
  ],
  "insights": ["Key finding from your specialised perspective"]
}}

Text:
{chunk}

JSON:"""

            try:
                raw = await ollama.generate(prompt, model=self.model)
            except Exception as e:
                await self.emit("agent.output", {
                    "output_type": "error",
                    "message": f"LLM request failed: {e}",
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

            # Broadcast findings to peers
            if self._bus:
                insights = result.get("insights", [])
                if insights:
                    summary = "; ".join(s for s in insights[:2] if s.strip())
                    if summary:
                        await self._bus.broadcast(
                            self.name, self.display_name, self.icon,
                            "finding",
                            f"[{self._focus}] Chunk {i+1}: {summary[:220]}",
                        )
                if added_labels:
                    await self._bus.broadcast(
                        self.name, self.display_name, self.icon,
                        "entities",
                        f"Extracted via {self._focus}: {', '.join(added_labels[:5])}",
                    )

            for insight in result.get("insights", [])[:3]:
                if insight.strip():
                    await self.emit("agent.output", {
                        "output_type": "insight",
                        "message": f"[{self._focus}] {insight.strip()}",
                        "chunk": i + 1,
                    })

            await asyncio.sleep(0.4)

        await self.progress(1.0, "Complete")
        summary = (
            f"Extracted {self.stats['nodes_added']} nodes and "
            f"{self.stats['edges_added']} edges as: {self._focus}"
        )
        await self.completed(summary)
        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "summary",
                f"Phase 1 complete. {summary}",
            )

    # ─────────────────────────────────────────────────────────────────
    # Role negotiation
    # ─────────────────────────────────────────────────────────────────

    async def _negotiate_role(self, chunks: List[str], ollama) -> str:
        """
        Use the LLM to determine this agent's focus area based on:
        - What peers have already declared
        - A sample of the documents this agent will process
        - The team's shared research goal
        """
        peer_declarations = self._bus.get_context_for(self.name, limit=10) if self._bus else ""
        doc_sample = (chunks[0][:500] if chunks else "No documents assigned.")

        prompt = f"""You are one of {self._total} research agents forming a self-organizing team.

Team goal: {self._goal}

Peer agents have already declared these focus areas:
{peer_declarations if peer_declarations else "(you are first — no peers have declared yet)"}

Sample of documents you will process:
---
{doc_sample}
---

Your task: decide the single most VALUABLE focus area for you to adopt,
given what the team already covers and what this document content suggests.

Rules:
- Pick a DIFFERENT focus than your peers (unless no peers have declared)
- Be specific: not just "research" but "causal relationships between X and Y"
- Consider gaps: what is NOT yet covered that the goal requires?

Return ONLY valid JSON:
{{
  "focus": "concise focus area (max 12 words)",
  "rationale": "one sentence — why this fills a gap the team needs",
  "keywords": ["kw1", "kw2", "kw3"]
}}
JSON:"""

        raw = await ollama.generate(prompt, model=self.model)
        result = ollama._parse_json_response(raw, default=None)

        if result and result.get("focus"):
            self._focus_keywords = result.get("keywords", [])
            return result["focus"]

        # Fallback: assign based on agent_id to guarantee diversity
        fallbacks = [
            "causal relationships and process dependencies",
            "quantitative metrics and variable interactions",
            "contradictions and conflicting evidence",
            "synthesis and cross-domain connections",
            "temporal patterns and dynamic processes",
            "risk factors and anomaly detection",
            "structural hierarchies and classifications",
            "constraints and limiting conditions",
        ]
        return fallbacks[self._agent_id % len(fallbacks)]

    # ─────────────────────────────────────────────────────────────────
    # Phase 2 — Aviation flight monitoring (contribution by focus)
    # ─────────────────────────────────────────────────────────────────

    async def contribute_to_flight_tick(
        self,
        flight_state: Dict,
        session_id: str,
        tick: int,
    ) -> Optional[Dict]:
        """
        Each tick the agent reads the flight state and contributes based on focus.
        Returns a typed contribution dict or None.

        Types: "command" | "pressure_alert" | "weather_obs" | "synthesis" | None
        """
        if not self._focus:
            return None

        focus_lower = self._focus.lower()

        # Flight control agents → every 3 ticks, produce a command
        if any(k in focus_lower for k in ("flight", "control", "command", "pilot", "manoeuvre", "throttle")):
            if tick % 3 == 2:
                return await self._produce_flight_command(flight_state, session_id)

        # Fuel / pressure agents → every tick, evaluate anomaly
        elif any(k in focus_lower for k in ("fuel", "pressure", "burn", "sfc", "efficiency", "anomaly", "deviation")):
            return await self._evaluate_pressure(flight_state, session_id)

        # Weather / route agents → every 5 ticks or on turbulence
        elif any(k in focus_lower for k in ("weather", "route", "turbulence", "navigation", "wind", "jet", "atmosphere")):
            turb = flight_state.get("turb_level", 0)
            if tick % 5 == 0 or turb > 0.3:
                return self._weather_observation(flight_state, tick)

        # Synthesis agents → every 8 ticks, identify graph gaps
        elif any(k in focus_lower for k in ("synthesis", "cross", "gap", "connect", "integrat")):
            if tick % 8 == 0:
                return await self._synthesis_contribution(flight_state, session_id)

        return None

    async def _produce_flight_command(self, state: Dict, session_id: str) -> Optional[Dict]:
        """Generate a flight command from graph context."""
        ollama = get_ollama()
        neo4j  = get_neo4j()

        # Score graph nodes relevant to current state
        all_nodes = neo4j.get_all_nodes(session_id)
        context   = self._score_subgraph(state, all_nodes)

        ctx_str = "\n".join(
            f"  • {n.get('label')}: {n.get('description', '')}"
            for n in context[:8]
        )
        peer_ctx = self._bus.get_context_for(self.name, limit=4) if self._bus else ""
        peer_section = f"\nPeer agent communications:\n{peer_ctx}\n" if peer_ctx else ""

        phase = state.get("phase", "cruise")
        alt   = state.get("alt_ft", 35000)
        mach  = state.get("mach", 0.785)
        fuel  = state.get("fuel_kg", 10000)
        oat   = state.get("oat_c", -54)
        turb  = state.get("turb_level", 0)

        prompt = f"""You are a flight management agent specialised in: {self._focus}
Flight: B737-800 JFK→LHR  state: phase={phase}, alt={alt:.0f}ft, Mach={mach:.3f},
fuel={fuel:.0f}kg, OAT={oat:.1f}°C, turbulence={turb:.2f}
{peer_section}
Knowledge graph context:
{ctx_str}

Generate a precise flight command. Return ONLY valid JSON:
{{
  "throttle_pct": 85.0, "pitch_deg": 2.5, "bank_deg": 0.0,
  "target_mach": 0.785, "target_alt_ft": 35000,
  "action": "MAINTAIN_CRUISE|STEP_CLIMB|SPEED_REDUCTION|TURBULENCE_AVOID|EMERGENCY_DESCENT",
  "reasoning": "Brief reasoning referencing graph nodes",
  "graph_nodes_used": ["node_id1"]
}}
JSON:"""

        raw = await ollama.generate(prompt, model=self.model)
        cmd = ollama._parse_json_response(raw, default={
            "throttle_pct": 85.0, "pitch_deg": 2.5, "bank_deg": 0.0,
            "target_mach": 0.785, "target_alt_ft": alt,
            "action": "MAINTAIN_CRUISE",
            "reasoning": f"Nominal cruise — {self._focus} analysis nominal",
            "graph_nodes_used": [],
        })
        self.stats["paths_computed"] += 1

        if self._bus and cmd:
            action = cmd.get("action", "MAINTAIN_CRUISE")
            reason = cmd.get("reasoning", "")
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "decision",
                f"{action} FL{int(alt/100):03d} M{mach:.3f} — {reason[:120]}",
            )

        return {"type": "command", "data": cmd} if cmd else None

    async def _evaluate_pressure(self, state: Dict, session_id: str) -> Optional[Dict]:
        """Evaluate fuel burn deviation (pressure loop)."""
        import time
        pressure_delta = state.get("pressure_delta", 0.0)
        if pressure_delta <= 0.04:
            return None

        anomaly  = state.get("active_anomaly")
        f_pred   = state.get("fuel_predicted", 0)
        f_actual = state.get("fuel_kg", 0)
        wp_name  = state.get("current_waypoint", {}).get("name", "en-route")
        alt      = state.get("alt_ft", 35000)
        mach     = state.get("mach", 0.785)

        await self.thinking(
            f"⚠️ Pressure signal at {wp_name}: |ΔF|={pressure_delta:.1%} — "
            f"F_p={f_pred:.0f}kg, F_a={f_actual:.0f}kg. Anomaly: {anomaly}"
        )

        if self._bus:
            severity = "CRITICAL" if pressure_delta > 0.10 else "WARNING"
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "alert",
                f"{severity}: Fuel deviation {pressure_delta:.1%} at {wp_name} "
                f"(FL{int(alt/100):03d} M{mach:.3f}). Anomaly={anomaly}. "
                f"F_pred={f_pred:.0f}kg → F_actual={f_actual:.0f}kg.",
            )

        t0     = time.perf_counter()
        ollama = get_ollama()
        neo4j  = get_neo4j()

        all_nodes   = neo4j.get_all_nodes(session_id)
        relevant    = self._nodes_for_anomaly(anomaly, all_nodes)

        update_prompt = f"""Fuel burn deviation {pressure_delta:.1%} detected at {wp_name}.
Anomaly type: {anomaly}. My focus: {self._focus}
Affected graph nodes: {[n.get('label') for n in relevant]}

Calculate updated edge weights and identify any new nodes. Return ONLY JSON:
{{
  "edge_updates": [{{"from": "id", "to": "id", "new_weight": 0.9, "reason": "…"}}],
  "new_nodes": [{{"id": "id", "label": "label", "type": "type", "description": "…"}}],
  "explanation": "One sentence"
}}
JSON:"""

        raw = await ollama.generate(update_prompt, model=self.model)
        upd = ollama._parse_json_response(raw, default={
            "edge_updates": [], "new_nodes": [],
            "explanation": f"{anomaly} caused {pressure_delta:.1%} deviation.",
        })

        latency_ms = (time.perf_counter() - t0) * 1000
        self.stats["paths_computed"] += 1

        for node in upd.get("new_nodes", []):
            if node.get("id") and not neo4j.node_exists(node["id"], session_id):
                neo4j.create_node(
                    node["id"], node.get("label", node["id"]),
                    node.get("type", "variable"), node.get("description", ""),
                    0.85, session_id,
                )
                self.stats["nodes_added"] += 1
                await self.emit("agent.node_added", {"node": node, "source": "pressure_loop"})

        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "finding",
                f"Pressure analysis done. {upd.get('explanation', '')} "
                f"Latency: {latency_ms:.0f}ms.",
            )

        return {
            "type": "pressure_alert",
            "data": {
                "waypoint": state.get("current_waypoint", {}).get("id", "?"),
                "waypoint_name": wp_name,
                "pressure_delta": round(pressure_delta, 4),
                "f_predicted": round(f_pred, 1),
                "f_actual": round(f_actual, 1),
                "anomaly": anomaly,
                "edge_updates": upd.get("edge_updates", []),
                "explanation": upd.get("explanation", ""),
                "knowledge_latency_ms": round(latency_ms, 1),
                "tick": state.get("tick", 0),
            },
        }

    def _weather_observation(self, state: Dict, tick: int) -> Optional[Dict]:
        """Broadcast weather/routing observation (synchronous, no LLM needed)."""
        if not self._bus:
            return None

        alt   = state.get("alt_ft", 35000)
        mach  = state.get("mach", 0.785)
        turb  = state.get("turb_level", 0)
        wp    = state.get("current_waypoint", {}).get("name", "en-route")

        async def _do_broadcast():
            if turb > 0.6:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "alert",
                    f"MODERATE CAT at {wp} FL{int(alt/100):03d}. Index {turb:.2f}. "
                    f"Recommend M{mach - 0.01:.3f} or ±2000ft deviation.",
                )
            elif turb > 0.3:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "finding",
                    f"Light turbulence at {wp} (index {turb:.2f}). Monitoring.",
                )
            else:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "status",
                    f"Clear air at {wp} FL{int(alt/100):03d} M{mach:.3f}. Track nominal.",
                )

        # Schedule the async broadcast without blocking (fire-and-forget)
        asyncio.ensure_future(_do_broadcast())
        return {"type": "weather_obs", "data": {"wp": wp, "turb": turb, "alt": alt}}

    async def _synthesis_contribution(self, state: Dict, session_id: str) -> Optional[Dict]:
        """Identify gaps in the knowledge graph and fill them."""
        neo4j = get_neo4j()
        ollama = get_ollama()

        all_nodes = neo4j.get_all_nodes(session_id)
        if len(all_nodes) < 4:
            return None

        peer_ctx = self._bus.get_context_for(self.name, limit=8) if self._bus else ""

        node_labels = [n.get("label") for n in all_nodes[:20]]
        prompt = f"""Synthesis agent reviewing the aviation knowledge graph.

Existing graph nodes: {node_labels}

Peer findings this flight:
{peer_ctx[:600] if peer_ctx else '(none yet)'}

My focus: {self._focus}

Identify 1-2 MISSING connections or nodes that would strengthen the graph.
Return ONLY valid JSON:
{{
  "new_nodes": [{{"id": "id", "label": "label", "type": "type", "description": "desc"}}],
  "new_relationships": [{{"from_id": "id", "to_id": "id", "type": "RELATES_TO", "weight": 0.8, "condition": null}}],
  "insight": "What gap this fills"
}}
JSON:"""

        raw = await ollama.generate(prompt, model=self.model)
        result = ollama._parse_json_response(raw, default={"new_nodes": [], "new_relationships": [], "insight": ""})
        if not result:
            return None

        added = []
        for node in result.get("new_nodes", [])[:2]:
            if node.get("id") and not neo4j.node_exists(node["id"], session_id):
                neo4j.create_node(
                    node["id"], node.get("label", node["id"]),
                    node.get("type", "concept"), node.get("description", ""),
                    0.8, session_id,
                )
                self.stats["nodes_added"] += 1
                added.append(node.get("label", node["id"]))
                await self.emit("agent.node_added", {"node": node, "source": "synthesis"})

        for rel in result.get("new_relationships", [])[:2]:
            fid = rel.get("from_id", "")
            tid = rel.get("to_id", "")
            if fid and tid:
                eid = neo4j.create_edge(fid, tid, rel.get("type", "RELATES_TO"),
                                        rel.get("weight", 0.8), rel.get("condition"),
                                        False, session_id)
                if eid:
                    self.stats["edges_added"] += 1
                    await self.emit("agent.edge_added", {
                        "edge": {"id": eid, "from_node": fid, "to_node": tid,
                                 "type": rel.get("type", "RELATES_TO"), "weight": rel.get("weight", 0.8)}
                    })

        if added and self._bus:
            insight = result.get("insight", "")
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "finding",
                f"Synthesis: added {', '.join(added)}. {insight[:160]}",
            )

        return {"type": "synthesis", "data": {"added": added}}

    # ─────────────────────────────────────────────────────────────────
    # Chat response (for aviation domain user queries)
    # ─────────────────────────────────────────────────────────────────

    async def chat_response(self, message: str, graph_context: List[Dict]) -> Dict:
        """Respond to a user chat message using graph + focus area knowledge."""
        ollama = get_ollama()
        ctx_str = "\n".join(
            f"  • {n.get('label')}: {n.get('description', '')}"
            for n in graph_context[:10]
        )
        peer_ctx = self._bus.get_context_for("user", limit=6) if self._bus else ""
        peer_section = f"\nRecent agent communications:\n{peer_ctx}\n" if peer_ctx else ""

        prompt = f"""You are a research agent specialised in: {self._focus}
Contributing to: B737-800 JFK→LHR digital twin

Aviation Knowledge Graph Context:
{ctx_str}
{peer_section}
Question: {message}

Answer with precise technical detail based on your specialisation and the graph context.
Return ONLY valid JSON:
{{
  "answer": "Detailed response referencing graph knowledge",
  "reasoning_chain": ["step 1", "step 2", "step 3"],
  "confidence": 0.88,
  "nodes_used": ["node_id1", "node_id2"]
}}
JSON:"""

        raw = await ollama.generate(prompt, model=self.model)
        return ollama._parse_json_response(raw, default={
            "answer": f"Based on my analysis ({self._focus}): {message}",
            "reasoning_chain": ["Graph traversal initiated", "Relevant nodes retrieved", "Response synthesised"],
            "confidence": 0.70,
            "nodes_used": [],
        })

    # ─────────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────────

    def _score_subgraph(self, state: Dict, all_nodes: List[Dict]) -> List[Dict]:
        """State-aware probabilistic node scoring."""
        phase   = state.get("phase", "cruise")
        mach    = state.get("mach", 0.785)
        turb    = state.get("turb_level", 0)
        pdelta  = state.get("pressure_delta", 0)

        keywords = [phase, "fuel", "sfc", "efficiency"] + self._focus_keywords
        if mach > 0.84:  keywords += ["mach_divergence", "wave_drag"]
        if turb  > 0.4:  keywords += ["turbulence", "fuel_burn"]
        if pdelta > 0.04: keywords += ["pressure", "anomaly"]

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

    def _nodes_for_anomaly(self, anomaly: Optional[str], all_nodes: List[Dict]) -> List[Dict]:
        kw_map = {
            "turbulence":     ["turbulence", "sfc", "fuel", "drag"],
            "isa_deviation":  ["oat", "isa", "temperature", "sfc", "density"],
            "jet_stream_loss":["jet_stream", "wind", "ground_speed", "fuel"],
            "mach_divergence":["mach", "drag", "wave_drag", "divergence"],
        }
        keywords = kw_map.get(anomaly or "", ["fuel", "sfc"])
        scored = []
        for n in all_nodes:
            score = sum(1 for kw in keywords
                        if kw in n.get("id", "").lower() or kw in n.get("label", "").lower())
            if score:
                scored.append((score, n))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:6]]
