<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 flex-shrink-0">
      <div class="flex items-center gap-2">
        <div class="w-5 h-5 bg-gradient-to-br from-green-400 to-emerald-600 rounded flex items-center justify-center text-white text-xs font-bold">⬡</div>
        <p class="text-xs font-semibold text-slate-700">NVIDIA Omniverse — Smart Vineyard</p>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="state" class="badge badge-success text-xs">LIVE</span>
        <span v-else class="badge badge-neutral text-xs">STANDBY</span>
        <span v-if="state" class="mono text-xs text-slate-400">{{ timeStr }}</span>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-hidden flex flex-col">
      <!-- No data state -->
      <div v-if="!state" class="flex-1 flex items-center justify-center text-center text-slate-300 p-6">
        <div>
          <div class="text-4xl mb-2">🌿</div>
          <p class="font-medium">Vineyard Digital Twin</p>
          <p class="text-sm mt-1">Simulation will appear when the session starts</p>
        </div>
      </div>

      <div v-else class="flex-1 overflow-y-auto">
        <!-- Vineyard SVG Grid -->
        <div class="px-3 pt-3">
          <div class="bg-gradient-to-b from-sky-50 to-slate-50 rounded-xl border border-slate-200 overflow-hidden">
            <svg :viewBox="`0 0 ${SVG_W} ${SVG_H}`" class="w-full" style="max-height: 160px">
              <!-- Background -->
              <rect width="100%" height="100%" fill="url(#sky-gradient)" />
              <defs>
                <linearGradient id="sky-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#e0f2fe"/>
                  <stop offset="100%" stop-color="#f0fdf4"/>
                </linearGradient>
              </defs>
              <!-- Soil strip at bottom -->
              <rect x="0" :y="SVG_H - 20" width="100%" height="20" fill="#92400e" opacity="0.3" rx="0"/>
              <!-- Zone labels -->
              <text v-for="z in 3" :key="z" :x="(z - 0.5) * SVG_W / 3" y="12"
                    text-anchor="middle" fill="#64748b" font-size="9" font-family="Inter, sans-serif">
                Zone {{ z }} — {{ zoneLabel(z) }}
              </text>
              <!-- Zone dividers -->
              <line v-for="z in [1, 2]" :key="z"
                    :x1="z * SVG_W / 3" y1="0" :x2="z * SVG_W / 3" :y2="SVG_H"
                    stroke="#cbd5e1" stroke-width="1" stroke-dasharray="3,3"/>
              <!-- Vines -->
              <g v-for="vine in vinesData" :key="`${vine.zone}-${vine.row}-${vine.col}`">
                <!-- Irrigation glow -->
                <circle v-if="vine.irrigating"
                        :cx="vine.x" :cy="vine.y" :r="VINE_R + 3"
                        fill="#60a5fa" opacity="0.3" class="animate-pulse" />
                <!-- Vine circle -->
                <circle :cx="vine.x" :cy="vine.y" :r="VINE_R"
                        :fill="vineColor(vine)"
                        stroke="rgba(0,0,0,0.1)" stroke-width="0.5" />
                <!-- Stress indicator -->
                <circle v-if="vine.temp_stress > 0.6"
                        :cx="vine.x + VINE_R * 0.5" :cy="vine.y - VINE_R * 0.5" r="1.5"
                        fill="#ef4444" opacity="0.9"/>
              </g>
              <!-- Sun indicator -->
              <g v-if="isDaytime">
                <circle :cx="SVG_W - 25" cy="18" r="10" fill="#fbbf24" opacity="0.8"/>
                <g v-for="i in 8" :key="i" :transform="`rotate(${i * 45} ${SVG_W - 25} 18)`">
                  <line :x1="SVG_W - 25" y1="6" :x2="SVG_W - 25" y2="3" stroke="#fbbf24" stroke-width="1.5" opacity="0.6"/>
                </g>
              </g>
              <!-- Moon -->
              <text v-else :x="SVG_W - 20" y="22" font-size="16" text-anchor="middle">🌙</text>
              <!-- Wind indicator -->
              <text x="15" y="22" font-size="9" fill="#64748b" font-family="Inter, sans-serif">
                💨 {{ state.wind_speed?.toFixed(1) }} m/s
              </text>
            </svg>
          </div>
        </div>

        <!-- Zone metrics tabs -->
        <div class="px-3 pt-2">
          <div class="flex gap-1 mb-2">
            <button v-for="z in [1, 2, 3]" :key="z"
                    @click="activeZone = z"
                    :class="['flex-1 py-1 text-xs font-medium rounded-lg transition-colors',
                             activeZone === z ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200']">
              Zone {{ z }}
              <span v-if="activeZoneData(z)?.stress_level === 'high'" class="ml-1">⚠️</span>
            </button>
          </div>

          <!-- Zone data -->
          <div v-if="activeZoneData(activeZone)" class="grid grid-cols-2 gap-2">
            <SensorBar label="Temperature" :value="activeZoneData(activeZone).temperature"
                       :min="20" :max="45" unit="°C"
                       :color="tempColor(activeZoneData(activeZone).temperature)" />
            <SensorBar label="Soil Moisture" :value="activeZoneData(activeZone).soil_moisture"
                       :min="0" :max="100" unit="%"
                       :color="activeZoneData(activeZone).soil_moisture < 25 ? '#ef4444' : '#34d399'" />
            <SensorBar label="Humidity" :value="activeZoneData(activeZone).humidity"
                       :min="0" :max="100" unit="%" color="#60a5fa" />
            <SensorBar label="Anthocyanin" :value="activeZoneData(activeZone).anthocyanin_index"
                       :min="0" :max="100" unit="%" color="#a78bfa" />
            <SensorBar label="Brix (°Bx)" :value="activeZoneData(activeZone).brix"
                       :min="10" :max="35" unit="" color="#fbbf24" />
            <SensorBar label="UV Index" :value="activeZoneData(activeZone).uv_index"
                       :min="0" :max="12" unit="" color="#f97316" />
          </div>

          <!-- Irrigation status -->
          <div class="mt-2 flex gap-1">
            <div v-for="z in [1, 2, 3]" :key="z"
                 :class="['flex-1 text-center text-xs py-1 rounded-lg font-medium',
                          irrigationActive(z) ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-400']">
              {{ irrigationActive(z) ? '💧 Z' + z + ' ON' : 'Z' + z + ' OFF' }}
            </div>
          </div>
        </div>

        <!-- LLM Commands -->
        <div class="px-3 pt-3 pb-2">
          <p class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wider">LLM → Graph → Omniverse</p>
          <div class="space-y-1.5 max-h-24 overflow-y-auto">
            <div v-if="!store.omniverseCommands.length" class="text-xs text-slate-300 text-center py-2">
              No commands yet…
            </div>
            <div v-for="(cmd, i) in store.omniverseCommands.slice(0, 5)" :key="i"
                 class="bg-slate-900 text-emerald-400 rounded-lg p-2 mono text-xs">
              <span class="text-slate-500">{{ cmd.ts }}</span>
              <span class="text-amber-400 ml-2">{{ cmd.source || 'CMD' }}</span>
              <span class="text-white ml-2">{{ cmd.command }}</span>
              <span v-if="cmd.parameters?.zone" class="text-cyan-400 ml-2">{{ cmd.parameters.zone }}</span>
              <br v-if="cmd.parameters?.reason" />
              <span v-if="cmd.parameters?.reason" class="text-slate-400 pl-4 text-xs">
                {{ cmd.parameters.reason?.slice(0, 70) }}…
              </span>
            </div>
          </div>
        </div>

        <!-- USD Stage log -->
        <div v-if="store.omniverseLog.length" class="px-3 pb-3">
          <p class="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">USD Stage Updates</p>
          <div class="bg-slate-900 rounded-lg p-2 max-h-16 overflow-y-auto">
            <div v-for="(entry, i) in store.omniverseLog.slice(-5).reverse()" :key="i"
                 class="mono text-xs"
                 :class="{
                   'text-cyan-400': entry.type === 'usd',
                   'text-amber-400': entry.type === 'command',
                   'text-emerald-400': entry.type === 'success',
                   'text-slate-300': entry.type === 'info',
                 }">
              <span class="text-slate-600">{{ entry.ts }}</span> {{ entry.msg }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const store = useSessionStore()
const activeZone = ref(2)

const state = computed(() => store.omniverseState)

// SVG constants
const SVG_W = 380
const SVG_H = 140
const ZONES = 3
const ROWS = 5
const COLS = 16
const VINE_R = 4
const PADDING = 8

const isDaytime = computed(() => {
  const h = state.value?.day_hour ?? 12
  return h >= 6 && h <= 20
})

const timeStr = computed(() => {
  const h = state.value?.day_hour ?? 0
  const hours = Math.floor(h)
  const mins = Math.floor((h % 1) * 60)
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
})

// Generate vine grid positions
const vinesData = computed(() => {
  if (!state.value) return []
  const vs = state.value.vine_states || []
  const zoneW = (SVG_W - PADDING * 2) / ZONES
  const rowH = (SVG_H - 35) / ROWS

  return vs.map(v => ({
    ...v,
    x: PADDING + (v.zone - 1) * zoneW + (v.col / COLS) * zoneW * 0.9 + zoneW * 0.05,
    y: 30 + v.row * rowH + rowH * 0.4,
  }))
})

function vineColor(vine) {
  const stress = vine.temp_stress || 0
  const health = vine.health || 1
  if (vine.irrigating) return '#60a5fa'
  // Gradient: green (healthy) → yellow (moderate) → red (stressed)
  const r = Math.round(stress * 239 + (1 - stress) * 52)
  const g = Math.round((1 - stress * 0.8) * 211 + stress * 68)
  const b = Math.round((1 - stress) * 52 + stress * 68)
  const alpha = 0.6 + health * 0.4
  return `rgba(${r},${g},${b},${alpha})`
}

function tempColor(temp) {
  if (temp < 28) return '#34d399'
  if (temp < 33) return '#fbbf24'
  if (temp < 38) return '#fb923c'
  return '#ef4444'
}

function activeZoneData(z) {
  return state.value?.zones?.[String(z)]
}

function irrigationActive(z) {
  return state.value?.irrigation?.[String(z)]?.active
}

function zoneLabel(z) {
  return ['North', 'Central', 'South'][z - 1]
}

// SensorBar sub-component
const SensorBar = {
  props: ['label', 'value', 'min', 'max', 'unit', 'color'],
  template: `
    <div class="bg-slate-50 rounded-xl p-2.5">
      <div class="flex justify-between items-center mb-1">
        <span class="text-xs text-slate-500">{{ label }}</span>
        <span class="text-xs font-bold text-slate-800 mono">{{ value?.toFixed(1) }}{{ unit }}</span>
      </div>
      <div class="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all duration-700"
             :style="{ width: pct + '%', background: color }"></div>
      </div>
    </div>
  `,
  computed: {
    pct() { return Math.min(100, Math.max(0, ((this.value - this.min) / (this.max - this.min)) * 100)) }
  }
}
</script>
