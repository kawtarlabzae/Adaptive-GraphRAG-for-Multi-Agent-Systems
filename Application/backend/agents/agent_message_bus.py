"""
Agent Message Bus — real-time inter-agent communication.

Agents broadcast findings / alerts / requests so peers can incorporate
that context into their own LLM calls, creating genuine collaboration.

Every message is also emitted as a WebSocket event (type: "agent.message")
so the frontend can visualise the communication network in real time.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable, Dict, List

logger = logging.getLogger(__name__)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentMessageBus:
    """
    Lightweight asyncio-safe pub/sub bus for agent-to-agent messaging.

    Usage
    -----
    bus = AgentMessageBus(emit_fn)

    # broadcast to all peers
    await bus.broadcast(sender, display, icon, "finding", "Entity X causes Y")

    # directed message
    await bus.send(sender, display, icon, "pilot", "alert", "Turbulence ahead")

    # read peer context (formatted string for LLM injection)
    ctx = bus.get_context_for("navigator", limit=5)
    """

    def __init__(self, emit: Callable[[Dict], Awaitable[None]]):
        self._emit = emit
        self._messages: List[Dict] = []
        self._lock = asyncio.Lock()

    # ── Publishing ─────────────────────────────────────────────────────

    async def broadcast(
        self,
        sender: str,
        sender_display: str,
        sender_icon: str,
        msg_type: str,   # "finding" | "alert" | "summary" | "request" | "status"
        content: str,
    ) -> None:
        """Broadcast a message to all agents."""
        await self._publish(sender, sender_display, sender_icon, "all", msg_type, content)

    async def send(
        self,
        sender: str,
        sender_display: str,
        sender_icon: str,
        receiver: str,   # agent name
        msg_type: str,
        content: str,
    ) -> None:
        """Send a directed message to a specific agent."""
        await self._publish(sender, sender_display, sender_icon, receiver, msg_type, content)

    async def _publish(
        self,
        sender: str,
        sender_display: str,
        sender_icon: str,
        receiver: str,
        msg_type: str,
        content: str,
    ) -> None:
        ts = _ts()
        msg: Dict = {
            "sender": sender,
            "sender_display": sender_display,
            "sender_icon": sender_icon,
            "receiver": receiver,
            "msg_type": msg_type,
            "content": content,
            "ts": ts,
        }
        async with self._lock:
            self._messages.append(msg)

        try:
            await self._emit({
                "type": "agent.message",
                "agent": sender,
                "agent_display": sender_display,
                "agent_icon": sender_icon,
                "data": msg,
                "timestamp": ts,
            })
        except Exception as e:
            logger.warning("AgentMessageBus emit error: %s", e)

    # ── Reading ────────────────────────────────────────────────────────

    def get_context_for(self, agent_name: str, limit: int = 5) -> str:
        """
        Return recent peer messages as a formatted string suitable for
        injection into an LLM prompt. Excludes messages sent BY this agent.
        """
        relevant = [
            m for m in self._messages
            if m["sender"] != agent_name
            and (m["receiver"] == "all" or m["receiver"] == agent_name)
        ]
        recent = relevant[-limit:]
        if not recent:
            return ""
        lines = []
        for m in recent:
            to = "everyone" if m["receiver"] == "all" else m["receiver"]
            lines.append(
                f"[{m['sender_display']} → {to}] {m['msg_type'].upper()}: {m['content']}"
            )
        return "\n".join(lines)

    def get_all(self) -> List[Dict]:
        return list(self._messages)
