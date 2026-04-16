<template>
  <div class="relative w-full h-full bg-slate-950 overflow-hidden">

    <!-- ── HUD overlay ─────────────────────────────────────────────── -->
    <div class="absolute top-3 left-3 z-10 flex flex-col gap-2 pointer-events-none">
      <!-- Route info bar -->
      <div class="bg-slate-950/85 backdrop-blur-md rounded-xl border border-slate-700/80
                  px-3 py-2 flex items-center gap-3 text-xs text-slate-300 shadow-lg">
        <span class="text-sky-400 font-bold tracking-wider">JFK → LHR</span>
        <div class="w-px h-4 bg-slate-700"/>
        <template v-if="flight">
          <span>FL<span class="text-white font-mono font-bold ml-0.5">{{ fl }}</span></span>
          <div class="w-px h-4 bg-slate-700"/>
          <span>M<span class="text-amber-400 font-mono font-bold ml-0.5">{{ mach }}</span></span>
          <div class="w-px h-4 bg-slate-700"/>
          <span><span class="text-emerald-400 font-mono font-bold">{{ fuel }}</span><span class="text-slate-500"> kg</span></span>
          <div class="w-px h-4 bg-slate-700"/>
          <span><span class="text-cyan-400 font-mono font-bold">{{ gs }}</span><span class="text-slate-500"> kt GS</span></span>
        </template>
        <template v-else>
          <span class="text-slate-600 italic">Awaiting flight data…</span>
        </template>
      </div>

      <!-- Anomaly alert -->
      <Transition name="fade">
        <div v-if="flight?.active_anomaly"
             class="bg-red-950/90 border border-red-600/80 rounded-xl px-3 py-2
                    text-xs text-red-300 font-semibold shadow-lg shadow-red-950/50
                    flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-red-400 animate-pulse flex-shrink-0"/>
          ⚠️ {{ anomalyLabel(flight.active_anomaly) }}
        </div>
      </Transition>

      <!-- Weather legend -->
      <div v-if="started"
           class="bg-slate-950/80 backdrop-blur-sm rounded-xl border border-slate-800
                  px-3 py-2 space-y-1.5 text-[10px] text-slate-400">
        <p class="text-slate-500 font-bold uppercase tracking-widest text-[9px]">Weather</p>
        <div class="flex items-center gap-1.5"><span class="w-3 h-2 rounded-sm bg-sky-500/50 border border-sky-400/40 flex-shrink-0"/>Jet Stream</div>
        <div class="flex items-center gap-1.5"><span class="w-3 h-2 rounded-sm bg-orange-500/50 border border-orange-400/40 flex-shrink-0"/>CAT / Turbulence</div>
        <div class="flex items-center gap-1.5"><span class="w-3 h-2 rounded-sm bg-yellow-500/40 border border-yellow-400/30 flex-shrink-0"/>ISA Deviation</div>
        <div class="flex items-center gap-1.5"><span class="w-3 h-2 rounded-sm bg-slate-300/30 border border-slate-400/30 flex-shrink-0"/>Cloud Systems</div>
      </div>
    </div>

    <!-- ── Camera controls ────────────────────────────────────────── -->
    <div class="absolute top-3 right-3 z-10 flex flex-col gap-1.5">
      <button @click="followAircraft = !followAircraft"
              :class="['backdrop-blur-sm border rounded-xl px-3 py-1.5 text-xs font-medium transition-all shadow',
                       followAircraft
                         ? 'bg-sky-900/80 border-sky-500 text-sky-300'
                         : 'bg-slate-900/80 border-slate-700 text-slate-400 hover:text-white']">
        {{ followAircraft ? '🔒 Tracking' : '🔓 Free' }}
      </button>
      <button @click="setCameraAngle('cockpit')"
              class="bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-400 hover:text-white backdrop-blur-sm">
        🎯 Cockpit
      </button>
      <button @click="setCameraAngle('overview')"
              class="bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-400 hover:text-white backdrop-blur-sm">
        🌍 Overview
      </button>
      <button @click="toggleMode"
              class="bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-400 hover:text-white backdrop-blur-sm">
        {{ mode2D ? '🌍 3D' : '🗺️ 2D' }}
      </button>
    </div>

    <!-- Phase + status badge -->
    <div v-if="flight?.phase" class="absolute bottom-4 left-3 z-10 flex items-center gap-2">
      <span :class="['px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shadow-lg', phaseBadge(flight.phase)]">
        {{ flight.phase }}
      </span>
      <span v-if="flight?.turb_level > 0.3"
            :class="['px-3 py-1 rounded-full text-xs font-semibold shadow-lg animate-pulse',
                     flight.turb_level > 0.6 ? 'bg-red-900/80 text-red-300 border border-red-700'
                                             : 'bg-orange-900/80 text-orange-300 border border-orange-700']">
        {{ flight.turb_level > 0.6 ? 'MODERATE CAT' : 'LIGHT CAT' }}
      </span>
    </div>

    <!-- Standby -->
    <div v-if="!started" class="absolute inset-0 flex items-center justify-center">
      <div class="text-center text-slate-500">
        <div class="text-6xl mb-4 animate-pulse">🌍</div>
        <p class="font-bold text-slate-400 text-lg">CesiumJS — North Atlantic</p>
        <p class="text-sm mt-1">3D Globe with live weather simulation</p>
        <p class="text-xs mt-2 text-slate-600">Flight simulation will appear when session starts</p>
      </div>
    </div>

    <!-- Cesium container -->
    <div ref="cesiumContainer" class="w-full h-full" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'

