"""
DRIFT: Dynamic Reasoning and Inference with Flexible Traversal
Inspired by Microsoft's GraphRAG DRIFT search.

Designed for nested / complex questions that require iterative graph exploration.

Three phases:
  A. Primer  — BFS-2 from seed entities → broad answer + follow-up questions
  B. Follow-Up — for each follow-up: entity text-search + BFS-1 → refined answer
  C. Synthesis — combine all intermediate answers into a final hierarchical response
"""

import asyncio
import json
import re
import time
from typing import Callable, List, Tuple

from ..base import BaseGraphStorage, QueryParam
from ..prompt import PROMPTS
from ..utils import logger, num_tokens

# ── tuneable constants ────────────────────────────────────────────────────────
DRIFT_MAX_FOLLOW_UPS_PER_ITER = 3   # follow-up questions explored per depth level
DRIFT_MAX_DEPTH = 2                  # maximum follow-up depth (iterations)
DRIFT_CONF_THRESHOLD = 0.8           # confidence above which we stop drilling down
DRIFT_CONTEXT_NODE_LIMIT = 80        # max nodes to include in a context window
DRIFT_CONTEXT_EDGE_LIMIT = 150       # max edges to include in a context window
# ─────────────────────────────────────────────────────────────────────────────


async def _get_bfs_context(
    graph: BaseGraphStorage,
    node_ids: dict,
    depth: int = 1,
) -> str:
    """
    Perform BFS up to `depth` hops from nodes in `node_ids` (a {name: id} or {id: id} dict).
    Returns a human-readable context string listing entities and relations.
    """
    all_nodes: set = set(node_ids.values())
    seed: set = set(node_ids.values())
    unique_edges: set = set()

    for _ in range(depth):
        if not seed:
            break
        edges_lists = await asyncio.gather(*[graph.get_node_edges(nid) for nid in seed])
        next_seed: set = set()
        for edges in edges_lists:
            for e in edges:
                unique_edges.add(frozenset(e.items()))
                for nid in (e.get("src_id"), e.get("tgt_id")):
                    if nid and nid not in all_nodes:
                        next_seed.add(nid)
        all_nodes.update(next_seed)
        seed = next_seed

    # Fetch node data (capped)
    node_list = list(all_nodes)[: DRIFT_CONTEXT_NODE_LIMIT]
    nodes_data = await asyncio.gather(*[graph.get_node(nid) for nid in node_list])
    nodes_data = [n for n in nodes_data if n is not None]

    # Build name lookup for edge formatting
    name_map = {n["id"]: n.get("name", n["id"]) for n in nodes_data}

    # Format entities
    lines = ["**Entities:**"]
    for n in nodes_data:
        desc = (n.get("description", "") or "")[:200]
        lines.append(
            f"- [{n.get('node_type', '')}] {n.get('name', '')} | {desc}"
        )

    # Format relations
    lines.append("\n**Relations:**")
    edge_list = [dict(e) for e in list(unique_edges)[: DRIFT_CONTEXT_EDGE_LIMIT]]
    for e in edge_list:
        src = name_map.get(e.get("src_id", ""), e.get("src_id", ""))
        tgt = name_map.get(e.get("tgt_id", ""), e.get("tgt_id", ""))
        lines.append(f"- {src} --[{e.get('relation', '')}]--> {tgt}")

    return "\n".join(lines)


def _keyword_variants(term: str) -> List[str]:
    """
    Return a small set of morphological variants for `term` so that a
    CONTAINS search is less brittle.  No external NLP library required.

    Examples:
      "superconductor"  → ["superconductor", "superconducti"]   (root prefix)
      "junctions"       → ["junctions", "junction"]             (strip trailing -s/-es)
      "published"       → ["published", "publish"]              (strip -ed)
    """
    variants = [term]
    lower = term.lower()

    # Strip common suffixes to expose a shared root
    for suffix in ("tion", "tions", "ity", "ities", "ing", "ings",
                   "ed", "er", "ers", "ors", "or", "ness", "ment",
                   "s", "es"):
        if lower.endswith(suffix) and len(lower) - len(suffix) >= 4:
            root = lower[: len(lower) - len(suffix)]
            if root not in variants:
                variants.append(root)
            break  # one suffix strip is enough

    # Also add a 6-char prefix so partial word matches work
    if len(lower) > 6:
        prefix = lower[:6]
        if prefix not in variants:
            variants.append(prefix)

    return variants


