"""
JSBSim-compatible 6-DOF Flight Dynamics Service.
Models a Boeing 737-800 on the JFK→LHR North Atlantic Track.

Equations:
  T(h)   = 15 - 6.5*(h_m/1000)              [ISA lapse rate, °C]
  ρ(h)   = 1.225 * (T(h)/288.15)^4.256      [air density, kg/m³]
  a(T)   = 340.29 * sqrt((T+273.15)/288.15) [speed of sound, m/s]
  TAS    = Mach * a(T)                       [true airspeed, m/s]
  D      = 0.5 * ρ * TAS² * S * CD          [drag, N]
  SFC    = SFC_base * η_oat * η_turb         [specific fuel consumption]
  ΔFuel  = SFC * D * Δt / 3600              [fuel burn per segment]
  ΔF     = |F_a - F_p| / F_p               [pressure signal ratio]
"""
import math
import random
import asyncio
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# ── Boeing 737-800 constants ─────────────────────────────────────────
WING_AREA_M2    = 124.6
CD0             = 0.0260   # zero-lift drag coefficient
AR              = 9.45     # aspect ratio
OSWALD          = 0.82     # Oswald efficiency
SFC_BASE        = 1.74e-5  # kg/(N·s)  (CFM56-7B cruise)
INIT_FUEL_KG    = 19_500   # JFK→LHR fuel load
OEW_KG          = 41_413   # operating empty weight
PAYLOAD_KG      = 16_000   # typical payload
MACH_CRUISE     = 0.785
MACH_DIVERGENCE = 0.840    # drag rises sharply above this
FL_CRUISE       = 35_000   # feet
CLIMB_RATE_FPM  = 1_800
DESCEND_RATE_FPM= 1_600
FT_TO_M         = 0.3048

# ── JFK→LHR waypoints (North Atlantic Track Bravo / Charlie) ────────
WAYPOINTS: List[Dict] = [
    {"id": "JFK",   "name": "New York JFK",    "lat":  40.6413, "lon": -73.7781, "phase": "ground"},
    {"id": "SHIPP", "name": "SHIPP (NE Coast)", "lat":  41.8,   "lon": -68.0,   "phase": "climb"},
    {"id": "TUNIT", "name": "TUNIT",            "lat":  43.5,   "lon": -55.0,   "phase": "cruise"},
    {"id": "GIRTS", "name": "GIRTS",            "lat":  46.0,   "lon": -43.0,   "phase": "cruise"},
    {"id": "SOMAX", "name": "SOMAX (Mid-Atl)",  "lat":  48.5,   "lon": -30.0,   "phase": "cruise"},
    {"id": "BEDRA", "name": "BEDRA",            "lat":  50.5,   "lon": -18.0,   "phase": "cruise"},
    {"id": "DOLIR", "name": "DOLIR (Ireland)",  "lat":  51.3,   "lon":  -8.0,   "phase": "descent"},
    {"id": "MIMKU", "name": "MIMKU",            "lat":  51.4,   "lon":  -2.0,   "phase": "descent"},
    {"id": "LHR",   "name": "London Heathrow",  "lat":  51.4700,"lon":  -0.4543,"phase": "arrival"},
]

# ── Anomaly schedule (triggers Pressure Loop) ───────────────────────
ANOMALIES: List[Dict] = [
    {"at_wp": 2, "type": "turbulence",     "severity": "moderate", "sfc_delta": +0.09,
     "desc": "CAT encountered at FL350 — unexpected moderate turbulence increases fuel burn 9%"},
    {"at_wp": 3, "type": "isa_deviation",  "severity": "high",     "sfc_delta": +0.13,
     "desc": "ISA+14°C temperature anomaly — warm air mass reduces engine efficiency 13%"},
    {"at_wp": 5, "type": "jet_stream_loss","severity": "medium",   "sfc_delta": +0.07,
     "desc": "Jet stream displaced 200nm south — aircraft exits tailwind core, GS drops 48 kts"},
    {"at_wp": 6, "type": "mach_divergence","severity": "low",      "sfc_delta": +0.05,
     "desc": "Step-climb attempted to FL370; approaching Mach divergence during acceleration"},
]


