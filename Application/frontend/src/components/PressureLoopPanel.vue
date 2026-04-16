<template>
  <div class="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden flex flex-col">
    <!-- Header -->
    <div class="px-4 py-2 border-b border-slate-700 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Pressure Loop Monitor</span>
        <span v-if="hasEvents"
              class="bg-amber-900/60 border border-amber-600 text-amber-300 text-xs px-2 py-0.5 rounded-full">
          {{ pressureEvents.length }} event{{ pressureEvents.length !== 1 ? 's' : '' }}
        </span>
      </div>
      <div class="flex items-center gap-3 text-xs text-slate-400">
        <span class="flex items-center gap-1">
          <span class="w-3 h-0.5 bg-blue-400 inline-block rounded"></span> F_predicted
        </span>
        <span class="flex items-center gap-1">
          <span class="w-3 h-0.5 bg-amber-400 inline-block rounded"></span> F_actual
        </span>
      </div>
    </div>

    <!-- SVG chart -->
    <div class="flex-1 p-2 min-h-0">
      <svg ref="chartSvg" class="w-full h-full" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none">
        <!-- Grid lines -->
        <g stroke="#1e293b" stroke-width="0.5">
          <line v-for="i in 5" :key="'h'+i"
            x1="42" :y1="plotY + plotH * (i-1)/4"
            :x2="42 + plotW" :y2="plotY + plotH * (i-1)/4"/>
          <line v-for="i in 7" :key="'v'+i"
            :x1="42 + plotW * (i-1)/6" :y1="plotY"
            :x2="42 + plotW * (i-1)/6" :y2="plotY + plotH"/>
        </g>

        <!-- Y-axis labels -->
        <text v-for="i in 5" :key="'yl'+i"
          x="38" :y="plotY + plotH * (i-1)/4 + 3"
          font-size="6" fill="#475569" text-anchor="end" font-family="monospace">
          {{ yLabel(i) }}
        </text>

        <!-- Threshold band (±4%) -->
        <rect v-if="hasData"
          x="42" :y="threshBandY" :width="plotW" :height="threshBandH"
          fill="#fbbf24" opacity="0.06"/>
        <line v-if="hasData"
          x1="42" :y1="threshLineY" :x2="42+plotW" :y2="threshLineY"
          stroke="#fbbf24" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>

        <!-- F_predicted line -->
        <polyline v-if="fpPoints"
          :points="fpPoints" fill="none"
          stroke="#60a5fa" stroke-width="1.5" stroke-linejoin="round"/>

        <!-- F_actual line -->
        <polyline v-if="faPoints"
          :points="faPoints" fill="none"
          stroke="#f59e0b" stroke-width="1.5" stroke-linejoin="round"/>

        <!-- F_actual fill under curve -->
        <polygon v-if="faFill"
          :points="faFill" :fill="'#f59e0b'" opacity="0.08"/>

        <!-- Pressure event markers -->
        <g v-for="(ev, i) in pressureEvents" :key="'pe'+i">
          <line
            :x1="tickX(ev.tick)" :y1="plotY"
            :x2="tickX(ev.tick)" :y2="plotY + plotH"
            stroke="#f87171" stroke-width="0.8" stroke-dasharray="2,2" opacity="0.7"/>
          <circle
            :cx="tickX(ev.tick)"
            :cy="faToPx(ev.f_actual)"
            r="3" fill="#f87171" opacity="0.9"/>
          <text
            :x="tickX(ev.tick) + 3" :y="plotY + 9"
            font-size="5.5" fill="#f87171" font-family="monospace">
            Δ{{ (ev.delta * 100).toFixed(1) }}%
          </text>
        </g>

        <!-- Axes -->
        <line x1="42" :y1="plotY" x2="42" :y2="plotY+plotH" stroke="#334155" stroke-width="1"/>
        <line x1="42" :y1="plotY+plotH" :x2="42+plotW" :y2="plotY+plotH" stroke="#334155" stroke-width="1"/>

        <!-- No data placeholder -->
        <text v-if="!hasData" :x="W/2" :y="H/2"
          text-anchor="middle" font-size="9" fill="#334155" font-family="sans-serif">
          Awaiting flight data…
        </text>
      </svg>
    </div>

    <!-- KPI strip -->
    <div class="border-t border-slate-700 px-3 py-2 grid grid-cols-4 gap-2 text-center">
      <div>
        <p class="text-xs text-slate-500">Avg Δ Fuel</p>
        <p class="text-sm font-mono font-bold text-blue-400">{{ avgDelta }}</p>
      </div>
      <div>
        <p class="text-xs text-slate-500">Max Δ Fuel</p>
        <p class="text-sm font-mono font-bold text-amber-400">{{ maxDelta }}</p>
      </div>
      <div>
        <p class="text-xs text-slate-500">Pressure Events</p>
        <p class="text-sm font-mono font-bold text-red-400">{{ pressureEvents.length }}</p>
      </div>
      <div>
        <p class="text-xs text-slate-500">Knowledge Latency</p>
        <p class="text-sm font-mono font-bold text-emerald-400">{{ avgLatency }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  fuelHistory:    { type: Array, default: () => [] }, // [{tick, f_predicted, f_actual}]
  pressureEvents: { type: Array, default: () => [] }, // [{tick, delta, f_predicted, f_actual, latency_ms}]
})