const props = defineProps({
  flightState: { type: Object, default: null },
  trajectory:  { type: Array,  default: () => [] },
  waypoints:   { type: Array,  default: () => [] },
})

const cesiumContainer = ref(null)
const followAircraft  = ref(true)
const mode2D          = ref(false)
const started         = ref(false)
const flight          = computed(() => props.flightState)

// HUD computed values
const fl   = computed(() => Math.round((flight.value?.alt_ft  || 0) / 100))
const mach = computed(() => (flight.value?.mach  || 0).toFixed(3))
const fuel = computed(() => Math.round(flight.value?.fuel_kg || 0).toLocaleString())
const gs   = computed(() => Math.round(flight.value?.gs_kts  || 0))

let viewer            = null
let C                 = null
let aircraftEntity    = null
let trailEntity       = null
let altLineEntity     = null
let weatherEntities   = []   // cleared + rebuilt on anomaly change
let _lastAnomaly      = null
let _lastTurb         = -1

// ── Initialise Cesium ─────────────────────────────────────────────
async function initCesium() {
  if (!cesiumContainer.value) return
  try {
    C = await import('cesium')
    C.Ion.defaultAccessToken = ''

    viewer = new C.Viewer(cesiumContainer.value, {
      imageryProvider: new C.UrlTemplateImageryProvider({
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        credit: '© OpenStreetMap contributors',
        maximumLevel: 18,
      }),
      baseLayerPicker:        false,
      geocoder:               false,
      homeButton:             false,
      sceneModePicker:        false,
      navigationHelpButton:   false,
      animation:              false,
      timeline:               false,
      fullscreenButton:       false,
      infoBox:                false,
      selectionIndicator:     false,
      shouldAnimate:          true,
    })

    viewer.terrainProvider      = new C.EllipsoidTerrainProvider()
    viewer.scene.backgroundColor = C.Color.fromCssColorString('#03060e')
    viewer.scene.globe.baseColor = C.Color.fromCssColorString('#0a1628')

    // Initial camera — North Atlantic wide view
    viewer.camera.setView({
      destination: C.Cartesian3.fromDegrees(-35, 46, 9_500_000),
      orientation: { heading: 0, pitch: -C.Math.PI_OVER_TWO, roll: 0 },
    })

    // Build scene
    buildStaticScene()
    started.value = true
  } catch (e) {
    console.warn('Cesium init error:', e)
  }
}

// ── Static scene (jet stream, clouds, pressure cells, route arc) ──
function buildStaticScene() {
  addGreatCircleRoute()
  addJetStream()
  addCloudSystems()
  addPressureCenters()
  addWaypointMarkers()
}

function addGreatCircleRoute() {
  // Planned great-circle route — shown as a dashed planning line
  const wps = props.waypoints.length ? props.waypoints : FALLBACK_WAYPOINTS
  if (wps.length < 2) return
  viewer.entities.add({
    polyline: {
      positions: wps.map(w => C.Cartesian3.fromDegrees(w.lon, w.lat, 11_500)),
      width: 1.5,
      material: new C.PolylineDashMaterialProperty({
        color: C.Color.fromCssColorString('#334155').withAlpha(0.7),
        dashLength: 16,
      }),
    }
  })
}