@dataclass
class AircraftState:
    # Position
    lat: float = 40.6413
    lon: float = -73.7781
    alt_ft: float = 0.0
    # Dynamics
    mach: float = 0.0
    tas_kts: float = 0.0
    gs_kts: float = 0.0
    heading: float = 56.0   # rough JFK→LHR bearing
    pitch_deg: float = 0.0
    bank_deg: float = 0.0
    vs_fpm: float = 0.0
    # Atmosphere
    oat_c: float = 15.0
    isa_dev_c: float = 0.0
    wind_kts: float = 0.0
    wind_dir: float = 270.0  # westerly (tailwind for eastbound)
    turb_level: float = 0.0  # 0=smooth, 1=severe
    # Fuel
    fuel_kg: float = INIT_FUEL_KG
    fuel_flow_kgh: float = 0.0
    gross_weight_kg: float = OEW_KG + PAYLOAD_KG + INIT_FUEL_KG
    # Predicted vs actual
    fuel_predicted: float = INIT_FUEL_KG
    pressure_delta: float = 0.0   # |F_a - F_p| / F_p
    # Navigation
    waypoint_index: int = 0
    phase: str = "ground"    # ground|climb|cruise|descent|arrival
    distance_nm_total: float = 0.0
    distance_nm_flown: float = 0.0
    ete_min: float = 0.0     # estimated time en-route (minutes)
    # Active anomaly
    active_anomaly: Optional[str] = None
    sfc_anomaly_factor: float = 1.0
    # Computed
    n1_pct: float = 0.0
    l_over_d: float = 0.0
    tick: int = 0


def isa_temperature(alt_ft: float, isa_dev: float = 0.0) -> float:
    """ISA temperature at altitude (°C)."""
    alt_m = alt_ft * FT_TO_M
    if alt_m < 11_000:
        return 15.0 - 6.5 * (alt_m / 1000) + isa_dev
    return -56.5 + isa_dev   # tropopause


def air_density(alt_ft: float, isa_dev: float = 0.0) -> float:
    """Air density ρ at altitude (kg/m³)."""
    T = isa_temperature(alt_ft, isa_dev) + 273.15
    return 1.225 * (T / 288.15) ** 4.256


def speed_of_sound(oat_c: float) -> float:
    """Speed of sound (m/s)."""
    return 340.29 * math.sqrt((oat_c + 273.15) / 288.15)


def mach_to_tas(mach: float, oat_c: float) -> float:
    """True airspeed (m/s) from Mach and OAT."""
    return mach * speed_of_sound(oat_c)


def drag_coefficient(cl: float, mach: float) -> float:
    """Drag polar including wave drag above Mach divergence."""
    cd_induced = cl ** 2 / (math.pi * AR * OSWALD)
    # Wave drag: rises sharply above M_div
    if mach > MACH_DIVERGENCE:
        cd_wave = 0.0015 * ((mach - MACH_DIVERGENCE) / 0.01) ** 2
    else:
        cd_wave = 0.0
    return CD0 + cd_induced + cd_wave