async def _search_entities_by_text(
    graph: BaseGraphStorage,
    namespace: str,
    text: str,
    limit: int = 5,
) -> dict:
    """
    Search Neo4j for nodes whose name or description matches keywords from `text`.

    Strategy (in order, stops as soon as results are found):
      1. Exact quoted phrases  → single CONTAINS per phrase
      2. Significant keywords  → OR-joined CONTAINS across name AND description
      3. Morphological variants of each keyword  → broader CONTAINS sweep
    Returns {name: id}.
    """
    # ── Extract candidate terms ────────────────────────────────────────────────
    quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", text)
    exact_phrases: List[str] = [q[0] or q[1] for q in quoted]

    _stop = {
        "what", "which", "where", "when", "how", "who", "that", "this",
        "with", "from", "about", "have", "been", "were", "are", "the",
        "and", "for", "its", "their", "does", "between", "both", "also",
        "would", "could", "should", "there", "these", "those",
    }
    keywords: List[str] = [
        w for w in re.split(r"\W+", text.lower())
        if len(w) > 4 and w not in _stop
    ][:5]

    found: dict = {}

    async def _run_cypher(cypher: str) -> None:
        try:
            records = await graph.exec_query(cypher)
            for r in records:
                if r.get("name") and r.get("id"):
                    found[r["name"]] = r["id"]
        except Exception as exc:
            logger.warning(f"DRIFT entity search failed: {exc}")

    # ── Strategy 1: exact quoted phrases ──────────────────────────────────────
    for phrase in exact_phrases[:2]:
        safe = phrase.replace("'", "\\'")
        await _run_cypher(
            f"MATCH (n:{namespace}) "
            f"WHERE toLower(n.name) CONTAINS toLower('{safe}') "
            f"RETURN n.id AS id, n.name AS name LIMIT {limit}"
        )
    if found:
        return found

    # ── Strategy 2: OR-joined keyword search over name AND description ─────────
    if keywords:
        name_clauses = " OR ".join(
            f"toLower(n.name) CONTAINS toLower('{w.replace(chr(39), chr(92)+chr(39))}')"
            for w in keywords
        )
        desc_clauses = " OR ".join(
            f"toLower(n.description) CONTAINS toLower('{w.replace(chr(39), chr(92)+chr(39))}')"
            for w in keywords
        )
        await _run_cypher(
            f"MATCH (n:{namespace}) "
            f"WHERE ({name_clauses}) OR ({desc_clauses}) "
            f"RETURN n.id AS id, n.name AS name LIMIT {limit * 2}"
        )
    if found:
        return found

    # ── Strategy 3: morphological variants per keyword ────────────────────────
    for kw in keywords[:3]:
        for variant in _keyword_variants(kw):
            safe = variant.replace("'", "\\'")
            await _run_cypher(
                f"MATCH (n:{namespace}) "
                f"WHERE toLower(n.name) CONTAINS toLower('{safe}') "
                f"   OR toLower(n.description) CONTAINS toLower('{safe}') "
                f"RETURN n.id AS id, n.name AS name LIMIT {limit}"
            )
        if found:
            return found

    return found  # {name: id}


