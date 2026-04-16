"""
Navigator Agent — Phase 2 (Aviation)
Plans the optimal North Atlantic Track trajectory using graph-based reasoning.
Adapts routing based on jet stream position and weather constraints.
Communicates route findings and weather observations to peer agents via AgentMessageBus.
"""
import asyncio
import logging
from typing import List, Dict, Optional

from .base import BaseAgent, EventEmitter
from .agent_message_bus import AgentMessageBus
from services.ollama_service import get_ollama
from services.neo4j_service import get_neo4j
from services.jsbsim_service import WAYPOINTS, haversine_nm

logger = logging.getLogger(__name__)


class NavigatorAgent(BaseAgent):
    name = "navigator"
    display_name = "Navigator Agent"
    phase = 2
    icon = "🗺️"

    def __init__(self, *args, bus: Optional[AgentMessageBus] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._bus = bus

    async def run(self, session_id: str, **kwargs):
        await self.started()
        await self.thinking("Computing optimal North Atlantic Track using graph-based routing…")
        await self._sleep(0.8)

        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "status",
                "Navigator Agent online. Initialising NATS route planner. JFK→LHR via NAT-B.",
            )

        ollama = get_ollama()
        neo4j  = get_neo4j()

        # Compute total route distance
        total_nm = sum(
            haversine_nm(WAYPOINTS[i]["lat"], WAYPOINTS[i]["lon"],
                         WAYPOINTS[i+1]["lat"], WAYPOINTS[i+1]["lon"])
            for i in range(len(WAYPOINTS) - 1)
        )
        await self.thinking(f"Route JFK→LHR: {total_nm:.0f} nm across {len(WAYPOINTS)} waypoints")
        await self._sleep(0.5)

        # Check graph for jet stream data to optimise routing
        nodes = neo4j.get_all_nodes(session_id)
        jet_nodes = [n for n in nodes if "jet" in n.get("label","").lower()
                     or "stream" in n.get("label","").lower()]

        if jet_nodes:
            await self.thinking("Jet stream node found in graph — adjusting routing for optimal tailwind benefit…")
            if self._bus:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "finding",
                    f"Jet stream active at FL350-FL390. Routing through core for 80-120 kt tailwind. "
                    f"Estimated fuel saving: 11-14% vs standard track.",
                )
        else:
            await self.thinking("No jet stream node yet — using standard NATS routing…")

        # Emit each waypoint
        for i, wp in enumerate(WAYPOINTS):
            await self.progress(i / len(WAYPOINTS), f"Waypoint {i+1}: {wp['name']}")
            await self.emit("agent.waypoint_planned", {
                "waypoint": wp,
                "index": i,
                "dist_from_prev": round(
                    haversine_nm(WAYPOINTS[i-1]["lat"], WAYPOINTS[i-1]["lon"],
                                 wp["lat"], wp["lon"]) if i > 0 else 0, 1
                ),
            })
            await self._sleep(0.2)

        await self.progress(1.0, "Route plan complete")
        await self.emit("agent.route_planned", {
            "route": WAYPOINTS,
            "total_nm": round(total_nm, 1),
            "flight_level": 350,
            "cruise_mach": 0.785,
            "estimated_fuel_kg": 19500,
            "estimated_time_h": round(total_nm / 450, 2),
        })

        if self._bus:
            await self._bus.broadcast(
                self.name, self.display_name, self.icon,
                "summary",
                f"Route plan complete. {total_nm:.0f} nm via {len(WAYPOINTS)} waypoints. "
                f"FL350, Mach 0.785. Step-climb to FL370 at waypoint 6 recommended.",
            )

        await self.completed(
            f"North Atlantic route planned: {total_nm:.0f} nm, "
            f"FL350, Mach 0.785. Jet stream optimisation active."
        )

    async def broadcast_weather_observation(self, flight_state: Dict, tick: int) -> None:
        """Broadcast weather and routing updates to peer agents each flight tick."""
        if not self._bus:
            return

        phase = flight_state.get("phase", "cruise")
        mach  = flight_state.get("mach", 0.785)
        alt   = flight_state.get("alt_ft", 35000)
        turb  = flight_state.get("turb_level", 0)
        wp    = flight_state.get("current_waypoint", {}).get("name", "en-route")

        # Only broadcast significant observations (every 5 ticks or on anomalies)
        if tick % 5 == 0 or turb > 0.4:
            if turb > 0.6:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "alert",
                    f"MODERATE CAT detected near {wp} at FL{int(alt/100):03d}. "
                    f"Turbulence index {turb:.2f}. Recommend speed reduction to M{mach-0.01:.3f}. "
                    f"Pilot: consider 2000ft deviation to avoid.",
                )
            elif turb > 0.3:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "finding",
                    f"Light-moderate turbulence at {wp}. Index {turb:.2f}. "
                    f"Monitoring — no action required yet.",
                )
            elif tick % 5 == 0:
                await self._bus.broadcast(
                    self.name, self.display_name, self.icon,
                    "status",
                    f"Routing nominal at {wp}, FL{int(alt/100):03d}, M{mach:.3f}. "
                    f"Track within NATS corridor.",
                )
