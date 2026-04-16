"""
Scenario Agent — Phase 2
Generates complex edge-case queries to test the depth and coverage of the
knowledge graph, then evaluates answer quality as a proxy for graph completeness.
"""
import asyncio
import logging
from typing import List, Dict

from .base import BaseAgent, EventEmitter
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j

logger = logging.getLogger(__name__)

DEFAULT_SCENARIOS = [
    "What is the causal chain from a 3-day heatwave (T > 38°C) to berry quality degradation?",
    "How does pre-dawn drip irrigation affect anthocyanin accumulation under UV-B stress?",
    "What triggers heat shock protein expression and how does it compete with anthocyanin synthesis?",
    "Under what conditions does water deficit increase berry quality rather than decrease it?",
    "How should the digital twin adjust irrigation when temperature crosses 35°C at véraison?",
]


class ScenarioAgent(BaseAgent):
    name = "scenario"
    display_name = "Scenario Agent"
    phase = 2
    icon = "🎭"

    async def run(self, session_id: str, domain: str = "viticulture", **kwargs):
        await self.started()
        await self.thinking("Generating edge-case reasoning scenarios to stress-test the knowledge graph…")
        await self._sleep(0.8)

        neo4j = get_neo4j()
        ollama = get_ollama()

        # Summarise graph for scenario generation
        nodes = neo4j.get_all_nodes(session_id)
        graph_summary = ", ".join(n.get("label", n.get("id", "")) for n in nodes[:15])

        # Generate scenarios via LLM
        await self.thinking("Asking LLM to generate domain-specific multi-hop queries…")
        result = await ollama.generate_scenarios(domain, graph_summary, model=self.model)
        queries = result.get("queries", DEFAULT_SCENARIOS)[:5]

        if not queries:
            queries = DEFAULT_SCENARIOS

        await self.thinking(f"Running {len(queries)} scenario(s) against the knowledge graph…")
        await self._sleep(0.5)

        total_scenarios = len(queries)
        passed = 0
        scenario_results = []

        for idx, query in enumerate(queries):
            if self._cancelled:
                break

            await self.progress(idx / total_scenarios, f"Testing scenario {idx + 1}/{total_scenarios}")
            await self.thinking(f'Scenario {idx + 1}: "{query[:80]}…"')
            await self._sleep(0.6)

            # Retrieve context nodes (simplified: use all nodes for now)
            context_nodes = nodes[:12]

            # Ask LLM to answer the query
            answer_data = await ollama.answer_query(query, context_nodes, model=self.model)

            confidence = answer_data.get("confidence", 0.75)
            contradicts = answer_data.get("contradicts_hard_edge", False)
            reasoning_chain = answer_data.get("reasoning_chain", [])
            nodes_used = answer_data.get("nodes_used", [])

            scenario_passed = confidence >= 0.6 and not contradicts
            if scenario_passed:
                passed += 1

            self.stats["scenarios_tested"] += 1
            scenario_results.append({
                "query": query,
                "answer": answer_data.get("answer", ""),
                "confidence": confidence,
                "contradicts_hard_edge": contradicts,
                "reasoning_chain": reasoning_chain,
                "nodes_used": nodes_used,
                "passed": scenario_passed,
            })

            await self.emit("agent.scenario_result", {
                "scenario_index": idx,
                "query": query,
                "answer": answer_data.get("answer", ""),
                "confidence": confidence,
                "reasoning_chain": reasoning_chain,
                "nodes_used": nodes_used,
                "passed": scenario_passed,
                "contradicts_hard_edge": contradicts,
            })
            await self._sleep(0.4)

        accuracy = passed / total_scenarios if total_scenarios > 0 else 0.0
        await self.progress(1.0, "Scenario testing complete")
        await self._sleep(0.5)

        await self.emit("agent.scenario_summary", {
            "total": total_scenarios,
            "passed": passed,
            "logical_chain_accuracy": round(accuracy, 3),
            "results": scenario_results,
        })
        await self.completed(
            f"Scenario testing complete: {passed}/{total_scenarios} passed. "
            f"Logical Chain Accuracy: {accuracy:.1%}"
        )
        return accuracy
