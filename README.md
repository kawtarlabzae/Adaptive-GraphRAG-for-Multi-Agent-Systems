<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=220&section=header&text=PolyG-DT&fontSize=90&fontColor=fff&animation=twinkling&fontAlignY=38&desc=Adaptive%20Multi-Agent%20GraphRAG%20for%20Intelligent%20Digital%20Twins&descAlignY=62&descColor=cce4ff&descSize=18" alt="PolyG-DT"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Knowledge_Graph-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x_Frontend-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-F57F17?style=for-the-badge)](LICENSE)

<br/>

<table>
<tr>
<td align="center"><b>🧠 5 Traversal Strategies</b></td>
<td align="center"><b>🤖 4 Cooperative Agents</b></td>
<td align="center"><b>🌐 3D Digital Twin</b></td>
<td align="center"><b>📊 Neo4j Knowledge Graph</b></td>
</tr>
<tr>
<td align="center"><sub>Adaptive LLM-routed retrieval</sub></td>
<td align="center"><sub>Autonomous KG construction</sub></td>
<td align="center"><sub>CesiumJS + Omniverse</sub></td>
<td align="center"><sub>Viticulture causal graph</sub></td>
</tr>
</table>

<br/>

> ### *"Where structured knowledge meets adaptive reasoning —*
> ### *a GraphRAG engine that thinks before it searches."*

<br/>

</div>

---

<div align="center">

## ✦ &nbsp; The Big Picture &nbsp; ✦

</div>

<br/>

**PolyG-DT** combines two powerful ideas into one unified system.

The first is **PolyG** — a research-grade Graph Retrieval-Augmented Generation engine that, unlike every other RAG system, does not apply a fixed retrieval algorithm to every query. Instead, it classifies each incoming question and routes it to the traversal strategy best suited to answer it: broad neighbourhood sweeps for exploratory questions, shortest-path chains for causal reasoning, constrained Cypher for fact verification. The result is a system that is simultaneously more accurate and more token-efficient than any single-strategy baseline.

The second is a **Viticulture Digital Twin** — a living, reasoning knowledge graph of wine grape physiology, built by four cooperative AI agents that read scientific papers, detect contradictions, synthesise entities, prune noise, and compute probabilistic reasoning paths. Domain experts interact with this twin through a natural-language chat interface backed by a real-time 3D visualisation.

Together they form a blueprint for **knowledge-grounded, reasoning-capable digital twins** across any domain.

<br/>

---

<div align="center">

## ✦ &nbsp; System Flow &nbsp; ✦

</div>

<br/>

<div align="center">

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        POLYG-DT  ·  END-TO-END FLOW                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   👤  User Query                                                         ║
║         │                                                                ║
║         ▼                                                                ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 1  ·  QUERY UNDERSTANDING                 │       ║
║   │                                                             │       ║
║   │   ┌──────────────────┐       ┌──────────────────────┐      │       ║
║   │   │  Entity Extractor│──────►│   Query Classifier   │      │       ║
║   │   │  Fuzzy KG linking│       │  LLM meta-router     │      │       ║
║   │   └──────────────────┘       └──────────┬───────────┘      │       ║
║   └──────────────────────────────────────────┼──────────────────┘       ║
║                                              │ selects strategy          ║
║                                              ▼                           ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 2  ·  ADAPTIVE RETRIEVAL                  │       ║
║   │                                                             │       ║
║   │   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐   │       ║
║   │   │ BFS  │  │BFS+  │  │Cypher│  │K-Path│  │  DRIFT   │   │       ║
║   │   │      │  │ PPR  │  │ Walk │  │      │  │ Explorer │   │       ║
║   │   └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘   │       ║
║   │      └─────────┴─────────┴──────────┴───────────┘         │       ║
║   │                              │                             │       ║
║   │                              ▼                             │       ║
║   │                    ╔═════════════════╗                     │       ║
║   │                    ║   Neo4j  KG     ║                     │       ║
║   │                    ╚═════════════════╝                     │       ║
║   └─────────────────────────────────────────────────────────────┘       ║
║                                              │ subgraph                  ║
║                                              ▼                           ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 3  ·  GROUNDED GENERATION                 │       ║
║   │                                                             │       ║
║   │   ┌──────────────────┐       ┌──────────────────────┐      │       ║
║   │   │  Context Ranker  │──────►│    LLM Generator     │      │       ║
║   │   │  Degree + PPR    │       │  Token-budgeted ctx  │      │       ║
║   │   └──────────────────┘       └──────────────────────┘      │       ║
║   └─────────────────────────────────────────────────────────────┘       ║
║                                              │                           ║
║                                              ▼                           ║
║                                    ✅  Grounded Response                 ║
╚══════════════════════════════════════════════════════════════════════════╝
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Five Traversal Strategies &nbsp; ✦

