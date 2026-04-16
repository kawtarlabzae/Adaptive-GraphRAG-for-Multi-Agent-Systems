"""
NVIDIA Omniverse Digital Twin simulation service.
Simulates a Smart Vineyard with realistic sensor data and USD stage updates.
Designed to interface with Omniverse Kit via REST/WebSocket (simulated here).
"""
import asyncio
import math
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

# Vineyard layout constants
ZONES = 3
ROWS_PER_ZONE = 5
VINES_PER_ROW = 16
TOTAL_VINES = ZONES * ROWS_PER_ZONE * VINES_PER_ROW

EventCallback = Callable[[Dict], Awaitable[None]]


class VineYard:
    """Simulates a 3-zone vineyard digital twin."""

    def __init__(self):
        self.tick = 0
        self.day_hour = 6.0         # Start at 6 AM
        self.zones: Dict[int, Dict] = {
            1: self._new_zone(1, base_temp=33.5, base_moisture=48.0),
            2: self._new_zone(2, base_temp=35.2, base_moisture=38.0),
            3: self._new_zone(3, base_temp=34.8, base_moisture=43.0),
        }
        self.irrigation: Dict[int, Dict] = {
            z: {"active": False, "duration_remaining": 0, "intensity": "off"}
            for z in [1, 2, 3]
        }
        self.vine_states: List[Dict] = self._init_vines()
        self.commands_log: List[Dict] = []
        self.usd_stage_log: List[str] = []
        self.anthocyanin_baseline = 62.0
        self.global_uv = 7.5
        self.wind_speed = 8.0

    @staticmethod
    def _new_zone(zone_id: int, base_temp: float, base_moisture: float) -> Dict:
        return {
            "id": zone_id,
            "name": f"Zone {zone_id} — {'North' if zone_id == 1 else 'Central' if zone_id == 2 else 'South'} Block",
            "temperature": base_temp,
            "humidity": 42.0 + zone_id * 3,
            "soil_moisture": base_moisture,
            "anthocyanin_index": 60.0 + zone_id * 2,
            "brix": 22.5 + zone_id * 0.5,
            "uv_index": 7.5,
            "stress_level": "low",
        }

    def _init_vines(self) -> List[Dict]:
        vines = []
        for z in range(ZONES):
            for r in range(ROWS_PER_ZONE):
                for v in range(VINES_PER_ROW):
                    vines.append({
                        "zone": z + 1, "row": r, "col": v,
                        "health": random.uniform(0.75, 1.0),
                        "temp_stress": random.uniform(0.0, 0.3),
                        "irrigating": False,
                    })
        return vines

    def tick_simulation(self) -> Dict:
        """Advance simulation by one time step (≈10 min)."""
        self.tick += 1
        self.day_hour = (self.day_hour + 10 / 60) % 24

        # Day/night temperature cycle
        hour_rad = (self.day_hour - 14) * math.pi / 12  # peak at 14:00
        temp_cycle = math.cos(hour_rad) * 5.0

        # UV follows solar angle
        solar_angle = max(0, math.cos((self.day_hour - 12) * math.pi / 8))
        self.global_uv = round(solar_angle * 10.5 + random.gauss(0, 0.3), 1)
        self.wind_speed = round(max(0, 8 + math.sin(self.tick * 0.1) * 4 + random.gauss(0, 1)), 1)

        for z_id, zone in self.zones.items():
            irr = self.irrigation[z_id]

            # Update irrigation duration
            if irr["active"] and irr["duration_remaining"] > 0:
                irr["duration_remaining"] -= 10
                if irr["duration_remaining"] <= 0:
                    irr["active"] = False
                    irr["intensity"] = "off"
                    self.usd_stage_log.append(
                        f"[{self._ts()}] USD: irrigation_system/zone_{z_id}.active = false"
                    )

            # Temperature update
            moisture_cooling = 2.0 if irr["active"] else 0.0
            new_temp = (zone["temperature"]
                        + temp_cycle * 0.15
                        + random.gauss(0, 0.2)
                        - moisture_cooling * 0.1)
            zone["temperature"] = round(max(22, min(45, new_temp)), 1)

            # Humidity
            zone["humidity"] = round(
                max(15, min(95, zone["humidity"] + random.gauss(0, 0.5)
                            + (3.0 if irr["active"] else 0))), 1
            )

            # Soil moisture
            evap = 0.8 + zone["temperature"] * 0.02
            gain = 12.0 if irr["active"] else 0.0
            zone["soil_moisture"] = round(
                max(5, min(95, zone["soil_moisture"] - evap * 0.1 + gain * 0.15
                           + random.gauss(0, 0.3))), 1
            )

            # Anthocyanin index (degrades with heat, improves with UV and moisture)
            heat_penalty = max(0, (zone["temperature"] - 35) * 0.4) if zone["temperature"] > 35 else 0
            uv_bonus = self.global_uv * 0.05
            moisture_bonus = max(0, (zone["soil_moisture"] - 30) * 0.03)
            zone["anthocyanin_index"] = round(
                max(0, min(100, zone["anthocyanin_index"]
                           - heat_penalty * 0.05
                           + uv_bonus * 0.03
                           + moisture_bonus * 0.02
                           + random.gauss(0, 0.2))), 1
            )

            # Brix (sugar content)
            zone["brix"] = round(
                max(10, min(35, zone["brix"]
                            + (0.02 if zone["soil_moisture"] < 30 else -0.01)
                            + random.gauss(0, 0.05))), 2
            )

            # Stress level
            if zone["temperature"] > 38 or zone["soil_moisture"] < 20:
                zone["stress_level"] = "high"
            elif zone["temperature"] > 34 or zone["soil_moisture"] < 35:
                zone["stress_level"] = "medium"
            else:
                zone["stress_level"] = "low"

            zone["uv_index"] = self.global_uv

        # Update vine states
        for vine in self.vine_states:
            z = self.zones[vine["zone"]]
            vine["irrigating"] = self.irrigation[vine["zone"]]["active"]
            vine["temp_stress"] = max(0, min(1, (z["temperature"] - 30) / 15))
            vine["health"] = round(max(0.1, min(1.0,
                vine["health"] + random.gauss(0, 0.005)
                - vine["temp_stress"] * 0.01
                + (0.005 if vine["irrigating"] else 0)
            )), 3)

        return self.get_state()

    def apply_command(self, command: str, params: Dict) -> Dict:
        """Apply a command from the LLM/pathfinder to the simulation."""
        ts = self._ts()
        result = {"success": False, "message": "", "usd_update": ""}

        if command == "IRRIGATE":
            zone_str = params.get("zone", "all")
            duration = int(params.get("duration_minutes", 30))
            intensity = params.get("intensity", "medium")
            zones_to_irrigate = list(self.zones.keys()) if zone_str == "all" \
                else [int(zone_str.split("_")[-1])]
            for z in zones_to_irrigate:
                if z in self.irrigation:
                    self.irrigation[z]["active"] = True
                    self.irrigation[z]["duration_remaining"] = duration
                    self.irrigation[z]["intensity"] = intensity
                    self.usd_stage_log.append(
                        f"[{ts}] USD: irrigation_system/zone_{z}.active = true, "
                        f"duration={duration}min, intensity={intensity}"
                    )
            result = {
                "success": True,
                "message": f"Activated irrigation for zones {zones_to_irrigate}, {duration} min, {intensity}",
                "usd_update": f"Activated drip heads in zones {zones_to_irrigate}; "
                              f"soil_moisture_shader will update in next tick."
            }
            self.commands_log.append({"ts": ts, "cmd": command, "params": params, "result": result})

        elif command == "SHADE":
            zone_str = params.get("zone", "zone_1")
            intensity = params.get("intensity", "medium")
            self.usd_stage_log.append(
                f"[{ts}] USD: shading_mesh/{zone_str}.opacity = "
                f"{'0.4' if intensity == 'medium' else '0.6'}"
            )
            result = {
                "success": True,
                "message": f"Deployed shade mesh over {zone_str}",
                "usd_update": f"Shading mesh activated; UV reduction ~40%; temperature drop expected 2-3°C."
            }
            self.commands_log.append({"ts": ts, "cmd": command, "params": params, "result": result})

        elif command == "MONITOR":
            result = {
                "success": True,
                "message": f"Enhanced monitoring activated for {params.get('zone', 'all')}",
                "usd_update": "Sensor sampling rate increased to 30s intervals."
            }
            self.commands_log.append({"ts": ts, "cmd": command, "params": params, "result": result})

        elif command == "ALERT":
            result = {
                "success": True,
                "message": f"Alert issued: {params.get('reason', 'Stress detected')}",
                "usd_update": "Alert prim activated; dashboard notification sent."
            }
            self.commands_log.append({"ts": ts, "cmd": command, "params": params, "result": result})

        return result

    def get_state(self) -> Dict:
        return {
            "tick": self.tick,
            "day_hour": round(self.day_hour, 2),
            "global_uv": self.global_uv,
            "wind_speed": self.wind_speed,
            "zones": {str(k): dict(v) for k, v in self.zones.items()},
            "irrigation": {str(k): dict(v) for k, v in self.irrigation.items()},
            "vine_states": self.vine_states,
            "usd_stage_log": self.usd_stage_log[-20:],
            "commands_log": self.commands_log[-10:],
        }

    def get_sensor_summary(self, zone_id: int = 2) -> Dict:
        """Return a flat sensor reading for a specific zone (for LLM input)."""
        z = self.zones.get(zone_id, self.zones[1])
        return {
            "temperature": z["temperature"],
            "humidity": z["humidity"],
            "soil_moisture": z["soil_moisture"],
            "anthocyanin_index": z["anthocyanin_index"],
            "brix": z["brix"],
            "uv_index": z["uv_index"],
            "stress_level": z["stress_level"],
            "day_hour": self.day_hour,
        }

    @staticmethod
    def _ts() -> str:
        return datetime.utcnow().strftime("%H:%M:%S")


