<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=220&section=header&text=Adaptive%20GraphRAG&fontSize=72&fontColor=fff&animation=twinkling&fontAlignY=38&desc=for%20Multi-Agent%20Systems&descAlignY=62&descColor=cce4ff&descSize=22" alt="Adaptive GraphRAG for Multi-Agent Systems"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js%203-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Multi--Model-6C3483?style=flat-square)](https://github.com/BerriAI/litellm)
[![License](https://img.shields.io/badge/License-MIT-F57F17?style=flat-square)](LICENSE)

<br/>

<table>
<tr>
<td align="center" width="200"><strong>5 Traversal Strategies</strong><br/><sub>Adaptive LLM-routed retrieval</sub></td>
<td align="center" width="200"><strong>3-Step Entity Linking</strong><br/><sub>Exact · Fuzzy · BERT Siamese</sub></td>
<td align="center" width="200"><strong>Multimodal Inputs</strong><br/><sub>Text · Images · Audio</sub></td>
<td align="center" width="200"><strong>2 Example Domains</strong><br/><sub>Aviation · Agriculture</sub></td>
</tr>
</table>

<br/>

> *"Where structured knowledge meets adaptive reasoning —*
> *a GraphRAG engine that thinks before it searches."*

<br/>

</div>

---

<div align="center">

### Project Team

**Oussama Laaroussi** &nbsp;&nbsp;·&nbsp;&nbsp; **Kawtar Labzae** &nbsp;&nbsp;·&nbsp;&nbsp; **Zyad Fri**

*Generative AI Project — 2026*

</div>

---

## The Concept: Knowledge as a Component

> [!IMPORTANT]
> The central design principle of this project is **Knowledge-as-a-Component (KaaC)**: a structured Knowledge Graph (KG) acts as the persistent, queryable *mind* of the agent system — continuously populated from multimodal sources and queried through an adaptive retrieval engine. The KG is domain-agnostic by design; only the seed schema changes per domain.

The goal is to explore how agents can learn and extract useful knowledge from a stack of multimodal resources — documents, images, sensor streams — and structure it into a KG that any downstream agent can reason over. This decouples knowledge acquisition from knowledge consumption.

---

## How It Works — Three-Component Architecture

<div align="center">

<table>
<tr>
<td align="center" width="270">

**① Multimodal Extraction**

Specialised agents ingest text, images, and audio through either Modular Encoding (per-modality encoders) or Native Multimodality (Gemma 4). Extracted entities and relations populate the KG incrementally.

</td>
<td align="center" width="30">→</td>
<td align="center" width="270">

**② Knowledge Graph (KaaC)**

Neo4j stores a typed causal graph with weighted edges, activation conditions, and confidence scores. The KG is the single source of truth — shared across all agents and human users.

</td>
<td align="center" width="30">→</td>
<td align="center" width="270">

**③ Adaptive GraphRAG**

Each query is classified and routed to the optimal traversal strategy. Retrieved subgraphs are ranked, token-budgeted, and passed to an LLM for grounded response generation.

</td>
</tr>
</table>

</div>

---

## Multimodal Input Pipeline

Two architectures are supported for handling heterogeneous input streams:

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  MODULAR ENCODING                                                   │
  │                                                                     │
  │  [Text] ──► Text Encoder  ──┐                                       │
  │  [Image]──► Vision Encoder ─┼──► Shared Embedding Space ──► KG     │
  │  [Audio]──► Audio Encoder  ─┘                                       │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │  NATIVE MULTIMODALITY  (e.g. Gemma 4)                               │
  │                                                                     │
  │  [Text + Image + Audio] ──► Single Multimodal LLM ──► KG           │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## Entity Linking — Three-Step Cascade

Before any graph traversal, surface mentions in the query are resolved to KG node IDs through a **cascading entity linking pipeline** that escalates in cost only when cheaper methods fail:

```
  [ Surface Mention ]
          │
          ▼
  ┌───────────────────────────────────────┐
  │  STEP 1  ·  Exact / Case Lookup       │ ──── match? ──── [ Resolved ]
  └───────────────────────────────────────┘          no ↓
          │
          ▼
  ┌───────────────────────────────────────┐
  │  STEP 2  ·  Fuzzy Search              │ ──── match? ──── [ Resolved ]
  │  Levenshtein distance (fuzzywuzzy)    │          no ↓
  │  Handles typos · abbreviations        │
  └───────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────┐
  │  STEP 3  ·  BERT Siamese Network      │ ──── match? ──── [ Resolved ]
  │  Fine-tuned on domain entity pairs    │          no ↓
  │  Cosine similarity in dense space     │     [ Unresolved / Skip ]
  │  Handles paraphrase · domain jargon   │
  └───────────────────────────────────────┘
```

> [!NOTE]
> The BERT Siamese network is fine-tuned on domain-specific positive/hard-negative entity pairs, enabling robust resolution of paraphrased or technical surface forms that character-level metrics cannot handle.

---

## End-to-End Architecture

```
╔══════════════════════════════════════════════════════════════════════════╗
║       ADAPTIVE GRAPHRAG FOR MULTI-AGENT SYSTEMS  ·  SYSTEM FLOW          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   [ USER QUERY ]                                                         ║
║         │                                                                ║
║         ▼                                                                ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 1  ·  QUERY UNDERSTANDING                 │       ║
║   │                                                             │       ║
║   │   ┌────────────────────────────────┐  ┌──────────────────┐ │       ║
║   │   │  Entity Extractor              │─►│ Query Classifier │ │       ║
║   │   │  Exact → Fuzzy → BERT Siamese  │  │ LLM meta-router  │ │       ║
║   │   └────────────────────────────────┘  └────────┬─────────┘ │       ║
║   └────────────────────────────────────────────────┼───────────┘       ║
║                                                    │ selects strategy   ║
║                                                    ▼                    ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 2  ·  ADAPTIVE RETRIEVAL                  │       ║
║   │                                                             │       ║
║   │   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐   │       ║
║   │   │ BFS  │  │BFS + │  │Cypher│  │K-Path│  │  DRIFT   │   │       ║
║   │   │      │  │ PPR  │  │ Walk │  │      │  │ Explorer │   │       ║
║   │   └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘   │       ║
║   │      └─────────┴─────────┴──────────┴───────────┘         │       ║
║   │                              ▼                             │       ║
║   │                    ╔═════════════════╗                     │       ║
║   │                    ║   Neo4j  KG     ║                     │       ║
║   │                    ╚═════════════════╝                     │       ║
║   └─────────────────────────────────────────────────────────────┘       ║
║                                                    │ subgraph           ║
║                                                    ▼                    ║
║   ┌─────────────────────────────────────────────────────────────┐       ║
║   │             LAYER 3  ·  GROUNDED GENERATION                 │       ║
║   │                                                             │       ║
║   │   ┌──────────────────────┐     ┌────────────────────────┐  │       ║
║   │   │   Context Ranker     │────►│     LLM Generator      │  │       ║
║   │   │   Degree + PPR       │     │   Token-budgeted ctx   │  │       ║
║   │   └──────────────────────┘     └────────────────────────┘  │       ║
║   └─────────────────────────────────────────────────────────────┘       ║
║                                                    │                    ║
║                                                    ▼                    ║
║                                        [ GROUNDED RESPONSE ]            ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Traversal Strategies

The adaptive routing engine reads the semantic intent of each query and dispatches it to the optimal retrieval algorithm before any graph access occurs.

```
 ╔════════╦════════════════╦══════════╦═════════════╦══════════════════════╗
 ║  ID    ║  Strategy      ║ LLM Hits ║  Complexity ║  Ideal Query Type    ║
 ╠════════╬════════════════╬══════════╬═════════════╬══════════════════════╣
 ║   0    ║  BFS           ║    0     ║  O(V+E)     ║  Exploratory         ║
 ║   0+   ║  BFS + PPR     ║    0     ║  O(V+E)     ║  Dense graph ranking ║
 ║   1    ║  Cypher Walk   ║   1–3    ║  O(Q)       ║  Object discovery    ║
 ║   2    ║  K-Shortest    ║    0     ║  O(KE)      ║  Causal chains       ║
 ║   3    ║  CSP Search    ║   1–2    ║  O(P)       ║  Fact checking       ║
 ║  −1    ║  DRIFT         ║  5–15    ║  O(I·V)     ║  Complex / nested    ║
 ╚════════╩════════════════╩══════════╩═════════════╩══════════════════════╝
```

### BFS + PPR — Best Overall Configuration

```
  BFS + PERSONALISED PAGERANK  —  WHY IT WINS FOR DOMAIN TWINS
  ─────────────────────────────────────────────────────────────────────
  Zero LLM calls during traversal    →  sub-100ms retrieval
  Deterministic results              →  reliable A/B testing
  PPR re-ranks by node importance    →  best precision-recall balance
  Domain KGs are locally dense       →  depth-2 captures full context
  Graceful degradation               →  never returns empty context
  ─────────────────────────────────────────────────────────────────────
        Token Efficiency  ██████████████████████  90%
        Hit Rate          ████████████████████░░  88%
        F1 Score          █████████████████████░  90%
        Latency           ██████████████████████  Fast
  ─────────────────────────────────────────────────────────────────────
```

---

## Knowledge Construction Pipeline

Four specialised AI agents transform multimodal domain resources into a high-quality causal knowledge graph.

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    KNOWLEDGE CONSTRUCTION PIPELINE                       ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   [ Multimodal Resources: Text · Images · Sensor Data ]                  ║
║                               │                                         ║
║                               ▼                                         ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  AGENT 1  ·  CONFLICT DETECTOR                               │     ║
║   │                                                              │     ║
║   │  Compares document chunks pairwise · detects contradictions  │     ║
║   │  Creates conditional edges annotated with source conflict    │     ║
║   └───────────────────────────┬──────────────────────────────────┘     ║
║                               │  conflict edges                         ║
║                               ▼                                         ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  AGENT 2  ·  KNOWLEDGE SYNTHESIZER                           │     ║
║   │                                                              │     ║
║   │  Seeds domain schema  ·  Extracts entities via LLM / Gemma4  │     ║
║   │  Merges entities + relations into Neo4j graph incrementally  │     ║
║   └───────────────────────────┬──────────────────────────────────┘     ║
║                               │  full graph                             ║
║                               ▼                                         ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  AGENT 3  ·  GRAPH PRUNER                                    │     ║
║   │                                                              │     ║
║   │  Scores every node:  utility = 0.6×degree + 0.4×avg_weight  │     ║
║   │  Removes low-utility nodes  ·  Produces lean deployment KG   │     ║
║   └───────────────────────────┬──────────────────────────────────┘     ║
║                               │  pruned graph                           ║
║                               ▼                                         ║
║   ┌──────────────────────────────────────────────────────────────┐     ║
║   │  AGENT 4  ·  PROBABILISTIC PATHFINDER                        │     ║
║   │                                                              │     ║
║   │  Walks paths via edge-weight products  ·  Calibrates scores  │     ║
║   │  Returns Top-K reasoning chains  →  feeds into GraphRAG      │     ║
║   └──────────────────────────────────────────────────────────────┘     ║
║                               │                                         ║
║                               ▼                                         ║
║              [ Adaptive GraphRAG Engine  →  Response ]                  ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Domain Coverage

The framework has been validated on two distinct real-world domains with no changes to the core engine — only the KG seed schema differs.

<div align="center">

<table>
<tr>
<td align="center" width="380">

**Aviation**

Agents ingest flight manuals, maintenance procedures, and incident reports. The KG captures aircraft systems, failure modes, and operational constraints.

*Example query types:* causal chains (`"what cascade leads to hydraulic loss?"`), fact-checking (`"is procedure X regulation-compliant?"`), exploratory (`"what systems are affected by sensor failure?"`)

</td>
<td align="center" width="30"></td>
<td align="center" width="380">

**Agriculture**

Agents process agronomic literature, sensor telemetry, and satellite imagery. The KG captures crop physiology, climate factors, and soil–plant interactions.

*Example query types:* causal reasoning (`"how does water deficit reduce crop yield?"`), exploratory (`"what environmental factors affect photosynthesis?"`), path discovery

</td>
</tr>
</table>

</div>

### Example: Agriculture Domain Knowledge Graph

```
                    ┌─────────────────────┐
                    │   Solar Radiation   │
                    └──────────┬──────────┘
                               │ PROMOTES
                               ▼
  ┌─────────────────┐    ┌─────────────────────┐
  │   Temperature   │    │    Chlorophyll      │
  └────────┬────────┘    └──────────┬──────────┘
           │                        │ AFFECTS
           │ AFFECTS                │
           ▼                        ▼
  ┌──────────────────┐      ╔══════════════════╗
  │   Water Uptake   │─────►║   Crop Quality   ║◄────────────┐
  └──────────────────┘      ╚══════════════════╝             │
           │                        ▲                        │
           │ CAUSES (T > 35°C)      │                        │
           ▼                        │                        │
  ┌──────────────────┐              │              ┌─────────┴────────┐
  │    Heat Stress   │──DEGRADES────┘              │  Soil Nutrients  │
  └──────────────────┘                             └─────────┬────────┘
                                                             ▲
  ┌──────────────────┐    ┌─────────────────────┐           │
  │    Irrigation    │───►│    Water Deficit    │──CONTROLS─┘
  └──────────────────┘    └─────────────────────┘
  CONTROLS ▲
           │
  ┌──────────────────┐
  │   Soil Moisture  │
  └──────────────────┘

  ━━  Solid edge  =  always-active causal relation
  ╌╌  Dashed edge =  conditional  (activates under specific conditions)
```

---

## Benchmark Results

<div align="center">

```
  BENCHMARK RESULTS  ·  GRBench + Physics Citation Graph
  ─────────────────────────────────────────────────────────────────────────
  Strategy             Hit Rate       F1 Score     Token Efficiency
  ─────────────────────────────────────────────────────────────────────────
  BFS                  ████████░░  82%  ████████░  85%  █████████░  94%
  BFS + PPR            ████████░░  88%  █████████  90%  █████████░  90%
  Cypher Walk          ███████░░░  79%  ███████░░  76%  ███████░░░  71%
  K-Shortest Paths     ████████░░  84%  ████████░  83%  ███████░░░  78%
  DRIFT                █████████░  91%  ████████░  88%  █████░░░░░  52%
  ─────────────────────────────────────────────────────────────────────────
  Adaptive  [BEST]     █████████░  93%  █████████  92%  ████████░░  86%
  ─────────────────────────────────────────────────────────────────────────
  Adaptive routing  =  highest accuracy + 31% fewer tokens than DRIFT
  Domain transfer hallucination: 3.2%  vs  12.7% standard RAG baseline
```

</div>

---

## Cypher Security Pipeline

Every LLM-generated Cypher statement passes through a two-stage hardened validation pipeline before touching the database.

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
  ║   │  Blocks:  DELETE · MERGE · CREATE        │                ║
  ║   │           SET · REMOVE · DROP            │                ║
  ║   │           LOAD CSV · APOC writes         │                ║
  ║   └──────────────────────┬───────────────────┘                ║
  ║                          │  safe read-only                     ║
  ║                          ▼                                     ║
  ║   ┌──────────────────────────────────────────┐                ║
  ║   │  STAGE 2  ·  Semantic Normaliser (7-pass)│                ║
  ║   │                                          │                ║
  ║   │  1.  Strip // comments                   │                ║
  ║   │  2.  Fix relation alias mismatches       │                ║
  ║   │  3.  Add dataset namespace prefixes      │                ║
  ║   │  4.  Coerce integer IDs to strings       │                ║
  ║   │  5.  Remove invalid WHERE clauses        │                ║
  ║   │  6.  Fix malformed RETURN projections    │                ║
  ║   │  7.  Ensure n.id alias is present        │                ║
  ║   └──────────────────────┬───────────────────┘                ║
  ║                          │  validated Cypher                   ║
  ║                          ▼                                     ║
  ║                  Execute on  Neo4j  [OK]                       ║
  ╚════════════════════════════════════════════════════════════════╝
```

---

## DRIFT — Iterative Refinement

For deeply complex nested queries, DRIFT breaks the problem into three phases of progressive refinement.

```
  ╔═══════════════════════════════════════════════════════════════════╗
  ║              DRIFT  ·  THREE-PHASE REFINEMENT LOOP                ║
  ╠═══════════════════════════════════════════════════════════════════╣
  ║                                                                   ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE A  ·  PRIMER                                   │      ║
  ║   │   BFS depth-2 from anchor entities                    │      ║
  ║   │   Generate broad initial answer                       │      ║
  ║   │   Produce follow-up questions for gaps                │      ║
  ║   └───────────────────────────┬───────────────────────────┘      ║
  ║                               │  follow-up questions              ║
  ║                               ▼                                  ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE B  ·  FOLLOW-UP  (max 2 iterations × 3 Qs)   │◄──┐  ║
  ║   │   Keyword search with morphological variants          │   │  ║
  ║   │   BFS depth-1 from matched nodes                      │   │  ║
  ║   │   Refine sub-answer per question                      │───┘  ║
  ║   └───────────────────────────┬───────────────────────────┘      ║
  ║                               │  sub-answers                     ║
  ║                               ▼                                  ║
  ║   ┌───────────────────────────────────────────────────────┐      ║
  ║   │  PHASE C  ·  SYNTHESIS                                │      ║
  ║   │   Combine all sub-answers                             │      ║
  ║   │   LLM generates hierarchical final response           │      ║
  ║   └───────────────────────────────────────────────────────┘      ║
  ║                                                                   ║
  ║   Bounds:  max 3 follow-ups/iter  ·  max depth 2                 ║
  ║            80 node limit  ·  150 edge limit per phase            ║
  ╚═══════════════════════════════════════════════════════════════════╝
```

---

## Token Budget Architecture

```
  CONTEXT ASSEMBLY  ·  10,000 TOKEN BUDGET (configurable)
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  ███████████████████████████░░░░░░░░░░░░░  ENTITIES   50%   │
  │  Sorted by node degree (highest-degree = most connected)     │
  │                                                              │
  │  ████████████████████░░░░░░░░░░░░░░░░░░░  RELATIONS   40%   │
  │  Sorted by sum of endpoint degrees                           │
  │                                                              │
  │  ░░░░░░░░░░░░░░░░░  Reasoning Paths   (remaining budget)     │
  │  Alternating entity → relation → entity chains               │
  │                                                              │
  │  ░░░░░░░░░░░░░░░░░  Auxiliary Data    (remaining budget)     │
  │  Raw Cypher results, citations, extra facts                  │
  │                                                              │
  │  Lists truncated from lowest-ranked items up                 │
  │  Orphaned edges (missing endpoint) pruned automatically      │
  └──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Role |
|:---|:---|:---|
| **Graph Database** | Neo4j 5.x | Knowledge graph storage + Cypher query engine |
| **Web API** | FastAPI + Uvicorn | Async REST backend with session management |
| **LLM Routing** | LiteLLM | Unified interface across OpenAI, Ollama, DeepSeek |
| **Graph Algorithms** | NetworkX | PageRank, in-memory traversal |
| **Entity Linking** | BERT Siamese Network | Fine-tuned semantic entity resolution |
| **Tokenisation** | tiktoken | Token counting + context budget management |
| **Vector Store** | nano-vectordb | Fast approximate nearest-neighbour lookup |
| **Frontend** | Vue.js 3 + Vite | Reactive single-page application |
| **3D Terrain** | CesiumJS | Geospatial digital twin visualisation |
| **Graph UI** | vis-network | Interactive live knowledge graph display |
| **State Management** | Pinia | Reactive frontend state management |
| **Multimodal** | Gemma 4 / Modular Encoders | Native or modular multimodal ingestion |

---

## Supported LLM Models

| Provider | Models |
|:---|:---|
| **OpenAI** | `gpt-4o` · `gpt-4o-mini` |
| **DeepSeek** | `deepseek-chat` |
| **Google** | `gemma-4` (multimodal) |
| **Ollama (local)** | `llama3.2` · `mistral` · `phi` · `qwen` · `gemma` |
| **vLLM (hosted)** | Any model via `hosted_vllm/<model-name>` |

---

## Benchmark Datasets

| Dataset | Nodes | Edges | Domain | Task |
|:---|:---:|:---:|:---|:---|
| **GRBench** | varied | varied | Mixed | Diverse GraphRAG QA |
| **Physics** | 11,000+ | 34,000+ | Citation graph | Multi-hop QA |
| **Amazon** | 9,500+ | 18,000+ | E-commerce | Co-purchase reasoning |
| **Goodreads** | 7,800+ | 21,000+ | Literary graph | Entity linking |

---

## Project Report

A full LaTeX report is included at [Documents/report.tex](Documents/report.tex), featuring:

- Title page with decorative TikZ header
- Abstract with quantified benchmark results
- Full system architecture diagram (3-layer TikZ flow)
- Four-layer deployment architecture diagram
- Three-step entity linking cascade diagram (BERT Siamese)
- Algorithm pseudocode with formal complexity analysis
- Mathematical formulations for PPR, semantic linking, path scoring
- Token budget allocation visualisation
- Example domain knowledge graph (TikZ)
- Four-agent pipeline diagram (TikZ)
- Strategy comparison bar chart (pgfplots)
- DRIFT three-phase process diagram
- Qualitative example queries — aviation and agriculture domains
- Cypher security pipeline explanation
- Limitations + future work discussion
- Full bibliography (14 cited works)

Compile: `pdflatex report.tex` (run twice for references)

---

## Configuration

| Variable | Default | Purpose |
|:---|:---:|:---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection string |
| `NEO4J_USER` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | — | Database password |
| `OLLAMA_URL` | `http://localhost:11434` | Local LLM endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Default local model |
| `OMNIVERSE_HOST` | `localhost` | 3D simulation host |
| `OMNIVERSE_PORT` | `8211` | 3D simulation port |
| `UPLOAD_DIR` | `./uploads` | Document + media storage |

---

## Citation

```bibtex
@software{adaptive_graphrag_mas_2026,
  title  = {Adaptive GraphRAG for Multi-Agent Systems:
            A Scalable Architecture for Dynamic Domain-Specific Reasoning},
  author = {Laaroussi, Oussama and Labzae, Kawtar and Fri, Zyad},
  year   = {2026},
  note   = {Generative AI Project — Validated on Aviation and Agriculture Domains}
}
```

---

<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=footer&animation=twinkling" alt="footer"/>

<br/>

**Built with precision. Reasoned with knowledge. Designed for the real world.**

<br/>

*Oussama Laaroussi &nbsp;·&nbsp; Kawtar Labzae &nbsp;·&nbsp; Zyad Fri &nbsp;·&nbsp; 2026*

</div>