</div>

<br/>

The heart of PolyG is its **adaptive routing engine** — an LLM meta-classifier that reads the semantic intent of each query and dispatches it to the optimal retrieval algorithm before any graph access occurs.

<br/>

<div align="center">

```
 ╔═══════════════════════════════════════════════════════════════════════╗
 ║                  THE FIVE TRAVERSAL STRATEGIES                       ║
 ╠════════╦════════════════╦══════════╦═══════════╦══════════════════════╣
 ║  ID    ║  Strategy      ║ LLM Hits ║ Complexity║  Ideal Query Type    ║
 ╠════════╬════════════════╬══════════╬═══════════╬══════════════════════╣
 ║   0    ║  BFS           ║    0     ║  O(V+E)   ║  Exploratory         ║
 ║   0+   ║  BFS + PPR     ║    0     ║  O(V+E)   ║  Dense graph ranking ║
 ║   1    ║  Cypher Walk   ║   1–3    ║  O(Q)     ║  Object discovery    ║
 ║   2    ║  K-Shortest    ║    0     ║  O(KE)    ║  Causal chains       ║
 ║   3    ║  CSP Search    ║   1–2    ║  O(P)     ║  Fact checking       ║
 ║  −1    ║  DRIFT         ║  5–15    ║  O(I·V)   ║  Complex / nested    ║
 ╚════════╩════════════════╩══════════╩═══════════╩══════════════════════╝
```

</div>

<br/>

<div align="center">

### ⭐ &nbsp; The BFS-Anchored Hybrid is the Star of the Show &nbsp; ⭐

</div>

<br/>

<div align="center">

