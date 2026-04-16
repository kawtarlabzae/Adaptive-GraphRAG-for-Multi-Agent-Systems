"""
Pathfinder Agent — Phase 2
Implements Agent-Led Probabilistic Walks for context-efficient sub-graph retrieval.
Replaces Top-K vector retrieval with scored reasoning paths.

Formula: P(path) = ∏ w_edge(i) · rel(query, node_i)
"""
import asyncio
import logging
import math
from typing import List, Dict, Tuple, Optional

from .base import BaseAgent, EventEmitter
from services.neo4j_service import get_neo4j
from services.ollama_service import get_ollama

logger = logging.getLogger(__name__)

MAX_PATH_DEPTH = 5
TOP_K_PATHS = 3


class PathfinderAgent(BaseAgent):
    name = "pathfinder"
    display_name = "Pathfinder Agent"
    phase = 2
    icon = "🧭"

    async def run(self, session_id: str, **kwargs):
        """Calibrate the pathfinder on the current graph."""
        await self.started()
        await self.thinking(
            "Initialising probabilistic walk engine over the knowledge graph…"
        )
        await self._sleep(0.8)

        neo4j = get_neo4j()
        all_nodes = neo4j.get_all_nodes(session_id)
        all_edges = neo4j.get_all_edges(session_id)

        await self.thinking(
            f"Graph loaded: {len(all_nodes)} nodes, {len(all_edges)} edges. "
            "Computing edge weight distributions…"
        )
        await self._sleep(0.6)

        # Compute basic statistics for adaptive thresholding
        weights = [float(e.get("weight", 1.0)) for e in all_edges]
        avg_w = sum(weights) / max(len(weights), 1)
        max_w = max(weights) if weights else 1.0

        await self.thinking(
            f"Edge weight stats — avg: {avg_w:.3f}, max: {max_w:.3f}. "
            "Pathfinder calibrated for probabilistic reasoning walks."
        )
        await self.progress(0.7, "Calibrating probabilistic walk parameters")
        await self._sleep(0.5)

        # Demo: run a quick test traversal
        if all_nodes:
            start_node = next(
                (n for n in all_nodes if n.get("id") == "temperature"),
                all_nodes[0]
            )
            paths = self._probabilistic_walk(
                start_id=start_node.get("id", ""),
                query_keywords=["anthocyanin", "quality"],
                session_id=session_id,
                neo4j=neo4j,
            )
            self.stats["paths_computed"] += len(paths)
            await self.emit("agent.path_computed", {
                "start_node": start_node.get("label", ""),
                "query": "temperature → berry quality",
                "paths": [
                    {
                        "nodes": p["nodes"],
                        "score": round(p["score"], 4),
                        "length": len(p["nodes"]),
                    }
                    for p in paths[:TOP_K_PATHS]
                ],
            })

        await self.progress(1.0, "Pathfinder ready")
        await self._sleep(0.4)
        await self.completed(
            f"Pathfinder calibrated. {self.stats['paths_computed']} path(s) computed. "
            "Ready for real-time sub-graph injection."
        )

    def _probabilistic_walk(
        self,
        start_id: str,
        query_keywords: List[str],
        session_id: str,
        neo4j,
        max_depth: int = MAX_PATH_DEPTH,
    ) -> List[Dict]:
        """
        BFS with probabilistic scoring.
        P(path) = ∏ w_edge(i) · rel(query, node_i)
        """
        all_nodes = {n.get("id", ""): n for n in neo4j.get_all_nodes(session_id)}
        queue: List[Tuple[str, List[str], float]] = [(start_id, [start_id], 1.0)]
        completed_paths: List[Dict] = []
        visited: set = {start_id}

        keywords_lower = [k.lower() for k in query_keywords]

        while queue:
            node_id, path, score = queue.pop(0)
            if len(path) >= max_depth:
                completed_paths.append({"nodes": path, "score": score})
                continue

            neighbours = neo4j.get_neighbors(node_id, session_id)
            if not neighbours:
                completed_paths.append({"nodes": path, "score": score})
                continue

            for nb_id, rel_type, weight in neighbours:
                if nb_id in visited:
                    continue
                nb_node = all_nodes.get(nb_id, {})
                nb_label = nb_node.get("label", nb_id).lower()
                # Relevance: keyword match
                relevance = 1.0 + sum(0.3 for kw in keywords_lower if kw in nb_label)
                new_score = score * float(weight) * relevance
                visited.add(nb_id)
                new_path = path + [nb_id]
                queue.append((nb_id, new_path, new_score))

                if len(new_path) >= 3:
                    completed_paths.append({"nodes": new_path, "score": new_score})

        # Sort by score descending
        completed_paths.sort(key=lambda p: p["score"], reverse=True)
        return completed_paths[:TOP_K_PATHS]

    def get_context_for_query(
        self,
        query: str,
        session_id: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """
        Public interface: returns top-k most relevant nodes for a query.
        Used by the Omniverse service for LLM command generation.
        """
        neo4j = get_neo4j()
        keywords = query.lower().split()[:5]
        all_nodes = neo4j.get_all_nodes(session_id)

        # Score nodes by keyword relevance
        scored = []
        for node in all_nodes:
            label = node.get("label", "").lower()
            desc = node.get("description", "").lower()
            score = sum(1.0 for kw in keywords if kw in label or kw in desc)
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]
