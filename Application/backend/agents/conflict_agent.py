"""
Conflict Agent — Phase 1
Detects contradictions and conflicting claims between document sources.
Creates conditional edges representing knowledge as a function of variables.
"""
import asyncio
import logging
from typing import List, Tuple

from .base import BaseAgent, EventEmitter
from services.ollama_service import get_ollama
from services.document_processor import get_chunk_pairs

logger = logging.getLogger(__name__)


class ConflictAgent(BaseAgent):
    name = "conflict"
    display_name = "Conflict Agent"
    phase = 1
    icon = "⚔️"

    async def run(self, chunks: List[str], **kwargs):
        await self.started()
        await self.thinking("Scanning document corpus for contradictions and conflicting claims…")
        await self._sleep(0.8)

        ollama = get_ollama()
        pairs = get_chunk_pairs(chunks)
        total = len(pairs)

        if total == 0:
            await self.thinking("No chunk pairs to compare. Skipping conflict detection.")
            await self.completed("No conflicts detected (single document).")
            return

        await self.thinking(f"Comparing {total} chunk pair(s) across {len(chunks)} document segments…")

        all_conflicts = []
        for idx, (chunk_a, chunk_b) in enumerate(pairs):
            if self._cancelled:
                break

            await self.progress((idx / total) * 0.8, f"Comparing pair {idx + 1}/{total}")
            await self.thinking(f"Analysing pair {idx + 1}/{total}: looking for conflicting thresholds and claims…")
            await self._sleep(0.5)

            result = await ollama.find_conflicts(chunk_a, chunk_b, model=self.model)
            conflicts = result.get("conflicts", [])

            for conflict in conflicts:
                self.stats["conflicts_found"] += 1
                all_conflicts.append(conflict)
                await self.emit("agent.conflict_found", {
                    "conflict": conflict,
                    "pair_index": idx,
                    "severity": conflict.get("severity", "medium"),
                    "topic": conflict.get("topic", "Unknown"),
                    "source_a": conflict.get("source_a", ""),
                    "source_b": conflict.get("source_b", ""),
                    "resolution": conflict.get("resolution", "Requires expert review"),
                })
                await self._sleep(0.3)

        await self.progress(1.0, "Conflict detection complete")
        await self._sleep(0.5)

        summary = (
            f"Detected {self.stats['conflicts_found']} conflict(s) across {total} chunk pair(s). "
            "Conflicts recorded as conditional edges in the knowledge graph."
        )
        await self.emit("agent.conflict_summary", {
            "total_conflicts": self.stats["conflicts_found"],
            "all_conflicts": all_conflicts,
        })
        await self.completed(summary)