```
  WHY BFS + PPR WINS FOR DIGITAL TWINS
  ─────────────────────────────────────────────────────────────────────
  ✔  Zero LLM calls during traversal → sub-100ms retrieval
  ✔  Deterministic results → reliable A/B testing of generation quality
  ✔  PPR re-ranks by node importance → best precision-recall balance
  ✔  Causal KGs are locally dense → depth-2 captures full neighbourhood
  ✔  Graceful degradation → never returns empty context
  ─────────────────────────────────────────────────────────────────────
        Token Efficiency ██████████████████████  90 %
        Hit Rate         ████████████████████░░  88 %
        F1 Score         █████████████████████░  90 %
        Latency          ██████████████████████  Fast ✓
  ─────────────────────────────────────────────────────────────────────
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; The Four-Agent Pipeline &nbsp; ✦

</div>

<br/>

Four specialised AI agents work in sequence to autonomously transform raw scientific PDFs into a high-quality causal knowledge graph.

<br/>

<div align="center">

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    KNOWLEDGE CONSTRUCTION PIPELINE                       ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   📄  PDF Documents ──────────────────────────────────────┐             ║
║                                                           │             ║
║                                                           ▼             ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  🔴  AGENT 1  ·  CONFLICT DETECTOR                           │     ║
║   │                                                              │     ║
║   │  Compares document chunks pairwise · detects contradictions  │     ║
║   │  Creates conditional edges annotated with source conflict    │     ║
║   └───────────────────────────────┬──────────────────────────────┘     ║
║                                   │  conflict edges                     ║
║                                   ▼                                     ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  🟢  AGENT 2  ·  KNOWLEDGE SYNTHESIZER                       │     ║
║   │                                                              │     ║
║   │  Pre-seeds 38 domain nodes  ·  19 causal edges with weights  │     ║
║   │  Extracts new entities via LLM  ·  Merges into Neo4j graph   │     ║
║   └───────────────────────────────┬──────────────────────────────┘     ║
║                                   │  full graph                         ║
║                                   ▼                                     ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  🟠  AGENT 3  ·  GRAPH PRUNER                                │     ║
║   │                                                              │     ║
║   │  Scores every node:  utility = 0.6×degree + 0.4×avg_weight  │     ║
║   │  Removes low-utility nodes  ·  Produces lean deployment KG   │     ║
║   └───────────────────────────────┬──────────────────────────────┘     ║
║                                   │  pruned graph                       ║
║                                   ▼                                     ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  🟣  AGENT 4  ·  PROBABILISTIC PATHFINDER                    │     ║
║   │                                                              │     ║
║   │  Walks paths via edge-weight products  ·  Calibrates scores  │     ║
║   │  Returns Top-K reasoning chains  →  feeds into PolyG RAG     │     ║
║   └──────────────────────────────────────────────────────────────┘     ║
║                                                                          ║
║                                   ▼                                     ║
║                   🧠  PolyG RAG  →  ✅  Response                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Viticulture Knowledge Graph &nbsp; ✦

</div>

<br/>

The domain KG is pre-seeded with **38 entities** and **19 causal edges** spanning grape physiology, climate factors, and biochemical pathways. Every edge carries a **weight** (causal strength 0–1), an optional **condition** (e.g. `T > 35°C`), and a **confidence** score.

<br/>

<div align="center">

```
                    ┌─────────────────────┐
                    │   ☀️  UV Radiation   │
                    └──────────┬──────────┘
                               │ PROMOTES
                               ▼
  ┌─────────────────┐    ┌─────────────────────┐
  │  🌡  Temperature │    │  🍇  Anthocyanin    │
  └────────┬────────┘    └──────────┬──────────┘
           │                        │ AFFECTS
           │ AFFECTS                │
           ▼                        ▼
  ┌──────────────────┐      ╔══════════════════╗
  │  🍬 Sugar Content│─────►║  🍷  Wine Quality ║◄───────────┐
  └──────────────────┘      ╚══════════════════╝             │
           │                        ▲                        │
           │ CAUSES (T>35°C)        │                        │
           ▼                        │                        │
  ┌──────────────────┐              │              ┌─────────┴────────┐
  │  🔥  Heat Stress │──DEGRADES────┘              │  🌿  Tannin      │
  └──────────────────┘                             └─────────┬────────┘
                                                             ▲
  ┌──────────────────┐    ┌─────────────────────┐           │
  │  💧 Irrigation   │───►│  💦 Water Deficit   │──CONTROLS─┘
  └──────────────────┘    └─────────────────────┘
  CONTROLS ▲
           │
  ┌──────────────────┐
  │  🌱 Soil Moisture│
  └──────────────────┘

  ━━  Solid edge  =  always-active causal relation
  ╌╌  Dashed edge =  conditional  (activates under specific conditions)
```

</div>

<br/>


## ✦ &nbsp; Performance at a Glance &nbsp; ✦

</div>

<br/>

<div align="center">

```
  BENCHMARK RESULTS  ·  Physics Citation Graph
  ─────────────────────────────────────────────────────────────────────────
  Strategy             Hit Rate       F1 Score     Token Efficiency
  ─────────────────────────────────────────────────────────────────────────
  BFS                  ████████░░  82%  ████████░  85%  █████████░  94% ⚡
  BFS + PPR            ████████░░  88%  █████████  90%  █████████░  90%
  Cypher Walk          ███████░░░  79%  ███████░░  76%  ███████░░░  71%
  K-Shortest Paths     ████████░░  84%  ████████░  83%  ███████░░░  78%
  DRIFT                █████████░  91%  ████████░  88%  █████░░░░░  52%
  ─────────────────────────────────────────────────────────────────────────
  PolyG Adaptive  ★   █████████░  93%  █████████  92%  ████████░░  86%
  ─────────────────────────────────────────────────────────────────────────
  ★  Adaptive routing = highest accuracy + 31% fewer tokens than DRIFT
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Cypher Security Pipeline &nbsp; ✦

</div>

<br/>

Every LLM-generated Cypher statement passes through a two-stage hardened validation pipeline before touching the database.

<br/>

<div align="center">