function addJetStream() {
  // Core corridor
  const coreLons = Array.from({ length: 20 }, (_, i) => -74 + i * 5)
  viewer.entities.add({
    corridor: {
      positions: coreLons.map(lon => C.Cartesian3.fromDegrees(lon, 48.5, 11_200)),
      width: 650_000,
      height: 11_200,
      material: new C.ColorMaterialProperty(C.Color.fromCssColorString('#38bdf8').withAlpha(0.10)),
      outline: false,
    }
  })
  // Outer diffuse halo
  viewer.entities.add({
    corridor: {
      positions: coreLons.map(lon => C.Cartesian3.fromDegrees(lon, 48.5, 11_100)),
      width: 1_100_000,
      height: 11_100,
      material: new C.ColorMaterialProperty(C.Color.fromCssColorString('#0ea5e9').withAlpha(0.05)),
    }
  })
  // Wind direction arrows along jet stream
  const arrowLons = [-65, -50, -35, -20, -5]
  arrowLons.forEach(lon => {
    viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, 48.5, 11_400),
      billboard: {
        image:  createWindArrowCanvas(),
        width:  28, height: 28,
        verticalOrigin: C.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        rotation: C.Math.toRadians(90), // pointing east
        alignedAxis: C.Cartesian3.UNIT_Z,
      }
    })
  })
  // "JET STREAM" label at centre
  viewer.entities.add({
    position: C.Cartesian3.fromDegrees(-30, 50.5, 11_800),
    label: {
      text: '◀ JET STREAM CORE ▶',
      font: 'bold 11px "Inter", monospace',
      fillColor: C.Color.fromCssColorString('#7dd3fc').withAlpha(0.85),
      outlineColor: C.Color.fromCssColorString('#0c2742'),
      outlineWidth: 3,
      style: C.LabelStyle.FILL_AND_OUTLINE,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      pixelOffset: new C.Cartesian2(0, 0),
    }
  })
}

function addCloudSystems() {
  // Scattered mid-Atlantic cloud systems at ~8 km (cirrus layer)
  const clouds = [
    { lon: -60, lat: 42, rx: 400_000, ry: 250_000, a: 0.12 },
    { lon: -44, lat: 50, rx: 300_000, ry: 200_000, a: 0.10 },
    { lon: -30, lat: 47, rx: 500_000, ry: 280_000, a: 0.09 },
    { lon: -18, lat: 52, rx: 350_000, ry: 200_000, a: 0.13 },
    { lon: -10, lat: 44, rx: 280_000, ry: 180_000, a: 0.08 },
    // Lower stratus near British Isles
    { lon: -8,  lat: 53, rx: 450_000, ry: 300_000, a: 0.18 },
    // Frontal cloud band
    { lon: -50, lat: 38, rx: 700_000, ry: 200_000, a: 0.09 },
  ]
  clouds.forEach(c => {
    viewer.entities.add({
      position: C.Cartesian3.fromDegrees(c.lon, c.lat, 8_000),
      ellipse: {
        semiMajorAxis: c.rx,
        semiMinorAxis: c.ry,
        height: 8_000,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#e2e8f0').withAlpha(c.a)
        ),
        outline: false,
        rotation: C.Math.toRadians(15),
      }
    })
    // Second diffuse layer
    viewer.entities.add({
      position: C.Cartesian3.fromDegrees(c.lon, c.lat, 7_200),
      ellipse: {
        semiMajorAxis: c.rx * 1.3,
        semiMinorAxis: c.ry * 1.3,
        height: 7_200,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#cbd5e1').withAlpha(c.a * 0.5)
        ),
        outline: false,
      }
    })
  })
}

function addPressureCenters() {
  // North Atlantic Low (typical Icelandic Low position)
  addPressureLabel(-24, 63, 'L', '#ef4444', 'Low Pressure\n964 hPa')
  // Azores High
  addPressureLabel(-28, 36, 'H', '#22c55e', 'Azores High\n1028 hPa')
  // Secondary low
  addPressureLabel(-58, 45, 'L', '#f97316', 'Deep Low\n980 hPa')
}

