"""
KnowledgeCore GraphRAG — FastAPI Backend
Modular Knowledge-as-a-Component: Adaptive Multi-Agent GraphRAG Framework
for Digital Twins (Smart Vineyard Application)
"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks, FastAPI, HTTPException, UploadFile, File, WebSocket,
    WebSocketDisconnect, Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.schemas import (
    Session, SessionCreate, SessionConfig, make_default_agents, make_research_agents,
    GraphState, GraphNode, GraphEdge, Metrics, ChatRequest,
)
from services.neo4j_service import get_neo4j
from services.ollama_service import get_ollama
from services.omniverse_service import get_omniverse

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s")
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# WebSocket Connection Manager
# ============================================================

class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(session_id, []).append(ws)
        logger.info("WS connected: session=%s total=%d",
                    session_id, len(self._connections[session_id]))

    def disconnect(self, session_id: str, ws: WebSocket):
        conns = self._connections.get(session_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, session_id: str, payload: dict):
        conns = self._connections.get(session_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)


ws_manager = ConnectionManager()


# ============================================================
# In-memory session store
# ============================================================

sessions: Dict[str, Session] = {}
session_tasks: Dict[str, asyncio.Task] = {}
session_files: Dict[str, List[Dict]] = {}       # session_id → [{name, content}]
session_phase_events: Dict[str, asyncio.Event] = {}   # for custom domain phase advance
session_orchestrators: Dict[str, object] = {}         # ref to running orchestrator


# ============================================================
# App lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting KnowledgeCore GraphRAG API…")
    # Warm up singletons
    get_neo4j()
    get_ollama()
    get_omniverse()
    yield
    logger.info("Shutting down…")
    neo4j = get_neo4j()
    neo4j.close()


app = FastAPI(
    title="KnowledgeCore GraphRAG",
    description="Adaptive Multi-Agent GraphRAG Framework for Digital Twins",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000",
                   "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health / Status
# ============================================================

@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "KnowledgeCore GraphRAG API"}


@app.get("/api/status", tags=["health"])
async def status():
    neo4j = get_neo4j()
    ollama = get_ollama()
    return {
        "neo4j": "connected" if neo4j.using_neo4j else "fallback (in-memory)",
        "ollama": "available" if ollama.available else "fallback (rule-based)",
        "omniverse": "simulation-ready",
        "active_sessions": len([s for s in sessions.values() if s.status == "running"]),
    }


# ============================================================
# Session management
# ============================================================

@app.post("/api/sessions", response_model=Session, status_code=201, tags=["sessions"])
async def create_session(body: SessionCreate):
    sid = str(uuid.uuid4())
    if body.config.domain in ("custom", "aviation"):
        agents = make_research_agents(max(2, min(body.config.num_agents, 8)))
    else:
        agents = make_default_agents(body.config.agents)
    session = Session(
        id=sid,
        config=body.config,
        status="created",
        agents=agents,
    )
    sessions[sid] = session
    session_files[sid] = []
    logger.info("Session created: %s (%s)", sid, body.config.name)
    return session


@app.get("/api/sessions", response_model=List[Session], tags=["sessions"])
async def list_sessions():
    return list(sessions.values())


@app.get("/api/sessions/{session_id}", response_model=Session, tags=["sessions"])
async def get_session(session_id: str):
    _require_session(session_id)
    return sessions[session_id]


@app.delete("/api/sessions/{session_id}", tags=["sessions"])
async def delete_session(session_id: str):
    _require_session(session_id)
    _stop_task(session_id)
    get_neo4j().clear_session(session_id)
    sessions.pop(session_id)
    session_files.pop(session_id, None)
    return {"deleted": session_id}


# ============================================================
# File upload
# ============================================================

@app.post("/api/sessions/{session_id}/upload", tags=["sessions"])
async def upload_file(session_id: str, file: UploadFile = File(...)):
    _require_session(session_id)
    content = await file.read()
    session_files.setdefault(session_id, []).append({
        "name": file.filename,
        "content": content,
        "size": len(content),
    })
    sess = sessions[session_id]
    if file.filename not in sess.files:
        sess.files.append(file.filename)
    logger.info("File uploaded: %s for session %s", file.filename, session_id)
    return {"filename": file.filename, "size": len(content)}


@app.delete("/api/sessions/{session_id}/files/{filename}", tags=["sessions"])
async def remove_file(session_id: str, filename: str):
    _require_session(session_id)
    session_files[session_id] = [
        f for f in session_files.get(session_id, []) if f["name"] != filename
    ]
    sessions[session_id].files = [
        f for f in sessions[session_id].files if f != filename
    ]
    return {"removed": filename}


# ============================================================
# Session control
# ============================================================

@app.post("/api/sessions/{session_id}/start", tags=["sessions"])
async def start_session(session_id: str):
    _require_session(session_id)
    sess = sessions[session_id]
    if sess.status == "running":
        raise HTTPException(400, "Session is already running")

    sess.status = "running"
    sess.started_at = datetime.now(timezone.utc)

    task = asyncio.create_task(_run_session(session_id))
    session_tasks[session_id] = task
    return {"started": session_id, "status": "running"}


@app.post("/api/sessions/{session_id}/stop", tags=["sessions"])
async def stop_session(session_id: str):
    _require_session(session_id)
    _stop_task(session_id)
    sessions[session_id].status = "stopped"
    return {"stopped": session_id}


# ============================================================
# Graph state
# ============================================================

@app.get("/api/sessions/{session_id}/graph", tags=["graph"])
async def get_graph(session_id: str):
    _require_session(session_id)
    neo4j = get_neo4j()
    raw_nodes = neo4j.get_all_nodes(session_id)
    raw_edges = neo4j.get_all_edges(session_id)
    return {
        "nodes": raw_nodes,
        "edges": raw_edges,
        "node_count": len(raw_nodes),
        "edge_count": len(raw_edges),
    }


@app.get("/api/sessions/{session_id}/metrics", tags=["graph"])
async def get_metrics(session_id: str):
    _require_session(session_id)
    return sessions[session_id].metrics


# ============================================================
# Phase advance (custom domain)
# ============================================================

@app.post("/api/sessions/{session_id}/advance", tags=["sessions"])
async def advance_phase(session_id: str):
    _require_session(session_id)
    ev = session_phase_events.get(session_id)
    if ev and not ev.is_set():
        ev.set()
        return {"advanced": session_id, "status": "ok"}
    return {"advanced": session_id, "status": "already_advanced_or_not_applicable"}


# ============================================================
# Chat query (custom domain Phase 2)
# ============================================================

@app.post("/api/sessions/{session_id}/chat", tags=["sessions"])
async def chat_query(session_id: str, body: ChatRequest):
    _require_session(session_id)
    neo4j = get_neo4j()
    ollama = get_ollama()
    sess = sessions[session_id]

    all_nodes = neo4j.get_all_nodes(session_id)
    if not all_nodes:
        return {"answer": "", "reasoning_chain": [], "nodes_used": [], "confidence": 0.0,
                "error": "Knowledge graph is empty. Run the session first."}

    # Keyword-score nodes for relevance
    keywords = [w for w in body.message.lower().split() if len(w) > 2]
    scored = []
    for node in all_nodes:
        text = (node.get("label", "") + " " + node.get("description", "")).lower()
        score = sum(1 for kw in keywords if kw in text)
        scored.append((score, node))
    scored.sort(key=lambda x: x[0], reverse=True)
    context_nodes = [n for _, n in scored[:10]]

    result = await ollama.answer_query(body.message, context_nodes, model=sess.config.model)

    nodes_used = []
    for nid in result.get("nodes_used", []):
        node = next((n for n in all_nodes if n.get("id") == nid), None)
        if node:
            nodes_used.append(node)
    if not nodes_used:
        nodes_used = context_nodes[:5]

    return {
        "answer": result.get("answer", ""),
        "reasoning_chain": result.get("reasoning_chain", []),
        "nodes_used": nodes_used,
        "confidence": result.get("confidence", 0.0),
        "contradicts_hard_edge": result.get("contradicts_hard_edge", False),
    }


# ============================================================
# Aero chat query (aviation domain Phase 2)
# ============================================================

@app.post("/api/sessions/{session_id}/aero-chat", tags=["sessions"])
async def aero_chat_query(session_id: str, body: ChatRequest):
    _require_session(session_id)
    orch = session_orchestrators.get(session_id)
    if not orch:
        raise HTTPException(400, "Session is not running or has completed.")
    if not hasattr(orch, "handle_chat"):
        raise HTTPException(400, "Active session is not an aviation session.")
    result = await orch.handle_chat(body.message)
    return result


# ============================================================
# WebSocket endpoint
# ============================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        # Send buffered events
        if session_id in sessions:
            sess = sessions[session_id]
            for event in sess.events[-50:]:
                await websocket.send_json(event)
        # Keep alive until disconnect
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
        logger.info("WS disconnected: session=%s", session_id)
    except Exception as e:
        logger.warning("WS error session=%s: %s", session_id, e)
        ws_manager.disconnect(session_id, websocket)


# ============================================================
# Background pipeline runner
# ============================================================

async def _run_session(session_id: str):
    """Run the full multi-agent pipeline for a session."""
    from agents.orchestrator import Orchestrator

    sess = sessions[session_id]

    async def emit(event: dict):
        """Broadcast event to all WebSocket clients and buffer it."""
        # Buffer last 500 events for late-joining clients
        sess.events.append(event)
        if len(sess.events) > 500:
            sess.events.pop(0)

        # Mirror key events into session state
        _apply_event_to_session(session_id, event)

        await ws_manager.broadcast(session_id, event)

    files = session_files.get(session_id, [])

    # Create phase advance event (used by custom domain)
    phase_event = asyncio.Event()
    session_phase_events[session_id] = phase_event

    # Route to domain-specific orchestrator
    if sess.config.domain == "aviation":
        from agents.aero_orchestrator import AeroOrchestrator
        orch = AeroOrchestrator(session_id=session_id, config=sess.config, emit=emit)
    elif sess.config.domain == "custom":
        from agents.general_orchestrator import GeneralOrchestrator
        orch = GeneralOrchestrator(session_id=session_id, config=sess.config,
                                   emit=emit, phase_event=phase_event)
    else:
        orch = Orchestrator(session_id=session_id, config=sess.config, emit=emit)

    session_orchestrators[session_id] = orch

    try:
        await orch.run(uploaded_files=files)
        sess.status = "completed"
        sess.completed_at = datetime.now(timezone.utc)
    except asyncio.CancelledError:
        sess.status = "stopped"
    except Exception as e:
        logger.exception("Pipeline error: %s", e)
        sess.status = "error"
        sess.error_message = str(e)
        await ws_manager.broadcast(session_id, {
            "type": "session.error",
            "data": {"message": str(e)}
        })
    finally:
        session_phase_events.pop(session_id, None)
        session_orchestrators.pop(session_id, None)


def _apply_event_to_session(session_id: str, event: dict):
    """Keep session model up-to-date from events."""
    sess = sessions.get(session_id)
    if not sess:
        return
    etype = event.get("type", "")
    data = event.get("data", {})
    agent_name = event.get("agent", "")

    if etype == "session.completed":
        metrics_data = data.get("metrics", {})
        sess.metrics.logical_chain_accuracy = metrics_data.get("logical_chain_accuracy", 0)
        sess.metrics.context_efficiency = metrics_data.get("context_efficiency", 0)
        sess.metrics.hallucination_rate = metrics_data.get("hallucination_rate", 0)
        sess.metrics.total_nodes = metrics_data.get("total_nodes", 0)
        sess.metrics.total_edges = metrics_data.get("total_edges", 0)
        sess.metrics.pruned_nodes = metrics_data.get("pruned_nodes", 0)
        sess.metrics.conflicts_detected = metrics_data.get("conflicts_detected", 0)
        sess.metrics.scenarios_passed = metrics_data.get("scenarios_passed", 0)

    # Research agent role assignment
    if etype == "agent.role_assigned":
        assigned_name  = data.get("agent", "")
        assigned_focus = data.get("focus", "")
        for a in sess.agents:
            if a.name == assigned_name:
                a.focus = assigned_focus
                a.task  = f"Focus: {assigned_focus}"
                break

    # Update agent status
    if agent_name and etype in ("agent.started", "agent.thinking", "agent.progress",
                                 "agent.completed", "agent.error"):
        for a in sess.agents:
            if a.name == agent_name:
                if etype == "agent.started":
                    a.status = "active"
                elif etype == "agent.thinking":
                    a.status = "thinking"
                    a.task = data.get("thought", "")[:100]
                elif etype == "agent.progress":
                    a.status = "active"
                    a.progress = data.get("progress", 0)
                    a.task = data.get("task", "")[:100]
                elif etype == "agent.completed":
                    a.status = "completed"
                    a.progress = 1.0
                    stats_data = data.get("stats", {})
                    if stats_data:
                        a.stats.nodes_added = stats_data.get("nodes_added", 0)
                        a.stats.edges_added = stats_data.get("edges_added", 0)
                        a.stats.conflicts_found = stats_data.get("conflicts_found", 0)
                        a.stats.scenarios_tested = stats_data.get("scenarios_tested", 0)
                        a.stats.nodes_pruned = stats_data.get("nodes_pruned", 0)
                        a.stats.paths_computed = stats_data.get("paths_computed", 0)
                elif etype == "agent.error":
                    a.status = "error"
                break


def _require_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, f"Session '{session_id}' not found")


def _stop_task(session_id: str):
    task = session_tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()
    get_omniverse().stop(session_id)