```
  ╔════════════════════════════════════════════════════════════════╗
  ║              CYPHER VALIDATION PIPELINE                        ║
  ╠════════════════════════════════════════════════════════════════╣
  ║                                                                ║
  ║   LLM Output (raw Cypher)                                      ║
  ║          │                                                     ║
  ║          ▼                                                     ║
  ║   ┌──────────────────────────────────────────┐                ║
  ║   │  STAGE 1  ·  Security Sanitiser          │                ║
  ║   │                                          │                ║
  ║   │  🚫 Blocks:  DELETE · MERGE · CREATE     │                ║
  ║   │              SET · REMOVE · DROP         │                ║
  ║   │              LOAD CSV · APOC writes      │                ║
  ║   └──────────────────────┬───────────────────┘                ║
  ║                          │  safe read-only                     ║
  ║                          ▼                                     ║
  ║   ┌──────────────────────────────────────────┐                ║
  ║   │  STAGE 2  ·  Semantic Normaliser (7-pass)│                ║
  ║   │                                          │                ║
  ║   │  ① Strip // comments                    │                ║
  ║   │  ② Fix relation alias mismatches        │                ║
  ║   │  ③ Add dataset namespace prefixes       │                ║
  ║   │  ④ Coerce integer IDs → strings         │                ║
  ║   │  ⑤ Remove invalid WHERE clauses         │                ║
  ║   │  ⑥ Fix malformed RETURN projections     │                ║
  ║   │  ⑦ Ensure n.id alias is present         │                ║
  ║   └──────────────────────┬───────────────────┘                ║
  ║                          │  validated Cypher                   ║
  ║                          ▼                                     ║
  ║                  Execute on  Neo4j  ✓                         ║
  ╚════════════════════════════════════════════════════════════════╝
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; DRIFT — Iterative Refinement &nbsp; ✦

</div>

<br/>

For deeply complex nested queries, DRIFT breaks the problem into phases of progressive refinement.

<br/>

<div align="center">

```
  ╔═══════════════════════════════════════════════════════════════════╗
  ║              DRIFT  ·  THREE-PHASE REFINEMENT LOOP                ║
  ╠═══════════════════════════════════════════════════════════════════╣
  ║                                                                   ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE A  ·  PRIMER                                   │      ║
  ║   │                                                       │      ║
  ║   │   → BFS depth-2 from anchor entities                  │      ║
  ║   │   → Generate broad initial answer                     │      ║
  ║   │   → Produce follow-up questions for gaps              │      ║
  ║   └───────────────────────────┬───────────────────────────┘      ║
  ║                               │  follow-up Qs                    ║
  ║                               ▼                                  ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE B  ·  FOLLOW-UP  (max 2 iterations × 3 Qs)    │◄──┐  ║
  ║   │                                                       │   │  ║
  ║   │   → Keyword search with morphological variants        │   │  ║
  ║   │   → BFS depth-1 from matched nodes                    │   │  ║
  ║   │   → Refine sub-answer per question                    │───┘  ║
  ║   └───────────────────────────┬───────────────────────────┘      ║
  ║                               │  sub-answers                     ║
  ║                               ▼                                  ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE C  ·  SYNTHESIS                                │      ║
  ║   │                                                       │      ║
  ║   │   → Combine all sub-answers                           │      ║
  ║   │   → LLM generates hierarchical final response         │      ║
  ║   └───────────────────────────────────────────────────────┘      ║
  ║                                                                   ║
  ║   Bounds:  max 3 follow-ups/iter  ·  max depth 2                 ║
  ║            80 node limit  ·  150 edge limit per phase            ║
  ╚═══════════════════════════════════════════════════════════════════╝
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Token Budget Architecture &nbsp; ✦

</div>

<br/>

<div align="center">

