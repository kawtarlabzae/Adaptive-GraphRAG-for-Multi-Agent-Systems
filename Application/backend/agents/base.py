"""
Base agent class with event emission and lifecycle management.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable, Dict, Any, Optional

logger = logging.getLogger(__name__)

EventEmitter = Callable[[Dict[str, Any]], Awaitable[None]]


class BaseAgent:
    """
    Abstract base for all Knowledge-as-a-Component agents.
    Each agent emits structured events consumed by the WebSocket layer
    and rendered in real-time by the Vue.js dashboard.
    """

    name: str = "base"
    display_name: str = "Base Agent"
    phase: int = 1
    icon: str = "🤖"

    def __init__(self, session_id: str, emit: EventEmitter,
                 model: str = "llama3.2"):
        self.session_id = session_id
        self._emit = emit
        self.model = model
        self._cancelled = False
        self.stats: Dict[str, int] = {
            "nodes_added": 0,
            "edges_added": 0,
            "conflicts_found": 0,
            "scenarios_tested": 0,
            "nodes_pruned": 0,
            "paths_computed": 0,
        }

    def cancel(self):
        self._cancelled = True

    async def emit(self, event_type: str, data: Dict[str, Any],
                   agent_override: Optional[str] = None):
        """Emit a timestamped event to all WebSocket subscribers."""
        payload = {
            "type": event_type,
            "agent": agent_override or self.name,
            "agent_display": self.display_name,
            "agent_icon": self.icon,
            "phase": self.phase,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        try:
            await self._emit(payload)
        except Exception as e:
            logger.error("Emit error [%s]: %s", event_type, e)

    async def started(self):
        await self.emit("agent.started", {
            "message": f"{self.display_name} initialising…",
            "stats": self.stats,
        })

    async def thinking(self, thought: str):
        await self.emit("agent.thinking", {"thought": thought})

    async def progress(self, pct: float, task: str = ""):
        await self.emit("agent.progress", {"progress": pct, "task": task})

    async def completed(self, summary: str = ""):
        await self.emit("agent.completed", {
            "message": summary or f"{self.display_name} completed.",
            "stats": self.stats,
        })

    async def error(self, message: str):
        await self.emit("agent.error", {"message": message})

    async def run(self, **kwargs):
        """Override in subclasses."""
        raise NotImplementedError

    async def _sleep(self, seconds: float):
        """Cancellable sleep."""
        await asyncio.sleep(seconds)