def haversine_nm(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in nautical miles."""
    R_nm = 3440.065
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return 2 * R_nm * math.asin(math.sqrt(a))


def great_circle_bearing(lat1, lon1, lat2, lon2) -> float:
    """Initial bearing (degrees) from point 1 to point 2."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)
    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def advance_position(lat, lon, bearing_deg, dist_nm) -> tuple:
    """Move position along a great circle."""
    R_nm = 3440.065
    δ = dist_nm / R_nm
    θ = math.radians(bearing_deg)
    φ1, λ1 = math.radians(lat), math.radians(lon)
    φ2 = math.asin(math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(θ))
    λ2 = λ1 + math.atan2(math.sin(θ) * math.sin(δ) * math.cos(φ1), math.cos(δ) - math.sin(φ1) * math.sin(φ2))
    return math.degrees(φ2), math.degrees(λ2)


class JSBSimService:
    """
    6-DOF flight dynamics for the B737-800 JFK→LHR.
    Advances the aircraft state each tick (≈ 3-min flight segments).
    """

    TICK_MIN = 3.0      # simulated minutes per tick
    PRESSURE_THRESH = 0.04   # 4% fuel deviation → pressure signal

    def __init__(self):
        self.state = AircraftState()
        self._total_distance()
        self._active_anomalies: Dict[int, Dict] = {a["at_wp"]: a for a in ANOMALIES}
        self._pressure_events: List[Dict] = []
        self._trajectory: List[Dict] = [
            {"lat": WAYPOINTS[0]["lat"], "lon": WAYPOINTS[0]["lon"], "alt_ft": 0}
        ]

    def _total_distance(self):
        d = 0.0
        for i in range(len(WAYPOINTS) - 1):
            d += haversine_nm(WAYPOINTS[i]["lat"], WAYPOINTS[i]["lon"],
                              WAYPOINTS[i + 1]["lat"], WAYPOINTS[i + 1]["lon"])
        self.state.distance_nm_total = round(d, 1)

    def tick(self) -> Dict:
        """Advance simulation by TICK_MIN minutes. Returns updated state dict."""
        s = self.state
        s.tick += 1

        wp_idx = min(s.waypoint_index, len(WAYPOINTS) - 1)
        wp = WAYPOINTS[wp_idx]
        s.phase = wp.get("phase", "cruise")

        # ── Apply anomaly at this waypoint ──────────────────────────
        if wp_idx in self._active_anomalies:
            a = self._active_anomalies[wp_idx]
            s.sfc_anomaly_factor = 1.0 + a["sfc_delta"]
            s.active_anomaly = a["type"]
            if a["type"] == "turbulence":
                s.turb_level = 0.6
            elif a["type"] == "isa_deviation":
                s.isa_dev_c = 14.0
            elif a["type"] == "jet_stream_loss":
                s.wind_kts = max(0, s.wind_kts - 55)
        else:
            s.sfc_anomaly_factor = max(1.0, s.sfc_anomaly_factor * 0.92)
            s.turb_level = max(0, s.turb_level - 0.1)
            s.isa_dev_c = max(0, s.isa_dev_c * 0.85)
            s.active_anomaly = None

        # ── Altitude & phase management ─────────────────────────────
        if s.phase == "ground":
            s.alt_ft = 0
            s.mach = 0
            s.vs_fpm = 0
        elif s.phase == "climb":
            target = FL_CRUISE * FT_TO_M * 0.7  # partially climbed at first WP
            s.alt_ft = min(FL_CRUISE, s.alt_ft + CLIMB_RATE_FPM * self.TICK_MIN)
            s.vs_fpm = CLIMB_RATE_FPM if s.alt_ft < FL_CRUISE else 0
            s.mach = 0.72 + (s.alt_ft / FL_CRUISE) * 0.065   # accelerates to cruise Mach
            s.pitch_deg = 8.0 - (s.alt_ft / FL_CRUISE) * 5.0
        elif s.phase == "cruise":
            s.alt_ft = FL_CRUISE + random.gauss(0, 20)
            s.mach = MACH_CRUISE + random.gauss(0, 0.003)
            s.vs_fpm = random.gauss(0, 30)
            s.pitch_deg = 2.5
        elif s.phase == "descent":
            s.alt_ft = max(0, s.alt_ft - DESCEND_RATE_FPM * self.TICK_MIN)
            s.mach = max(0.45, s.mach - 0.015)
            s.vs_fpm = -DESCEND_RATE_FPM
            s.pitch_deg = -3.0
        elif s.phase == "arrival":
            s.alt_ft = max(0, s.alt_ft - 800 * self.TICK_MIN)
            s.mach = max(0.35, s.mach - 0.02)
            s.vs_fpm = -800
            s.pitch_deg = -4.0

        # ── Atmosphere ───────────────────────────────────────────────
        s.oat_c = isa_temperature(s.alt_ft, s.isa_dev_c)
        rho = air_density(s.alt_ft, s.isa_dev_c)

        # ── Jet stream (strongest 45-52°N, FL310-FL390) ──────────────
        if 43 <= s.lat <= 53 and s.alt_ft > 28_000:
            if s.wind_kts < 80:
                s.wind_kts = min(90, s.wind_kts + 6 + random.gauss(0, 3))
        else:
            s.wind_kts = max(15, s.wind_kts - 4)
        s.wind_kts = max(0, s.wind_kts + random.gauss(0, 2))

        # ── TAS / GS ─────────────────────────────────────────────────
        tas_ms = mach_to_tas(max(s.mach, 0.01), s.oat_c)
        s.tas_kts = tas_ms / 0.5144
        wind_component = s.wind_kts * 0.85   # mostly tailwind for eastbound
        s.gs_kts = s.tas_kts + wind_component

        # ── Aerodynamics ─────────────────────────────────────────────
        s.gross_weight_kg = OEW_KG + PAYLOAD_KG + s.fuel_kg
        if rho > 0 and tas_ms > 10:
            cl = (2 * s.gross_weight_kg * 9.81) / (rho * tas_ms ** 2 * WING_AREA_M2)
            cl = max(0.1, min(1.5, cl))
        else:
            cl = 0.5
        cd = drag_coefficient(cl, s.mach)
        drag_n = 0.5 * rho * tas_ms ** 2 * WING_AREA_M2 * cd
        s.l_over_d = round(cl / cd, 2)

        # ── Engine ────────────────────────────────────────────────────
        s.n1_pct = 85 + (drag_n / 120_000) * 15 + s.turb_level * 3
        s.n1_pct = min(102, max(0, s.n1_pct))

        # ── Fuel burn ─────────────────────────────────────────────────
        # Predicted (without anomalies)
        dt_s = self.TICK_MIN * 60
        fuel_flow_kgs = SFC_BASE * drag_n
        predicted_burn = fuel_flow_kgs * dt_s
        s.fuel_predicted = max(0, s.fuel_predicted - predicted_burn)

        # Actual (with anomalies)
        actual_sfc = SFC_BASE * s.sfc_anomaly_factor * (1 + 0.03 * s.turb_level)
        actual_fuel_flow = actual_sfc * drag_n
        actual_burn = actual_fuel_flow * dt_s
        s.fuel_kg = max(0, s.fuel_kg - actual_burn)
        s.fuel_flow_kgh = round(actual_fuel_flow * 3600, 1)

        # ── Pressure Loop detection ───────────────────────────────────
        pred_remaining = s.fuel_predicted
        actual_remaining = s.fuel_kg
        if pred_remaining > 0 and s.phase != "ground":
            s.pressure_delta = abs(actual_remaining - pred_remaining) / max(pred_remaining, 1)
            if s.pressure_delta > self.PRESSURE_THRESH and s.active_anomaly:
                self._pressure_events.append({
                    "tick": s.tick,
                    "waypoint": wp["id"],
                    "delta": round(s.pressure_delta, 4),
                    "anomaly": s.active_anomaly,
                    "f_predicted": round(pred_remaining, 1),
                    "f_actual": round(actual_remaining, 1),
                    "desc": self._active_anomalies.get(wp_idx, {}).get("desc", "Deviation detected"),
                })

        # ── Navigation: advance toward next waypoint ──────────────────
        if wp_idx < len(WAYPOINTS) - 1:
            next_wp = WAYPOINTS[wp_idx + 1]
            dist_to_next = haversine_nm(s.lat, s.lon, next_wp["lat"], next_wp["lon"])
            dist_covered = s.gs_kts / 60 * self.TICK_MIN
            s.distance_nm_flown += dist_covered

            bearing = great_circle_bearing(s.lat, s.lon, next_wp["lat"], next_wp["lon"])
            s.heading = bearing
            if dist_covered >= dist_to_next:
                s.lat = next_wp["lat"]
                s.lon = next_wp["lon"]
                s.waypoint_index = min(wp_idx + 1, len(WAYPOINTS) - 1)
            else:
                s.lat, s.lon = advance_position(s.lat, s.lon, bearing, dist_covered)
        else:
            # Final approach
            s.lat = WAYPOINTS[-1]["lat"]
            s.lon = WAYPOINTS[-1]["lon"]

        # ── ETE ───────────────────────────────────────────────────────
        remaining_nm = s.distance_nm_total - s.distance_nm_flown
        if s.gs_kts > 0:
            s.ete_min = round(remaining_nm / s.gs_kts * 60, 0)

        # ── Trajectory ───────────────────────────────────────────────
        self._trajectory.append({"lat": round(s.lat, 4), "lon": round(s.lon, 4), "alt_ft": round(s.alt_ft, 0)})

        return self.to_dict()

    def to_dict(self) -> Dict:
        d = asdict(self.state)
        d["waypoints"] = WAYPOINTS
        d["trajectory"] = self._trajectory[-60:]   # last 60 points
        d["pressure_events"] = self._pressure_events[-10:]
        d["current_waypoint"] = WAYPOINTS[min(self.state.waypoint_index, len(WAYPOINTS) - 1)]
        d["next_waypoint"] = WAYPOINTS[min(self.state.waypoint_index + 1, len(WAYPOINTS) - 1)]
        return d

    def get_predicted_fuel(self, n_ticks: int = 1) -> float:
        """Predict fuel burn for next n ticks."""
        s = self.state
        rho = air_density(s.alt_ft, s.isa_dev_c)
        tas_ms = mach_to_tas(max(s.mach, 0.01), s.oat_c)
        cl = max(0.1, (2 * s.gross_weight_kg * 9.81) / max(rho * tas_ms ** 2 * WING_AREA_M2, 1))
        cd = drag_coefficient(cl, s.mach)
        drag_n = 0.5 * rho * tas_ms ** 2 * WING_AREA_M2 * cd
        return SFC_BASE * drag_n * self.TICK_MIN * 60 * n_ticks

    @property
    def is_arrived(self) -> bool:
        return self.state.waypoint_index >= len(WAYPOINTS) - 1 and self.state.alt_ft < 500

    @property
    def latest_pressure_event(self) -> Optional[Dict]:
        return self._pressure_events[-1] if self._pressure_events else None