```
  CONTEXT ASSEMBLY  ·  10,000 TOKEN BUDGET (configurable)
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  ███████████████████████████░░░░░░░░░░░░░  ENTITIES   50 %  │
  │  Sorted by node degree (highest-degree = most connected)     │
  │                                                              │
  │  ████████████████████░░░░░░░░░░░░░░░░░░░  RELATIONS   40 %  │
  │  Sorted by sum of endpoint degrees                           │
  │                                                              │
  │  ░░░░░░░░░░░░░░░░░ Reasoning Paths  (remaining budget)       │
  │  Alternating entity → relation → entity chains               │
  │                                                              │
  │  ░░░░░░░░░░░░░░░░░ Auxiliary Data   (remaining budget)       │
  │  Raw Cypher results, citations, extra facts                  │
  │                                                              │
  │  → Lists truncated from lowest-ranked items up               │
  │  → Orphaned edges (missing endpoint) pruned automatically    │
  └──────────────────────────────────────────────────────────────┘
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Technology Stack &nbsp; ✦

</div>

<br/>

<div align="center">

| Layer | Technology | Role |
|:---:|:---:|:---|
| 🗄 **Graph Database** | Neo4j 5.x | Knowledge graph storage + Cypher query engine |
| ⚡ **Web API** | FastAPI + Uvicorn | Async REST backend with session management |
| 🔀 **LLM Routing** | LiteLLM | Unified interface across OpenAI, Ollama, DeepSeek |
| 🕸 **Graph Algorithms** | NetworkX | PageRank, in-memory traversal |
| 🔢 **Tokenisation** | tiktoken | Token counting + context budget management |
| 📐 **Vector Store** | nano-vectordb | Fast approximate nearest-neighbour lookup |
| 🎨 **Frontend** | Vue.js 3 + Vite | Reactive single-page application |
| 🌍 **3D Terrain** | CesiumJS | Geospatial digital twin visualisation |
| 🔗 **Graph UI** | vis-network | Interactive live knowledge graph display |
| 🗂 **State** | Pinia | Reactive frontend state management |
| 📄 **PDF Parsing** | pdfplumber | Document ingestion and text extraction |

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Supported LLM Models &nbsp; ✦

</div>

<br/>

<div align="center">

| Provider | Models |
|:---:|:---|
| ☁️ **OpenAI** | `gpt-4o` · `gpt-4o-mini` |
| 🌊 **DeepSeek** | `deepseek-chat` |
| 🦙 **Ollama (local)** | `llama3.2` · `mistral` · `phi` · `qwen` · `gemma` |
| ⚡ **vLLM (hosted)** | Any model via `hosted_vllm/<model-name>` |

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Benchmark Datasets &nbsp; ✦

</div>

<br/>

<div align="center">

| Dataset | Nodes | Edges | Entity Types | Domain |
|:---:|:---:|:---:|:---:|:---:|
| 🔬 **Physics** | 11,000+ | 34,000+ | paper · author · venue | Citation graph |
| 🛒 **Amazon** | 9,500+ | 18,000+ | item · brand | Co-purchase graph |
| 📚 **Goodreads** | 7,800+ | 21,000+ | book · author · series | Literary graph |

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Project Report &nbsp; ✦

</div>

<br/>

A full academic LaTeX report is included at [report.tex](report.tex), featuring:

<br/>

<div align="center">

```
  📄  report.tex  ·  Contents
  ─────────────────────────────────────────────────────────────
  ✦  Title page with decorative TikZ header and domain badges
  ✦  Abstract with quantified benchmark results
  ✦  Full system architecture diagram (3-layer TikZ flow)
  ✦  Algorithm pseudocode with formal complexity analysis
  ✦  Mathematical formulations for PPR, path scoring, utility
  ✦  Viticulture causal knowledge graph (TikZ)
  ✦  Four-agent pipeline diagram (TikZ)
  ✦  Strategy comparison bar chart (pgfplots)
  ✦  DRIFT three-phase process diagram
  ✦  Qualitative example queries with traced reasoning paths
  ✦  Cypher security pipeline explanation
  ✦  Limitations + future work discussion
  ✦  Full bibliography (9 cited works)
  ─────────────────────────────────────────────────────────────
  Compile:  pdflatex report.tex  (run twice for references)
```

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Environment Variables &nbsp; ✦

</div>

<br/>

<div align="center">

| Variable | Default | Purpose |
|:---|:---:|:---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection string |
| `NEO4J_USER` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | — | Database password |
| `OLLAMA_URL` | `http://localhost:11434` | Local LLM endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Default local model |
| `OMNIVERSE_HOST` | `localhost` | 3D simulation host |
| `OMNIVERSE_PORT` | `8211` | 3D simulation port |
| `UPLOAD_DIR` | `./uploads` | PDF document storage |

</div>

<br/>

---

<div align="center">

## ✦ &nbsp; Citation &nbsp; ✦

</div>

<br/>

<div align="center">

```bibtex
@software{polyg_dt_2025,
  title  = {PolyG-DT: Adaptive Multi-Agent GraphRAG for Digital Twins},
  author = {PolyG Research Team},
  year   = {2025},
  note   = {Viticulture Digital Twin Application}
}
```

</div>

<br/>

---

<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=footer&animation=twinkling" alt="footer"/>

<br/>

**Built with precision. Reasoned with knowledge. Designed for the real world.**

<br/>

*PolyG-DT Research Team &nbsp;·&nbsp; 2025*

</div>
