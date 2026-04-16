from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class ChatRequest(BaseModel):
    message: str


class SessionConfig(BaseModel):
    name: str
    description: str = ""
    domain: str = "viticulture"
    model: str = "llama3.2"
    chunk_size: int = 500
    confidence_threshold: float = 0.7
    utility_threshold: float = 0.3
    omniverse_enabled: bool = True
    # Standard domain agents (viticulture / agriculture)
    agents: List[str] = ["conflict", "synthesizer", "scenario", "pruning", "pathfinder"]
    # Research network config (custom + aviation domains)
    num_agents: int = 4          # number of self-organizing research agents
    research_goal: str = ""      # shared goal the agent network pursues


class AgentStats(BaseModel):
    nodes_added: int = 0
    edges_added: int = 0
    conflicts_found: int = 0
    scenarios_tested: int = 0
    nodes_pruned: int = 0
    paths_computed: int = 0


class AgentStatus(BaseModel):
    name: str
    display_name: str
    phase: int
    status: str = "idle"   # idle | thinking | active | completed | skipped
    task: str = ""
    progress: float = 0.0
    stats: AgentStats = AgentStats()
    icon: str = "🤖"
    focus: str = ""        # emergent focus area (set during negotiation)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "entity"
    description: str = ""
    properties: Dict[str, Any] = {}
    confidence: float = 1.0


class GraphEdge(BaseModel):
    id: str
    from_node: str
    to_node: str
    type: str
    weight: float = 1.0
    condition: Optional[str] = None
    is_hard_edge: bool = False


class GraphState(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


class Metrics(BaseModel):
    logical_chain_accuracy: float = 0.0
    context_efficiency: float = 0.0
    hallucination_rate: float = 0.0
    total_nodes: int = 0
    total_edges: int = 0
    pruned_nodes: int = 0
    conflicts_detected: int = 0
    scenarios_passed: int = 0


class SessionCreate(BaseModel):
    config: SessionConfig


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: SessionConfig
    status: str = "created"   # created | running | completed | stopped | error
    agents: List[AgentStatus] = []
    graph: GraphState = GraphState()
    metrics: Metrics = Metrics()
    files: List[str] = []
    events: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


def make_research_agents(n: int) -> List[AgentStatus]:
    """Create N idle research agent status entries."""
    from agents.research_agent import ICONS
    return [
        AgentStatus(
            name=f"research_{i}",
            display_name=f"Agent {i}",
            phase=1,
            icon=ICONS[i % len(ICONS)],
            status="idle",
            focus="",
        )
        for i in range(n)
    ]


def make_default_agents(enabled: List[str]) -> List[AgentStatus]:
    all_agents = [
        AgentStatus(name="conflict",    display_name="Conflict Agent",    phase=1, icon="⚔️",
                    status="idle" if "conflict"    in enabled else "skipped"),
        AgentStatus(name="synthesizer", display_name="Synthesizer Agent", phase=1, icon="🔬",
                    status="idle" if "synthesizer" in enabled else "skipped"),
        AgentStatus(name="scenario",    display_name="Scenario Agent",    phase=2, icon="🎭",
                    status="idle" if "scenario"    in enabled else "skipped"),
        AgentStatus(name="pruning",     display_name="Pruning Agent",     phase=2, icon="✂️",
                    status="idle" if "pruning"     in enabled else "skipped"),
        AgentStatus(name="pathfinder",  display_name="Pathfinder Agent",  phase=2, icon="🧭",
                    status="idle" if "pathfinder"  in enabled else "skipped"),
    ]
    return all_agents