// Chart dimensions
const W = 320, H = 130
const plotX = 42, plotY = 8, plotW = W - 52, plotH = H - 30

const hasData   = computed(() => props.fuelHistory.length > 1)
const hasEvents = computed(() => props.pressureEvents.length > 0)

// Value ranges
const maxFuel = 19500
const minFuel = computed(() => {
  if (!hasData.value) return 0
  return Math.min(...props.fuelHistory.map(d => Math.min(d.f_predicted, d.f_actual))) * 0.97
})
const topFuel = computed(() => {
  if (!hasData.value) return maxFuel
  return Math.max(...props.fuelHistory.map(d => Math.max(d.f_predicted, d.f_actual))) * 1.01
})

function yToPx(kg) {
  const ratio = 1 - (kg - minFuel.value) / (topFuel.value - minFuel.value)
  return plotY + ratio * plotH
}
function faToPx(kg) { return yToPx(kg) }

const maxTick = computed(() => Math.max(35, ...(props.fuelHistory.map(d => d.tick) || [35])))
function tickX(t) {
  return plotX + (t / maxTick.value) * plotW
}

function pointsStr(key) {
  if (!hasData.value) return null
  return props.fuelHistory
    .map(d => `${tickX(d.tick).toFixed(1)},${yToPx(d[key]).toFixed(1)}`)
    .join(' ')
}

const fpPoints = computed(() => pointsStr('f_predicted'))
const faPoints = computed(() => pointsStr('f_actual'))
const faFill   = computed(() => {
  if (!hasData.value) return null
  const pts = props.fuelHistory
    .map(d => `${tickX(d.tick).toFixed(1)},${yToPx(d.f_actual).toFixed(1)}`)
    .join(' ')
  const last = props.fuelHistory.at(-1)
  const first = props.fuelHistory[0]
  return `${pts} ${tickX(last.tick).toFixed(1)},${plotY + plotH} ${tickX(first.tick).toFixed(1)},${plotY + plotH}`
})

// Threshold band around f_predicted (±4%)
const threshBandY = computed(() => {
  if (!hasData.value) return plotY
  const last = props.fuelHistory.at(-1)
  return yToPx(last.f_predicted * 1.04)
})
const threshBandH = computed(() => {
  if (!hasData.value) return 0
  const last = props.fuelHistory.at(-1)
  return Math.abs(yToPx(last.f_predicted * 0.96) - yToPx(last.f_predicted * 1.04))
})
const threshLineY = computed(() => {
  if (!hasData.value) return plotY
  const last = props.fuelHistory.at(-1)
  return yToPx(last.f_predicted)
})

function yLabel(i) {
  if (!hasData.value) return ''
  const val = topFuel.value - (i - 1) * (topFuel.value - minFuel.value) / 4
  return (val / 1000).toFixed(0) + 'k'
}

// KPIs
const avgDelta = computed(() => {
  if (!props.pressureEvents.length) return '—'
  const avg = props.pressureEvents.reduce((s, e) => s + Math.abs(e.delta), 0) / props.pressureEvents.length
  return (avg * 100).toFixed(2) + '%'
})
const maxDelta = computed(() => {
  if (!props.pressureEvents.length) return '—'
  return (Math.max(...props.pressureEvents.map(e => Math.abs(e.delta))) * 100).toFixed(2) + '%'
})
const avgLatency = computed(() => {
  const evs = props.pressureEvents.filter(e => e.latency_ms != null)
  if (!evs.length) return '—'
  const avg = evs.reduce((s, e) => s + e.latency_ms, 0) / evs.length
  return avg.toFixed(0) + ' ms'
})
</script>
