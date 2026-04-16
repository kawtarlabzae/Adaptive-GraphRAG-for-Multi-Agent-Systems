"""
Pruning Agent — Phase 2
Monitors graph traversal utility and removes low-value nodes that clutter
the context window without contributing to reasoning paths.
Produces the Task-Optimized sub-graph for production deployment.
"""
import asyncio
import logging
from typing import List, Dict

from .base import BaseAgent, EventEmitter
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)


class PruningAgent(BaseAgent):
    name = "pruning"
    display_name = "Pruning Agent"
    phase = 2
    icon = "✂️"

    async def run(self, session_id: str, utility_threshold: float = 0.3, **kwargs):
        await self.started()
        await self.thinking(
            "Analysing knowledge graph topology to identify low-utility nodes…"
        )
        await self._sleep(0.8)

        neo4j = get_neo4j()
        all_nodes = neo4j.get_all_nodes(session_id)
        all_edges = neo4j.get_all_edges(session_id)
        total_nodes = len(all_nodes)

        if total_nodes == 0:
            await self.completed("Graph is empty — nothing to prune.")
            return

        await self.thinking(
            f"Evaluating utility scores for {total_nodes} nodes using degree centrality + "
            "edge weight analysis…"
        )
        await self._sleep(0.6)

        # Build adjacency for utility scoring
        edge_index: Dict[str, List] = {n.get("id", ""): [] for n in all_nodes}
        total_weight = 0.0
        for edge in all_edges:
            fn = edge.get("from_node", "")
            tn = edge.get("to_node", "")
            w = float(edge.get("weight", 1.0))
            if fn in edge_index:
                edge_index[fn].append((tn, w))
            if tn in edge_index:
                edge_index[tn].append((fn, w))
            total_weight += w

        avg_weight = total_weight / max(len(all_edges), 1)

        to_prune = []
        keep = []

        for node in all_nodes:
            node_id = node.get("id", "")
            degree = len(edge_index.get(node_id, []))
            neighbour_weights = [w for _, w in edge_index.get(node_id, [])]
            avg_neighbour_w = sum(neighbour_weights) / max(len(neighbour_weights), 1)

            # Utility score: normalised combination of degree and edge weight
            max_degree = max(len(v) for v in edge_index.values()) or 1
            utility = (degree / max_degree) * 0.6 + (avg_neighbour_w / 1.0) * 0.4

            if degree == 0 or (utility < utility_threshold and degree < 2):
                to_prune.append((node_id, node.get("label", node_id), utility))
            else:
                keep.append((node_id, utility))

        await self.thinking(
            f"Found {len(to_prune)} low-utility node(s) below threshold {utility_threshold:.2f}. "
            f"Keeping {len(keep)} nodes."
        )
        await self._sleep(0.5)

        # Execute pruning
        for idx, (node_id, label, utility) in enumerate(to_prune):
            if self._cancelled:
                break
            await self.progress(idx / max(len(to_prune), 1), f"Pruning: {label}")
            await self.thinking(f"Removing node '{label}' (utility={utility:.3f} < {utility_threshold})")
            neo4j.delete_node(node_id, session_id)
            self.stats["nodes_pruned"] += 1
            await self.emit("agent.node_pruned", {
                "node_id": node_id,
                "label": label,
                "utility_score": round(utility, 3),
                "reason": f"Utility {utility:.3f} below threshold {utility_threshold}",
            })
            await self._sleep(0.3)

        # Calculate context efficiency
        total_after = total_nodes - self.stats["nodes_pruned"]
        context_efficiency = 1.0 - (self.stats["nodes_pruned"] / max(total_nodes, 1))
        # Represent efficiency as the fraction of answer-critical tokens retained
        critical_fraction = len(keep) / max(total_nodes, 1)

        await self.progress(1.0, "Pruning complete")
        await self._sleep(0.5)

        await self.emit("agent.pruning_summary", {
            "nodes_before": total_nodes,
            "nodes_pruned": self.stats["nodes_pruned"],
            "nodes_after": total_after,
            "context_efficiency": round(critical_fraction, 3),
            "kept_nodes": [k[0] for k in keep],
        })
        await self.completed(
            f"Task-optimised sub-graph ready: {total_after}/{total_nodes} nodes retained. "
            f"Context efficiency: {critical_fraction:.1%}"
        )
        return critical_fraction
