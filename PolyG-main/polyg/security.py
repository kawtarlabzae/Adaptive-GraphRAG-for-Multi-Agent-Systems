"""
Cypher query security and normalisation layer.

Two responsibilities:
  1. sanitize_cypher  — rejects mutative statements (DELETE, MERGE, CREATE …)
  2. normalize_cypher — fixes common LLM hallucinations before the query runs:
       • wrong relation type names  (cites → reference, etc.)
       • missing dataset label on bare node labels  (:paper → :physics_small:paper)
       • integer IDs that should be strings  ({id: 123} → {id: '123'})
       • inline comments that confuse some Neo4j versions  (// … stripped)
"""

import re


# ── 1. Mutative-keyword guard ──────────────────────────────────────────────────

_MUTATIVE = re.compile(
    r"\b("
    r"DELETE|DETACH\s+DELETE"
    r"|MERGE"
    r"|CREATE"
    r"|SET"
    r"|REMOVE"
    r"|DROP"
    r"|LOAD\s+CSV"
    r"|CALL\s+apoc\."
    r"|CALL\s+db\.index\.(fulltext|vector)\.create"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_cypher(query: str) -> str:
    """Raise ValueError if `query` contains any mutative Cypher keyword."""
    match = _MUTATIVE.search(query)
    if match:
        raise ValueError(
            f"Rejected LLM-generated Cypher: contains forbidden keyword "
            f"'{match.group().strip()}'. Only READ operations are allowed.\n{query}"
        )
    return query


# ── 2. Relation-name normalisation ────────────────────────────────────────────

# Maps every hallucinated relation name → the real Neo4j relationship type.
# Keys are lowercase; matching is case-insensitive.
_RELATION_ALIASES: dict[str, str] = {
    # citation hallucinations
    "cites":         "reference",
    "cite":          "reference",
    "cited":         "reference",
    "references":    "reference",
    "refs":          "reference",
    "referenced_by": "cited_by",
    "cited_by_ref":  "cited_by",
    "citedby":       "cited_by",
    "cited":         "cited_by",   # ambiguous but safer default
    # authorship hallucinations
    "writes":        "paper",
    "written_by":    "author",
    "authored_by":   "author",
    "authored":      "author",
    "has_author":    "author",
    # venue hallucinations
    "published_in":  "venue",
    "published_at":  "venue",
    "publishes":     "paper",
    # property masquerading as relation
    "description":   None,   # not a relation at all — remove the clause
    "abstract":      None,
    "title":         None,
}

# Pattern: [:cites] or [:cites|something] inside a relationship pattern
_REL_PATTERN = re.compile(r"\[:([A-Za-z_|]+)\]")


def _fix_relation(match: re.Match) -> str:
    """Replace each pipe-separated relation name with its canonical form."""
    inner = match.group(1)          # e.g. "cites|referenced_by"
    parts = inner.split("|")
    fixed = []
    for part in parts:
        canonical = _RELATION_ALIASES.get(part.lower())
        if canonical is None and part.lower() in _RELATION_ALIASES:
            # mapped to None → skip (not a real relation)
            continue
        elif canonical is not None:
            fixed.append(canonical)
        else:
            fixed.append(part)      # already correct
    if not fixed:
        # every part was invalid — replace with a safe fallback
        fixed = ["reference"]
    return f"[:{('|'.join(fixed))}]"


# ── 3. Label normalisation ────────────────────────────────────────────────────

def _fix_labels(query: str, dataset: str) -> str:
    """
    Ensure every bare node-type label inside (...) node patterns gets the
    dataset prefix.  e.g.  :paper  →  :physics_small:paper

    IMPORTANT: must NOT touch relationship-type expressions inside [...] since
    Cypher does not allow ':' as a label separator there.
    e.g.  [:author]  must stay  [:author],  not become  [:physics_small:author].
    """
    # Step 1 – stash every [...] block so label substitution cannot touch it.
    _stashed: list[str] = []

    def _stash(m: re.Match) -> str:  # type: ignore[type-arg]
        _stashed.append(m.group(0))
        return f"\x00REL{len(_stashed) - 1}\x00"

    protected = re.sub(r"\[[^\]]*\]", _stash, query)

    # Step 2 – apply label prefix only in the remaining (node-pattern) text.
    for node_type in ("author", "paper", "venue"):
        pat = re.compile(
            rf"(?<!:{re.escape(dataset)}):({re.escape(node_type)})\b"
        )
        protected = pat.sub(rf":{dataset}:\1", protected)

    # Step 3 – restore stashed relationship blocks verbatim.
    for idx, rel in enumerate(_stashed):
        protected = protected.replace(f"\x00REL{idx}\x00", rel)

    return protected


# ── 4. Integer-ID fix ─────────────────────────────────────────────────────────

_INT_ID = re.compile(r"\{id:\s*(\d+)\s*\}")


def _fix_int_ids(query: str) -> str:
    """Convert {id: 1234567} → {id: '1234567'} (IDs are always strings)."""
    return _INT_ID.sub(lambda m: f"{{id: '{m.group(1)}'}}", query)


# ── 5. Strip inline comments ──────────────────────────────────────────────────

_COMMENT = re.compile(r"//[^\n]*")


# ── 6. WHERE-clause relationship-pattern fix ─────────────────────────────────

# Cypher 5 does not allow relationship patterns directly inside WHERE.
# e.g.  WHERE n-[:reference]->m  is invalid.
# Match the entire WHERE block: from WHERE to the line before RETURN/WITH/ORDER.
# We strip line-by-line so we don't accidentally eat RETURN clauses.
_WHERE_REL_LINE = re.compile(
    r"^\s*WHERE\b.*-\s*\[:[A-Za-z_|]+\]\s*-?>.*$",
    re.IGNORECASE | re.MULTILINE,
)
# Also remove continuation lines of such a WHERE (OR / AND continuations on next lines)
_WHERE_CONTINUATION = re.compile(
    r"^\s*(OR|AND)\b.*-\s*\[:[A-Za-z_|]+\]\s*-?>.*$",
    re.IGNORECASE | re.MULTILINE,
)


def _fix_where_rel_patterns(query: str) -> str:
    """
    Remove lines that contain WHERE / AND / OR with relationship pattern expressions
    (e.g. WHERE a-[:reference]->b) which are invalid in Neo4j 5.x.
    Only the offending lines are removed; the rest of the query (including RETURN) is kept.
    """
    query = _WHERE_REL_LINE.sub("", query)
    query = _WHERE_CONTINUATION.sub("", query)
    return query


# ── 7. RETURN-clause cleanup (remove invalid expressions) ────────────────────

# Remove LLM hallucinations like  type(p1)-[r]->p2  inside RETURN clauses
_INVALID_RETURN_TYPE_EXPR = re.compile(
    r",?\s*type\s*\([^)]+\)\s*-\[.*?\]->\s*\w+",
    re.IGNORECASE,
)

# Remove  , type(r)  and  , TYPE(r)  (relationship type function calls)
_RETURN_TYPE_FUNC = re.compile(r",?\s*\btype\s*\(\s*\w+\s*\)", re.IGNORECASE)


def _fix_invalid_return_exprs(query: str) -> str:
    """Strip common invalid expressions that LLMs put into RETURN clauses."""
    query = _INVALID_RETURN_TYPE_EXPR.sub("", query)
    query = _RETURN_TYPE_FUNC.sub("", query)
    # If RETURN is now empty (e.g. "RETURN "), add a safe default
    query = re.sub(r"\bRETURN\s*$", "RETURN 1", query, flags=re.IGNORECASE)
    return query


# ── 8. RETURN-clause normalisation ───────────────────────────────────────────

# Matches things like  RETURN DISTINCT p.id AS paper_id
# or  RETURN p.id, p.name  when the id column has the wrong alias.
_RETURN_ID_WRONG_ALIAS = re.compile(
    r"\bRETURN\s+(DISTINCT\s+)?(\w+)\.id\s+AS\s+(?!id\b)\w+",
    re.IGNORECASE,
)

# Matches bare  RETURN p.id  (no alias at all)
_RETURN_ID_NO_ALIAS = re.compile(
    r"\bRETURN\s+(DISTINCT\s+)?(\w+)\.id(?!\s+AS\b)",
    re.IGNORECASE,
)


def _fix_return_id(query: str) -> str:
    """
    Ensure that when a Cypher query returns a node's .id, the alias is
    exactly ``id`` so downstream code can do ``row["id"]`` safely.

    Transforms:
      RETURN DISTINCT p.id AS paper_id  →  RETURN DISTINCT p.id AS id
      RETURN p.id                       →  RETURN p.id AS id
    """
    # Fix wrong alias first
    def _fix_alias(m: re.Match) -> str:  # type: ignore[type-arg]
        distinct = m.group(1) or ""
        var = m.group(2)
        return f"RETURN {distinct}{var}.id AS id"

    query = _RETURN_ID_WRONG_ALIAS.sub(_fix_alias, query)

    # Fix missing alias
    def _add_alias(m: re.Match) -> str:  # type: ignore[type-arg]
        distinct = m.group(1) or ""
        var = m.group(2)
        return f"RETURN {distinct}{var}.id AS id"

    query = _RETURN_ID_NO_ALIAS.sub(_add_alias, query)
    return query


# ── Public entry point ────────────────────────────────────────────────────────

def normalize_cypher(query: str, dataset: str) -> str:
    """
    Apply all normalisation passes to an LLM-generated Cypher query.
    Call this BEFORE sanitize_cypher and BEFORE exec_query.

    Fixes:
      - strips // comments
      - wrong relation type names
      - bare :paper/:author/:venue labels missing the dataset prefix (node patterns only)
      - integer IDs → quoted string IDs
      - wrong/missing alias on RETURN n.id  →  RETURN n.id AS id
    """
    query = _COMMENT.sub("", query)          # strip comments first
    query = _REL_PATTERN.sub(_fix_relation, query)
    query = _fix_labels(query, dataset)
    query = _fix_int_ids(query)
    query = _fix_where_rel_patterns(query)
    query = _fix_invalid_return_exprs(query)
    query = _fix_return_id(query)
    # collapse blank lines left by comment stripping
    query = re.sub(r"\n\s*\n", "\n", query).strip()
    return query