def _parse_json(response: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response string.
    Falls back to heuristic text extraction when the model doesn't produce
    valid JSON (common with small 8-B class models).
    """
    # 1. Strict: ```json ... ``` block
    try:
        m = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception:
        pass

    # 2. Lenient: first { … } in the response
    try:
        m = re.search(r"\{.*\}", response, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass

    # 3. Heuristic fallback for models that write prose instead of JSON.
    #    Extract numbered / bulleted follow-up questions from the text.
    result: dict = {}

    # Pull "initial_answer" – everything before the first numbered item or bullet
    intro_m = re.split(r"\n\s*(?:\d+[\.\)]|-|\*)\s+", response, maxsplit=1)
    if intro_m:
        result["initial_answer"] = intro_m[0].strip()

    # Pull follow-up questions: lines starting with number/bullet that end with "?"
    fu_candidates = re.findall(
        r"(?:^|\n)\s*(?:\d+[\.\)]|-|\*)\s*(.+?\?)",
        response,
        re.MULTILINE,
    )
    if fu_candidates:
        result["follow_up_questions"] = [q.strip() for q in fu_candidates[:3]]

    # Pull confidence value if mentioned
    conf_m = re.search(r"confidence[:\s]+([0-9]\.[0-9]+)", response, re.IGNORECASE)
    if conf_m:
        try:
            result["confidence"] = float(conf_m.group(1))
        except ValueError:
            pass

    # Pull refined_answer label
    ref_m = re.search(
        r"refined[_\s]answer[:\s]+(.+?)(?:\n\n|\Z)", response, re.IGNORECASE | re.DOTALL
    )
    if ref_m:
        result["refined_answer"] = ref_m.group(1).strip()

    return result


# ─────────────────────────────────────────────────────────────────────────────


async def drift_search(
    query: str,
    id_mapping: dict,
    graph: BaseGraphStorage,
    model_func: Callable,
    token_encoder,
    param: QueryParam,
    global_config: dict,
) -> Tuple[str, float, int, int, list]:
    """
    Run DRIFT search for a nested / complex question.

    Returns (response, duration_sec, total_tokens, total_api_calls, answer_list).
    """
    t0 = time.time()
    total_tokens = 0
    total_api_calls = 0
    namespace = global_config["dataset"]

    # ═══════════════════════════════════════════════════════════════
    # PHASE A — PRIMER
    # ═══════════════════════════════════════════════════════════════
    logger.info("DRIFT Phase A: Primer")
    primer_context = await _get_bfs_context(graph, id_mapping, depth=2)

    primer_prompt = PROMPTS["drift_primer"].format(
        question=query,
        context=primer_context,
    )
    primer_raw = await model_func(prompt=primer_prompt)
    total_api_calls += 1
    total_tokens += num_tokens(primer_prompt, token_encoder)

    primer_data = _parse_json(primer_raw)
    initial_answer: str = primer_data.get("initial_answer", primer_raw)
    follow_ups: List[str] = primer_data.get("follow_up_questions", [])[:DRIFT_MAX_FOLLOW_UPS_PER_ITER]
    logger.info(f"DRIFT Primer done. {len(follow_ups)} follow-up questions generated.")

    # ═══════════════════════════════════════════════════════════════
    # PHASE B — ITERATIVE FOLLOW-UP
    # ═══════════════════════════════════════════════════════════════
    all_answers = [{"question": query, "answer": initial_answer, "level": 0}]
    current_follow_ups = follow_ups

    for depth in range(DRIFT_MAX_DEPTH):
        if not current_follow_ups:
            break
        logger.info(f"DRIFT Phase B depth {depth + 1}: {len(current_follow_ups)} follow-ups")
        next_follow_ups: List[str] = []

        for sub_q in current_follow_ups[:DRIFT_MAX_FOLLOW_UPS_PER_ITER]:
            # Find entities relevant to this follow-up
            found_ents = await _search_entities_by_text(graph, namespace, sub_q)
            if found_ents:
                fu_context = await _get_bfs_context(graph, found_ents, depth=1)
            else:
                fu_context = await _get_bfs_context(graph, id_mapping, depth=1)

            history_str = "\n\n".join(
                f"Q: {a['question']}\nA: {a['answer']}"
                for a in all_answers[-3:]
            )

            fu_prompt = PROMPTS["drift_follow_up"].format(
                question=query,
                sub_question=sub_q,
                context=fu_context,
                history=history_str,
            )
            fu_raw = await model_func(prompt=fu_prompt)
            total_api_calls += 1
            total_tokens += num_tokens(fu_prompt, token_encoder)

            fu_data = _parse_json(fu_raw)
            refined_answer: str = fu_data.get("refined_answer", fu_raw)
            confidence: float = float(fu_data.get("confidence", 0.5))
            new_fus: List[str] = fu_data.get("follow_up_questions", [])

            all_answers.append({
                "question": sub_q,
                "answer": refined_answer,
                "confidence": confidence,
                "level": depth + 1,
            })
            logger.info(
                f"  sub-Q '{sub_q[:60]}...' → confidence={confidence:.2f}"
            )

            if confidence < DRIFT_CONF_THRESHOLD:
                next_follow_ups.extend(new_fus[:2])

        current_follow_ups = next_follow_ups

    # ═══════════════════════════════════════════════════════════════
    # PHASE C — SYNTHESIS
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"DRIFT Phase C: Synthesizing {len(all_answers)} intermediate answers")
    answers_str = "\n\n".join(
        f"[Level {a['level']}] Q: {a['question']}\nA: {a['answer']}"
        for a in all_answers
    )
    synth_prompt = PROMPTS["drift_synthesis"].format(
        question=query,
        answers=answers_str,
        response_type=param.response_type,
    )
    final_response = await model_func(prompt=synth_prompt)
    total_api_calls += 1
    total_tokens += num_tokens(synth_prompt, token_encoder)

    duration = time.time() - t0
    logger.info(
        f"DRIFT complete: {total_api_calls} API calls, "
        f"{total_tokens} tokens, {duration:.1f}s"
    )
    return final_response, duration, total_tokens, total_api_calls, []