function addPressureLabel(lon, lat, type, color, tooltip) {
  viewer.entities.add({
    position: C.Cartesian3.fromDegrees(lon, lat, 5_000),
    billboard: {
      image:  createPressureCanvas(type, color),
      width: 44, height: 44,
      verticalOrigin: C.VerticalOrigin.CENTER,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    description: tooltip,
  })
}

function addWaypointMarkers() {
  const wps = props.waypoints.length ? props.waypoints : FALLBACK_WAYPOINTS
  wps.forEach((wp, i) => {
    const isEndpoint = i === 0 || i === wps.length - 1
    viewer.entities.add({
      position: C.Cartesian3.fromDegrees(wp.lon, wp.lat, 11_600),
      billboard: {
        image: createWaypointCanvas(wp.id, isEndpoint),
        width: isEndpoint ? 40 : 28,
        height: isEndpoint ? 40 : 28,
        verticalOrigin: C.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: wp.name || wp.id,
        font: `${isEndpoint ? 'bold ' : ''}10px Inter, sans-serif`,
        fillColor: isEndpoint ? C.Color.fromCssColorString('#f0f9ff') : C.Color.fromCssColorString('#94a3b8'),
        outlineColor: C.Color.fromCssColorString('#03060e'),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new C.Cartesian2(0, isEndpoint ? -26 : -20),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    })
  })
}

// ── Dynamic weather (cleared + rebuilt when anomaly changes) ──────
function updateWeather(state) {
  if (!viewer || !C || !state) return

  const anomaly = state.active_anomaly || null
  const turb    = state.turb_level || 0
  const isa     = state.isa_dev_c  || 0

  const changed = anomaly !== _lastAnomaly || Math.abs(turb - _lastTurb) > 0.15
  if (!changed) return

  _lastAnomaly = anomaly
  _lastTurb    = turb

  // Remove old dynamic weather entities
  weatherEntities.forEach(e => { try { viewer.entities.remove(e) } catch {} })
  weatherEntities = []

  const lat = state.lat || 48
  const lon = state.lon || -30

  // ── Turbulence zone ──
  if (turb > 0.25) {
    const radius   = 280_000 + turb * 400_000
    const alpha    = 0.15 + turb * 0.3
    const color    = turb > 0.6 ? '#ef4444' : '#f97316'

    // Inner hot core
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, lat, 11_000),
      ellipse: {
        semiMajorAxis: radius * 0.5,
        semiMinorAxis: radius * 0.35,
        height: 11_000,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString(color).withAlpha(alpha * 1.4)
        ),
        outline: true,
        outlineColor: new C.ColorMaterialProperty(C.Color.fromCssColorString(color).withAlpha(0.6)),
        outlineWidth: 2,
        rotation: C.Math.toRadians(30),
      }
    }))
    // Outer diffuse halo
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, lat, 11_000),
      ellipse: {
        semiMajorAxis: radius,
        semiMinorAxis: radius * 0.65,
        height: 11_000,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString(color).withAlpha(alpha * 0.4)
        ),
        rotation: C.Math.toRadians(30),
      }
    }))
    // CAT label
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, lat + 2.5, 12_000),
      label: {
        text: turb > 0.6 ? '⚡ MODERATE CAT' : '~ LIGHT CAT',
        font: 'bold 12px Inter, sans-serif',
        fillColor: C.Color.fromCssColorString(turb > 0.6 ? '#fca5a5' : '#fdba74').withAlpha(0.95),
        outlineColor: C.Color.fromCssColorString('#1a0505'),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    }))
  }

  // ── ISA deviation zone ──
  if (anomaly === 'isa_deviation' || isa > 8) {
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon - 2, lat - 1, 10_500),
      ellipse: {
        semiMajorAxis: 550_000,
        semiMinorAxis: 380_000,
        height: 10_500,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#fbbf24').withAlpha(0.13)
        ),
        rotation: C.Math.toRadians(-15),
      }
    }))
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon - 2, lat - 1, 10_600),
      ellipse: {
        semiMajorAxis: 280_000,
        semiMinorAxis: 190_000,
        height: 10_600,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#f59e0b').withAlpha(0.20)
        ),
        rotation: C.Math.toRadians(-15),
      }
    }))
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon - 2, lat + 2, 12_000),
      label: {
        text: `🌡 ISA +${Math.round(isa || 14)}°C`,
        font: 'bold 11px Inter, sans-serif',
        fillColor: C.Color.fromCssColorString('#fde68a').withAlpha(0.95),
        outlineColor: C.Color.fromCssColorString('#1a0d00'),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    }))
  }

  // ── Jet stream loss — show displaced stream ──
  if (anomaly === 'jet_stream_loss') {
    const lons = Array.from({ length: 8 }, (_, i) => lon + i * 4)
    weatherEntities.push(viewer.entities.add({
      corridor: {
        positions: lons.map(l => C.Cartesian3.fromDegrees(l, 43, 11_200)),
        width: 500_000,
        height: 11_200,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#94a3b8').withAlpha(0.15)
        ),
      }
    }))
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon + 10, 44, 12_000),
      label: {
        text: '↘ JET STREAM DISPLACED',
        font: 'bold 11px Inter, sans-serif',
        fillColor: C.Color.fromCssColorString('#94a3b8').withAlpha(0.9),
        outlineColor: C.Color.fromCssColorString('#0f172a'),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    }))
  }

  // ── Mach divergence zone — high-Mach warning bubble ──
  if (anomaly === 'mach_divergence') {
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, lat, 11_200),
      ellipse: {
        semiMajorAxis: 180_000,
        semiMinorAxis: 120_000,
        height: 11_200,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#a855f7').withAlpha(0.20)
        ),
      }
    }))
    weatherEntities.push(viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lon, lat + 1.5, 12_000),
      label: {
        text: '⚠ MACH DIVERGENCE',
        font: 'bold 11px Inter, sans-serif',
        fillColor: C.Color.fromCssColorString('#d8b4fe').withAlpha(0.95),
        outlineColor: C.Color.fromCssColorString('#1a0030'),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    }))
  }
}

