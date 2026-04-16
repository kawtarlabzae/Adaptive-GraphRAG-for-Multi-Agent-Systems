"""
Ollama LLM service with graceful fallback to rule-based extraction
when Ollama is not available.
"""
import os
import json
import re
import logging
import time
import httpx
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
TIMEOUT = 120.0
RECHECK_INTERVAL = 30.0   # seconds between availability re-checks


class OllamaService:
    def __init__(self):
        self.base_url = OLLAMA_URL
        self.available = False
        self._last_check: float = 0.0
        self._check_availability()

    def _check_availability(self):
        self._last_check = time.monotonic()
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                if r.status_code == 200:
                    if not self.available:
                        logger.info("Ollama available at %s", self.base_url)
                    self.available = True
                    return
        except Exception as e:
            logger.warning("Ollama not available (%s). Using rule-based fallback.", e)
        self.available = False

    def _ensure_available(self):
        """Re-check availability if it was previously False and the interval has elapsed."""
        if not self.available and (time.monotonic() - self._last_check) > RECHECK_INTERVAL:
            self._check_availability()

    async def generate(self, prompt: str, model: str = DEFAULT_MODEL,
                       system: str = "") -> str:
        self._ensure_available()
        if not self.available:
            logger.warning("Ollama unavailable — skipping LLM call. Start Ollama with: ollama serve")
            return ""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": model, "messages": messages, "stream": False}
                )
                data = r.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error("Ollama generate error: %s", e)
            return ""

    async def extract_graph(self, text: str, model: str = DEFAULT_MODEL) -> Dict:
        """Extract knowledge graph entities and relationships from text."""
        system = (
            "You are an expert knowledge graph engineer specializing in viticulture and precision agriculture. "
            "You extract structured entity-relationship data from scientific text and return ONLY valid JSON."
        )
        prompt = f"""Extract a knowledge graph from the following viticulture text.
Return ONLY valid JSON matching this schema exactly (no extra text):
{{
  "entities": [
    {{
      "id": "snake_case_unique_id",
      "label": "Human Readable Name",
      "type": "molecule|process|variable|condition|technology|biological_component|metric",
      "description": "One sentence description"
    }}
  ],
  "relationships": [
    {{
      "from_id": "entity_id",
      "to_id": "entity_id",
      "type": "AFFECTS|CAUSES|REQUIRES|PROMOTES|INHIBITS|CONTROLS|PRODUCES|DETERMINES|INCREASES_WITH",
      "weight": 0.85,
      "condition": "optional condition string or null"
    }}
  ]
}}

Text:
{text}

JSON:"""
        raw = await self.generate(prompt, model=model, system=system)
        return self._parse_json_response(raw, default={"entities": [], "relationships": []})

    async def find_conflicts(self, text_a: str, text_b: str, model: str = DEFAULT_MODEL) -> Dict:
        """Find contradictions between two text passages."""
        system = (
            "You are a scientific fact-checker. You identify contradictions and conflicting claims "
            "between scientific sources. Return ONLY valid JSON."
        )
        prompt = f"""Compare these two passages and identify any factual contradictions or conflicting claims.
Return ONLY valid JSON:
{{
  "conflicts": [
    {{
      "topic": "topic of conflict",
      "source_a": "claim from passage A with value",
      "source_b": "claim from passage B with value",
      "severity": "low|medium|high",
      "resolution": "suggested resolution"
    }}
  ]
}}
If no conflicts exist return {{"conflicts": []}}.

Passage A:
{text_a}

Passage B:
{text_b}

JSON:"""
        raw = await self.generate(prompt, model=model, system=system)
        return self._parse_json_response(raw, default={"conflicts": []})

    async def generate_scenarios(self, domain: str, graph_summary: str,
                                 model: str = DEFAULT_MODEL) -> Dict:
        """Generate test queries for graph validation."""
        prompt = f"""Generate 5 complex multi-hop reasoning queries for a {domain} knowledge graph.
These queries should test causal chain reasoning across multiple entities.
Graph contains: {graph_summary}

Return ONLY valid JSON:
{{
  "queries": [
    "Query text here"
  ]
}}

JSON:"""
        raw = await self.generate(prompt, model=model)
        return self._parse_json_response(raw, default={"queries": []})

    async def answer_query(self, query: str, context_nodes: List[Dict],
                           model: str = DEFAULT_MODEL) -> Dict:
        """Answer a query using retrieved graph context."""
        context_str = "\n".join(
            f"- {n.get('label', n.get('id'))}: {n.get('description', '')}"
            for n in context_nodes
        )
        prompt = f"""Using the following knowledge graph context, answer the query.
Identify if the answer contradicts any physical laws (hard constraints).

Context nodes:
{context_str}

Query: {query}

Return ONLY valid JSON:
{{
  "answer": "detailed answer",
  "reasoning_chain": ["step 1", "step 2", "step 3"],
  "confidence": 0.85,
  "contradicts_hard_edge": false,
  "nodes_used": ["node_id1", "node_id2"]
}}

JSON:"""
        raw = await self.generate(prompt, model=model)
        return self._parse_json_response(raw, default={
            "answer": "",
            "reasoning_chain": [],
            "confidence": 0.0,
            "contradicts_hard_edge": False,
            "nodes_used": []
        })

    async def generate_omniverse_command(self, sensor_data: Dict,
                                         graph_context: List[Dict],
                                         model: str = DEFAULT_MODEL) -> Dict:
        """Generate Omniverse simulation command from sensor data + graph."""
        graph_str = "\n".join(
            f"- {n.get('label')}: {n.get('description', '')}"
            for n in graph_context[:10]
        )
        prompt = f"""You are an AI controller for a Smart Vineyard Digital Twin in NVIDIA Omniverse.
Based on sensor readings and knowledge graph context, generate a precise simulation command.

Current Sensor Data:
- Temperature: {sensor_data.get('temperature', 35):.1f}°C
- Humidity: {sensor_data.get('humidity', 40):.0f}%
- Soil Moisture: {sensor_data.get('soil_moisture', 35):.0f}%
- Anthocyanin Index: {sensor_data.get('anthocyanin_index', 60):.0f}%
- UV Index: {sensor_data.get('uv_index', 7):.1f}

Knowledge Graph Context:
{graph_str}

Return ONLY valid JSON:
{{
  "command": "IRRIGATE|SHADE|MONITOR|ALERT|HARVEST_PREP",
  "parameters": {{
    "zone": "zone_1|zone_2|zone_3|all",
    "duration_minutes": 30,
    "intensity": "low|medium|high",
    "reason": "Explanation referencing graph knowledge"
  }},
  "predicted_outcome": "Expected result in 24-48h",
  "confidence": 0.87,
  "usd_update": "Description of 3D scene update"
}}

JSON:"""
        raw = await self.generate(prompt, model=model)
        return self._parse_json_response(raw, default=None)

    def _parse_json_response(self, raw: str, default: Any = None) -> Any:
        """Robustly extract JSON from LLM response."""
        if not raw:
            return default
        # Try direct parse
        try:
            return json.loads(raw.strip())
        except Exception:
            pass
        # Try extracting JSON block
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        # Try array block
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        logger.warning("Failed to parse JSON from LLM response: %s...", raw[:200])
        return default


_ollama: Optional[OllamaService] = None


def get_ollama() -> OllamaService:
    global _ollama
    if _ollama is None:
        _ollama = OllamaService()
    return _ollama
