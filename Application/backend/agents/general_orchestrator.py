"""
General Orchestrator — Custom domain
Spawns N self-organizing ResearchAgents that negotiate their own roles
through the AgentMessageBus before processing documents.

Phase 1: Agents negotiate focus areas, then build the knowledge graph in parallel.
Phase 2: Chat interface — agents answer queries from their specialized perspectives.
"""
import asyncio
import logging
from typing import Dict, List, Callable, Awaitable

from agents.research_agent import ResearchAgent
from agents.agent_message_bus import AgentMessageBus
from services.document_processor import extract_text_from_file, chunk_text
from models.schemas import SessionConfig

logger = logging.getLogger(__name__)

EventEmitter = Callable[[Dict], Awaitable[None]]


def _ts():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


class GeneralOrchestrator:
    def __init__(self, session_id: str, config: SessionConfig,
                 emit: EventEmitter, phase_event: asyncio.Event):
        self.session_id   = session_id
        self.config       = config
        self._emit        = emit
        self._phase_event = phase_event
        self._cancelled   = False
        self._bus         = AgentMessageBus(emit)

        n    = max(2, min(config.num_agents, 8))
        goal = config.research_goal or config.description or config.name

        self._agents: List[ResearchAgent] = [
            ResearchAgent(
                agent_id=i,
                session_id=session_id,
                emit=emit,
                model=config.model,
                bus=self._bus,
                total_agents=n,
                research_goal=goal,
            )
            for i in range(n)
        ]

    def cancel(self):
        self._cancelled = True
        for a in self._agents:
            a.cancel()

    async def run(self, uploaded_files: List[Dict] = None):
        try:
            await self._run_inner(uploaded_files or [])
        except asyncio.CancelledError:
            await self._emit({"type": "session.stopped",
                              "data": {"message": "Session stopped."},
                              "timestamp": _ts()})
        except Exception as e:
            logger.exception("GeneralOrchestrator error: %s", e)
            await self._emit({"type": "session.error",
                              "data": {"message": str(e)},
                              "timestamp": _ts()})

    async def _run_inner(self, uploaded_files: List[Dict]):
        n    = len(self._agents)
        goal = self.config.research_goal or self.config.description or self.config.name

        await self._emit({
            "type": "session.started",
            "data": {
                "session_id": self.session_id,
                "config": self.config.model_dump(),
                "message": (
                    f"Research network starting: {n} agents, "
                    f"goal — {goal[:80]}"
                ),
                "domain": "custom",
            },
            "timestamp": _ts(),
        })
        await asyncio.sleep(0.3)

        # ── Prepare chunks ─────────────────────────────────────────
        chunks: List[str] = []
        for f in uploaded_files:
            text = extract_text_from_file(f["content"], f["name"])
            chunks.extend(chunk_text(text, self.config.chunk_size))

        await self._emit({
            "type": "documents.ready",
            "data": {
                "total_chunks": len(chunks),
                "uploaded_files": [f["name"] for f in uploaded_files],
            },
            "timestamp": _ts(),
        })

        if not chunks:
            await self._emit({
                "type": "agent.output",
                "agent": "system", "agent_display": "System", "agent_icon": "⚠️",
                "data": {
                    "output_type": "warning",
                    "message": (
                        "No documents uploaded. Agents will negotiate roles but have no "
                        "source material to analyse. Upload files to enable knowledge extraction."
                    ),
                },
                "timestamp": _ts(),
            })

        # ════════════════════════════════════════════════════════════
        # PHASE 1 — Self-organizing knowledge build
        # ════════════════════════════════════════════════════════════
        await self._emit({
            "type": "phase.started",
            "data": {
                "phase": 1,
                "name": "Knowledge Build",
                "message": (
                    f"Phase 1: {n} research agents negotiating roles and "
                    f"building knowledge graph…"
                ),
            },
            "timestamp": _ts(),
        })

        # Round-robin chunk distribution — each agent processes a distinct slice
        agent_chunks = [chunks[i::n] for i in range(n)]

        await asyncio.gather(
            *[
                agent.run(chunks=agent_chunks[i], session_id=self.session_id)
                for i, agent in enumerate(self._agents)
            ]
        )

        await self._emit({
            "type": "phase.completed",
            "data": {"phase": 1, "message": "Phase 1 complete — knowledge graph built."},
            "timestamp": _ts(),
        })

        # ── Signal frontend: waiting for user to advance ───────────
        from services.neo4j_service import get_neo4j
        neo4j      = get_neo4j()
        node_count = len(neo4j.get_all_nodes(self.session_id))
        edge_count = len(neo4j.get_all_edges(self.session_id))

        await self._emit({
            "type": "phase.waiting",
            "data": {
                "message": "Phase 1 complete. Click 'Start Testing' to enter the chat phase.",
                "node_count": node_count,
                "edge_count": edge_count,
            },
            "timestamp": _ts(),
        })

        try:
            await asyncio.wait_for(self._phase_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            logger.info("Phase advance timed out for session %s", self.session_id)

        if self._cancelled:
            return

        # ════════════════════════════════════════════════════════════
        # PHASE 2 — Chat / testing
        # ════════════════════════════════════════════════════════════
        await self._emit({
            "type": "phase.started",
            "data": {"phase": 2, "name": "Testing",
                     "message": "Phase 2: chat mode — query the agent network."},
            "timestamp": _ts(),
        })

        await self._emit({
            "type": "phase2.ready",
            "data": {
                "message": "Research network ready. Use the chat panel to query the knowledge graph.",
                "node_count": node_count,
                "edge_count": edge_count,
            },
            "timestamp": _ts(),
        })

        # Keep alive until stopped
        while not self._cancelled:
            await asyncio.sleep(5)

        await self._emit({
            "type": "session.completed",
            "data": {
                "message": "Session completed.",
                "metrics": {
                    "total_nodes": node_count,
                    "total_edges": edge_count,
                    "logical_chain_accuracy": 0,
                    "context_efficiency": 0,
                    "hallucination_rate": 0,
                    "pruned_nodes": 0,
                    "conflicts_detected": 0,
                    "scenarios_passed": 0,
                },
            },
            "timestamp": _ts(),
        })