// ── Aircraft update ───────────────────────────────────────────────
watch(() => props.flightState, (state) => {
  if (!state || !viewer || !C) return

  const alt  = (state.alt_ft || 0) * 0.3048
  const pos  = C.Cartesian3.fromDegrees(state.lon, state.lat, alt)

  // ── Create aircraft entities on first update ──
  if (!aircraftEntity) {
    aircraftEntity = viewer.entities.add({
      position: pos,
      billboard: {
        image: createAircraftCanvas(state.throttle_pct),
        width:  72,
        height: 72,
        rotation: C.Math.toRadians(-(state.heading || 56)),
        alignedAxis: C.Cartesian3.UNIT_Z,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        verticalOrigin: C.VerticalOrigin.CENTER,
        scaleByDistance: new C.NearFarScalar(1e6, 1.4, 8e6, 0.7),
      }
    })

    // Contrail / trajectory trail
    trailEntity = viewer.entities.add({
      polyline: {
        positions: new C.CallbackProperty(() =>
          props.trajectory.map(p => C.Cartesian3.fromDegrees(p.lon, p.lat, p.alt_ft * 0.3048)),
          false
        ),
        width: 3,
        material: new C.PolylineGlowMaterialProperty({
          color: C.Color.fromCssColorString('#818cf8').withAlpha(0.85),
          glowPower: 0.25,
          taperPower: 0.6,
        }),
        clampToGround: false,
        arcType: C.ArcType.NONE,
      }
    })

    // Vertical altitude indicator (line from aircraft to ground)
    altLineEntity = viewer.entities.add({
      polyline: {
        positions: new C.CallbackProperty(() => {
          if (!props.flightState) return []
          const s = props.flightState
          return [
            C.Cartesian3.fromDegrees(s.lon, s.lat, (s.alt_ft || 0) * 0.3048),
            C.Cartesian3.fromDegrees(s.lon, s.lat, 0),
          ]
        }, false),
        width: 1,
        material: new C.ColorMaterialProperty(
          C.Color.fromCssColorString('#6366f1').withAlpha(0.25)
        ),
        clampToGround: false,
      }
    })
  } else {
    // Update position + rotation
    aircraftEntity.position = pos
    aircraftEntity.billboard.rotation = C.Math.toRadians(-(state.heading || 56))
    // Redraw aircraft canvas (engine glow changes with throttle)
    aircraftEntity.billboard.image = createAircraftCanvas(state.throttle_pct)
  }

  // Update dynamic weather
  updateWeather(state)

  // Camera follow
  if (followAircraft.value) {
    viewer.camera.lookAt(
      pos,
      new C.HeadingPitchRange(
        C.Math.toRadians((state.heading || 56) - 5),
        C.Math.toRadians(-28),
        850_000
      )
    )
  }
}, { deep: true })

// Rebuild waypoints when they arrive
watch(() => props.waypoints, (wps) => {
  if (!wps.length || !viewer || !C) return
  viewer.entities.removeAll()
  aircraftEntity = null
  trailEntity    = null
  altLineEntity  = null
  weatherEntities = []
  _lastAnomaly   = null
  _lastTurb      = -1
  buildStaticScene()
}, { deep: true })

// ── Canvas builders ───────────────────────────────────────────────

/**
 * Realistic top-down B737-800 silhouette.
 * Rendered at 80×80px with fuselage, swept wings, engine nacelles,
 * horizontal/vertical stabilizers, window row, wingtip nav lights,
 * and engine exhaust glow that intensifies with throttle.
 */