class OmniverseService:
    def __init__(self):
        self.sessions: Dict[str, VineYard] = {}
        self._running: Dict[str, bool] = {}

    def create_vineyard(self, session_id: str) -> VineYard:
        vy = VineYard()
        self.sessions[session_id] = vy
        return vy

    def get_vineyard(self, session_id: str) -> Optional[VineYard]:
        return self.sessions.get(session_id)

    async def run_simulation_loop(
        self,
        session_id: str,
        emit: EventCallback,
        command_getter: Callable[[], Optional[Dict]],
        tick_interval: float = 3.0,
        max_ticks: int = 40,
    ):
        """Run the vineyard simulation loop, emitting events each tick."""
        vy = self.sessions.get(session_id)
        if not vy:
            vy = self.create_vineyard(session_id)
        self._running[session_id] = True

        await emit({
            "type": "omniverse.started",
            "data": {
                "message": "NVIDIA Omniverse Digital Twin initialised",
                "scene": "Smart_Vineyard_v2.usd",
                "zones": ZONES,
                "total_vines": TOTAL_VINES,
            }
        })
        await asyncio.sleep(1)

        for tick in range(max_ticks):
            if not self._running.get(session_id, False):
                break

            # Advance simulation
            state = vy.tick_simulation()

            # Emit sensor update every tick
            await emit({
                "type": "omniverse.sensor_update",
                "data": {
                    "tick": tick,
                    "state": state,
                }
            })

            # Every 5 ticks, request an LLM command
            if tick % 5 == 4:
                cmd = command_getter()
                if cmd:
                    result = vy.apply_command(
                        cmd.get("command", "MONITOR"),
                        cmd.get("parameters", {})
                    )
                    await emit({
                        "type": "omniverse.command_applied",
                        "data": {
                            "command": cmd,
                            "result": result,
                            "usd_log": state.get("usd_stage_log", [])[-5:],
                        }
                    })

            await asyncio.sleep(tick_interval)

        await emit({
            "type": "omniverse.completed",
            "data": {
                "message": "Simulation loop completed",
                "total_ticks": max_ticks,
                "final_state": state,
            }
        })
        self._running[session_id] = False

    def stop(self, session_id: str):
        self._running[session_id] = False


_omniverse: Optional[OmniverseService] = None


def get_omniverse() -> OmniverseService:
    global _omniverse
    if _omniverse is None:
        _omniverse = OmniverseService()
    return _omniverse
