"""
run_fact_check.py
=================
Runs the topk_csp_retriever (cypher_path_search) on a single fact-check question.
Uses the physics_small benchmark so Neo4j only needs the 10K-node graph loaded.

Run from the project root:
    python run_fact_check.py
"""
import os
import logging
from dotenv import load_dotenv
from polyg import GraphRAG, QueryParam
from polyg.storage import Neo4jStorage

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.WARNING)
logging.getLogger("polyg").setLevel(logging.INFO)

# ── Neo4j + model config ───────────────────────────────────────────────────────
neo4j_config = {
    "neo4j_url":  os.environ.get("NEO4J_URL",      "bolt://localhost:7687"),
    "neo4j_auth": (
        os.environ.get("NEO4J_USER",     "neo4j"),
        os.environ.get("NEO4J_PASSWORD", "password"),
    ),
}

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL       = "ollama_chat/llama3:8b-instruct-q4_K_M"

rag = GraphRAG(
    dataset="physics_small",            # matches the Neo4j label used at import time
    model=MODEL,
    model_max_token_size=32768,
    model_sampling_params={
        "api_base":   OLLAMA_HOST,
        "max_tokens": 1024,
    },
    graph_storage_cls=Neo4jStorage,
    addon_params=neo4j_config,
)

# ── Question (from benchmarks/physics_small/fact_check.jsonl, qid=0) ──────────
question   = "Have the author 'Karoly Szego' cited or been cited by the work of the author 'L. Foldy'?"
id_mapping = {
    "Karoly Szego": "2116127405",
    "L. Foldy":     "2149150795",
}

param = QueryParam(
    mode="local",
    traversal_type="cypher_path_search",   # forces topk_csp_retriever directly
    edge_depth=1,
    local_context_length=10000,
    response_type="a concise paragraph",
    failure_retries=2,
)

if __name__ == "__main__":
    print(f"Question : {question}")
    print(f"Entities : {id_mapping}")
    print(f"Retriever: cypher_path_search (topk_csp_retriever)")
    print("=" * 70)

    response, duration, tokens, api_calls, answer_list = rag.query(
        question, id_mapping, param=param
    )

    print("\nAnswer:")
    print(response)
    print("=" * 70)
    print(f"Duration : {duration:.2f}s")
    print(f"Tokens   : {tokens}")
    print(f"API calls: {api_calls}")