function createAircraftCanvas(throttlePct = 85) {
  const sz  = 80
  const cv  = document.createElement('canvas')
  cv.width  = sz
  cv.height = sz
  const ctx = cv.getContext('2d')

  ctx.translate(sz / 2, sz / 2)

  // ── Glow halo ──
  ctx.shadowColor = '#a5b4fc'
  ctx.shadowBlur  = 14

  // ── Fuselage ──
  const fuseGrad = ctx.createLinearGradient(-4, -30, 4, 30)
  fuseGrad.addColorStop(0,   '#f8fafc')
  fuseGrad.addColorStop(0.3, '#e2e8f0')
  fuseGrad.addColorStop(0.7, '#cbd5e1')
  fuseGrad.addColorStop(1,   '#94a3b8')
  ctx.fillStyle   = fuseGrad
  ctx.strokeStyle = '#c7d2fe'
  ctx.lineWidth   = 0.6
  ctx.beginPath()
  ctx.ellipse(0, 0, 4.5, 29, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.stroke()

  // ── Left wing (35° sweep) ──
  const lwGrad = ctx.createLinearGradient(-30, 0, 0, 0)
  lwGrad.addColorStop(0, '#94a3b8')
  lwGrad.addColorStop(1, '#f1f5f9')
  ctx.fillStyle   = lwGrad
  ctx.strokeStyle = '#a0aec0'
  ctx.lineWidth   = 0.5
  ctx.beginPath()
  ctx.moveTo(-2.5, -9)   // root front
  ctx.lineTo(-30,   4)   // tip front
  ctx.lineTo(-27,   9)   // tip rear
  ctx.lineTo(-1.5,  3)   // root rear
  ctx.closePath()
  ctx.fill(); ctx.stroke()

  // ── Right wing ──
  const rwGrad = ctx.createLinearGradient(0, 0, 30, 0)
  rwGrad.addColorStop(0, '#f1f5f9')
  rwGrad.addColorStop(1, '#94a3b8')
  ctx.fillStyle = rwGrad
  ctx.beginPath()
  ctx.moveTo(2.5, -9)
  ctx.lineTo(30,   4)
  ctx.lineTo(27,   9)
  ctx.lineTo(1.5,  3)
  ctx.closePath()
  ctx.fill(); ctx.stroke()

  // ── Wing root fairings (subtle blend) ──
  ctx.fillStyle = 'rgba(203,213,225,0.4)'
  ctx.beginPath()
  ctx.ellipse(-3, -2, 4, 8, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.ellipse(3, -2, 4, 8, 0, 0, Math.PI * 2)
  ctx.fill()

  // ── Engine nacelles ──
  const engColor = '#374151'
  const drawEngine = (x, y) => {
    ctx.fillStyle = engColor
    ctx.beginPath()
    ctx.ellipse(x, y, 3.5, 7.5, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#6b7280'
    ctx.lineWidth = 0.5
    ctx.stroke()
    // Inlet highlight ring
    ctx.fillStyle = '#4b5563'
    ctx.beginPath()
    ctx.ellipse(x, y - 5.5, 2.8, 1.5, 0, 0, Math.PI * 2)
    ctx.fill()
  }
  drawEngine(-18, 2)
  drawEngine( 18, 2)

  // ── Engine exhaust glow (proportional to throttle) ──
  const glow = Math.min(1, (throttlePct || 85) / 100)
  const drawExhaust = (x) => {
    const g = ctx.createRadialGradient(x, 8.5, 0, x, 8.5, 6)
    g.addColorStop(0, `rgba(251,191,36,${0.65 * glow})`)
    g.addColorStop(0.5, `rgba(251,146,60,${0.3 * glow})`)
    g.addColorStop(1, 'rgba(251,146,60,0)')
    ctx.fillStyle = g
    ctx.shadowColor = '#fb923c'
    ctx.shadowBlur  = 8 * glow
    ctx.beginPath()
    ctx.ellipse(x, 9.5, 3, 5 * glow + 1, 0, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.shadowBlur = 0
  drawExhaust(-18)
  drawExhaust( 18)
  ctx.shadowBlur  = 14
  ctx.shadowColor = '#a5b4fc'

  // ── Horizontal stabilizers ──
  ctx.fillStyle   = '#d1d5db'
  ctx.strokeStyle = '#9ca3af'
  ctx.lineWidth   = 0.5
  // Left
  ctx.beginPath()
  ctx.moveTo(-1.5, 19); ctx.lineTo(-13, 24.5); ctx.lineTo(-12, 27.5); ctx.lineTo(-1.5, 22.5)
  ctx.closePath(); ctx.fill(); ctx.stroke()
  // Right
  ctx.beginPath()
  ctx.moveTo(1.5, 19); ctx.lineTo(13, 24.5); ctx.lineTo(12, 27.5); ctx.lineTo(1.5, 22.5)
  ctx.closePath(); ctx.fill(); ctx.stroke()

  // ── Vertical fin (subtle, top view) ──
  ctx.fillStyle = 'rgba(203,213,225,0.5)'
  ctx.beginPath()
  ctx.moveTo(0, 18); ctx.lineTo(-1, 28); ctx.lineTo(1, 28)
  ctx.closePath(); ctx.fill()

  // ── Nose specular highlight ──
  ctx.shadowBlur  = 0
  ctx.fillStyle   = 'rgba(255,255,255,0.55)'
  ctx.beginPath()
  ctx.ellipse(-1.2, -25, 1.2, 3, 0, 0, Math.PI * 2)
  ctx.fill()

  // ── Fuselage window row ──
  ctx.shadowBlur  = 0
  ctx.fillStyle   = '#bfdbfe'
  for (let i = -4; i <= 2; i++) {
    ctx.beginPath()
    ctx.ellipse(-0.8, i * 4.5 + 2, 1.0, 0.8, 0, 0, Math.PI * 2)
    ctx.fill()
  }

  // ── Wingtip nav lights ──
  // Left (red)
  ctx.fillStyle   = '#ef4444'
  ctx.shadowColor = '#ef4444'
  ctx.shadowBlur  = 7
  ctx.beginPath()
  ctx.arc(-29, 7, 1.8, 0, Math.PI * 2)
  ctx.fill()
  // Right (green)
  ctx.fillStyle   = '#22c55e'
  ctx.shadowColor = '#22c55e'
  ctx.beginPath()
  ctx.arc(29, 7, 1.8, 0, Math.PI * 2)
  ctx.fill()
  // Tail beacon (white)
  ctx.fillStyle   = '#ffffff'
  ctx.shadowColor = '#ffffff'
  ctx.shadowBlur  = 5
  ctx.beginPath()
  ctx.arc(0, 28, 1.4, 0, Math.PI * 2)
  ctx.fill()

  ctx.shadowBlur = 0
  return cv
}

function createWindArrowCanvas() {
  const cv  = document.createElement('canvas')
  cv.width  = 28; cv.height = 28
  const ctx = cv.getContext('2d')
  ctx.translate(14, 14)
  ctx.strokeStyle = '#7dd3fc'
  ctx.fillStyle   = '#7dd3fc'
  ctx.lineWidth   = 1.5
  ctx.globalAlpha = 0.75
  // Arrow body
  ctx.beginPath()
  ctx.moveTo(-9, 0); ctx.lineTo(6, 0)
  ctx.stroke()
  // Arrowhead
  ctx.beginPath()
  ctx.moveTo(6, 0); ctx.lineTo(1, -3.5); ctx.lineTo(1, 3.5)
  ctx.closePath(); ctx.fill()
  return cv
}

function createWaypointCanvas(id, isAirport) {
  const sz  = isAirport ? 40 : 28
  const cv  = document.createElement('canvas')
  cv.width  = sz; cv.height = sz
  const ctx = cv.getContext('2d')
  const cx  = sz / 2, cy = sz / 2, r = sz / 2 - 3

  if (isAirport) {
    // Airport: runway symbol
    ctx.fillStyle   = '#022c22'
    ctx.shadowColor = '#4ade80'
    ctx.shadowBlur  = 8
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#4ade80'
    ctx.lineWidth   = 1.5
    ctx.stroke()
    // Runway cross
    ctx.strokeStyle = '#4ade80'
    ctx.lineWidth   = 2
    ctx.beginPath()
    ctx.moveTo(cx, cy - r + 4); ctx.lineTo(cx, cy + r - 4)
    ctx.moveTo(cx - r + 4, cy); ctx.lineTo(cx + r - 4, cy)
    ctx.stroke()
  } else {
    // Waypoint: diamond
    ctx.fillStyle   = '#1c1917'
    ctx.strokeStyle = '#fbbf24'
    ctx.shadowColor = '#fbbf24'
    ctx.shadowBlur  = 6
    ctx.lineWidth   = 1.5
    ctx.beginPath()
    ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy)
    ctx.lineTo(cx, cy + r); ctx.lineTo(cx - r, cy)
    ctx.closePath()
    ctx.fill(); ctx.stroke()
    // Centre dot
    ctx.fillStyle = '#fbbf24'
    ctx.beginPath()
    ctx.arc(cx, cy, 2.5, 0, Math.PI * 2)
    ctx.fill()
  }
  return cv
}

function createPressureCanvas(type, color) {
  const cv  = document.createElement('canvas')
  cv.width  = 44; cv.height = 44
  const ctx = cv.getContext('2d')

  // Spiral ring background
  ctx.fillStyle   = color === '#ef4444' ? 'rgba(127,29,29,0.6)' : 'rgba(5,46,22,0.6)'
  ctx.shadowColor = color
  ctx.shadowBlur  = 10
  ctx.beginPath()
  ctx.arc(22, 22, 18, 0, Math.PI * 2)
  ctx.fill()

  ctx.strokeStyle = color
  ctx.lineWidth   = 1.5
  ctx.globalAlpha = 0.6
  ctx.beginPath()
  ctx.arc(22, 22, 18, 0, Math.PI * 2)
  ctx.stroke()

  // Inner ring
  ctx.beginPath()
  ctx.arc(22, 22, 11, 0, Math.PI * 2)
  ctx.stroke()
  ctx.globalAlpha = 1

  // L / H letter
  ctx.fillStyle   = color
  ctx.shadowColor = color
  ctx.shadowBlur  = 6
  ctx.font        = 'bold 18px Inter, sans-serif'
  ctx.textAlign   = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(type, 22, 23)

  return cv
}

// ── Camera presets ────────────────────────────────────────────────
function setCameraAngle(mode) {
  if (!viewer || !C) return
  if (mode === 'cockpit' && props.flightState) {
    const s = props.flightState
    const pos = C.Cartesian3.fromDegrees(s.lon, s.lat, s.alt_ft * 0.3048)
    followAircraft.value = true
    viewer.camera.lookAt(pos, new C.HeadingPitchRange(
      C.Math.toRadians(s.heading || 56),
      C.Math.toRadians(-8),
      120_000
    ))
  } else {
    followAircraft.value = false
    viewer.camera.flyTo({
      destination: C.Cartesian3.fromDegrees(-35, 47, 9_000_000),
      duration: 1.8,
    })
  }
}

function toggleMode() {
  if (!viewer || !C) return
  mode2D.value = !mode2D.value
  if (mode2D.value) viewer.scene.morphTo2D(1.0)
  else              viewer.scene.morphTo3D(1.0)
}

// ── Helpers ───────────────────────────────────────────────────────
function phaseBadge(phase) {
  return {
    ground:  'bg-slate-800 text-slate-300 border border-slate-700',
    climb:   'bg-blue-950  text-blue-300  border border-blue-800',
    cruise:  'bg-emerald-950 text-emerald-300 border border-emerald-800',
    descent: 'bg-amber-950 text-amber-300 border border-amber-800',
    arrival: 'bg-purple-950 text-purple-300 border border-purple-800',
  }[phase] || 'bg-slate-800 text-slate-300'
}

function anomalyLabel(a) {
  return {
    turbulence:     'Clear Air Turbulence Detected',
    isa_deviation:  'ISA Temperature Anomaly (+14°C)',
    jet_stream_loss:'Jet Stream Displaced South',
    mach_divergence:'Approaching Mach Divergence',
  }[a] || a
}

onMounted(async () => {
  await nextTick()
  await initCesium()
})

onUnmounted(() => {
  try { viewer?.destroy() } catch {}
})

const FALLBACK_WAYPOINTS = [
  { id: 'JFK', name: 'New York JFK', lat:  40.64, lon: -73.78 },
  { id: 'TUNIT', name: 'TUNIT',      lat:  43.5,  lon: -55.0  },
  { id: 'SOMAX', name: 'SOMAX',      lat:  48.5,  lon: -30.0  },
  { id: 'DOLIR', name: 'DOLIR',      lat:  51.3,  lon:  -8.0  },
  { id: 'LHR',  name: 'London LHR',  lat:  51.47, lon:  -0.45 },
]
</script>

<style scoped>
:deep(.cesium-widget-credits)          { display: none !important; }
:deep(.cesium-viewer-toolbar)          { display: none !important; }
:deep(.cesium-viewer-animationContainer){ display: none !important; }
:deep(.cesium-viewer-timelineContainer){ display: none !important; }
:deep(.cesium-viewer-bottom)           { display: none !important; }
:deep(.cesium-viewer-fullscreenContainer){ display: none !important; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
