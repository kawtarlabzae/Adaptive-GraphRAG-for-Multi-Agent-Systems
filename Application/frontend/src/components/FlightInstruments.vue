<template>
  <div class="grid grid-cols-4 gap-2 p-2 select-none">
    <!-- Altimeter -->
    <GaugeDial
      label="ALTITUDE" unit="ft"
      :value="f.alt_ft" :min="0" :max="45000"
      :warn="38000" :danger="41000"
      :display="Math.round(f.alt_ft).toLocaleString()"
      color="#60a5fa"
    />
    <!-- Airspeed -->
    <GaugeDial
      label="AIRSPEED" unit="kts"
      :value="f.tas_kts" :min="0" :max="600"
      :warn="480" :danger="540"
      :display="Math.round(f.tas_kts).toString()"
      color="#34d399"
    />
    <!-- Mach -->
    <GaugeDial
      label="MACH" unit=""
      :value="f.mach" :min="0" :max="1.0"
      :warn="0.84" :danger="0.90"
      :display="f.mach.toFixed(3)"
      color="#f59e0b"
    />
    <!-- Heading compass -->
    <CompassDial :heading="f.heading" />
    <!-- Vertical speed -->
    <GaugeDial
      label="V/S" unit="fpm"
      :value="f.vs_fpm + 3000" :min="0" :max="6000"
      :warn="5500" :danger="5900"
      :display="(f.vs_fpm >= 0 ? '+' : '') + Math.round(f.vs_fpm)"
      color="#a78bfa"
    />
    <!-- OAT -->
    <GaugeDial
      label="OAT" unit="°C"
      :value="f.oat_c + 70" :min="0" :max="120"
      :warn="100" :danger="115"
      :display="Math.round(f.oat_c).toString()"
      color="#67e8f9"
    />
    <!-- Fuel tank -->
    <FuelGauge :fuel_kg="f.fuel_kg" :max_fuel="19500" />
    <!-- N1 -->
    <GaugeDial
      label="N1" unit="%"
      :value="f.n1_pct" :min="0" :max="110"
      :warn="95" :danger="105"
      :display="f.n1_pct.toFixed(1)"
      color="#fb7185"
    />
  </div>
</template>

<script setup>
import { computed, defineComponent, h } from 'vue'

const props = defineProps({
  flightState: { type: Object, default: null }
})

const DEFAULTS = {
  alt_ft: 0, tas_kts: 0, mach: 0, heading: 0,
  vs_fpm: 0, oat_c: -56, fuel_kg: 19500, n1_pct: 82
}
const f = computed(() => ({ ...DEFAULTS, ...props.flightState }))

// ─── helpers ──────────────────────────────────────────────────────────────────
function arcPath(cx, cy, r, startDeg, endDeg) {
  const rad = d => (d * Math.PI) / 180
  const x1 = cx + r * Math.cos(rad(startDeg))
  const y1 = cy + r * Math.sin(rad(startDeg))
  const x2 = cx + r * Math.cos(rad(endDeg))
  const y2 = cy + r * Math.sin(rad(endDeg))
  const large = endDeg - startDeg > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
}

// ─── GaugeDial sub-component ──────────────────────────────────────────────────
const GaugeDial = defineComponent({
  props: {
    label: String, unit: String,
    value: { type: Number, default: 0 },
    min:   { type: Number, default: 0 },
    max:   { type: Number, default: 100 },
    warn:  { type: Number, default: null },
    danger:{ type: Number, default: null },
    display:{ type: String, default: '' },
    color: { type: String, default: '#60a5fa' },
  },
  setup(p) {
    const clampRatio = v => Math.min(1, Math.max(0, (v - p.min) / (p.max - p.min)))
    const bgArc     = arcPath(50, 50, 36, -135, 135)
    const valueArc  = computed(() => arcPath(50, 50, 36, -135, -135 + clampRatio(p.value) * 270))
    const warnArc   = computed(() => p.warn !== null
      ? arcPath(50, 50, 36, -135 + clampRatio(p.warn) * 270,
                -135 + clampRatio(p.danger ?? p.max) * 270) : null)
    const dangerArc = computed(() => p.danger !== null
      ? arcPath(50, 50, 36, -135 + clampRatio(p.danger) * 270, 135) : null)
    const needleAngle = computed(() => -135 + clampRatio(p.value) * 270)
    const arcColor = computed(() => {
      if (p.danger !== null && p.value >= p.danger) return '#f87171'
      if (p.warn  !== null && p.value >= p.warn)   return '#fbbf24'
      return p.color
    })
    return { bgArc, valueArc, warnArc, dangerArc, needleAngle, arcColor }
  },
  template: `
    <div class="bg-slate-900 border border-slate-700 rounded-xl p-1 flex flex-col items-center">
      <svg viewBox="0 0 100 100" class="w-full" style="max-height:92px">
        <path :d="bgArc"
              fill="none" stroke="#1e293b" stroke-width="6" stroke-linecap="round"/>
        <path v-if="warnArc" :d="warnArc"
              fill="none" stroke="#fbbf24" stroke-width="6" stroke-linecap="round" opacity="0.35"/>
        <path v-if="dangerArc" :d="dangerArc"
              fill="none" stroke="#f87171" stroke-width="6" stroke-linecap="round" opacity="0.35"/>
        <path :d="valueArc" fill="none" :stroke="arcColor"
              stroke-width="4" stroke-linecap="round"/>
        <line x1="50" y1="50" x2="50" y2="18"
              :transform="'rotate(' + needleAngle + ',50,50)'"
              stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="50" cy="50" r="3" fill="white"/>
        <text x="50" y="73" text-anchor="middle"
              font-size="11" font-family="monospace" font-weight="700"
              :fill="arcColor">{{ display }}</text>
        <text x="50" y="83" text-anchor="middle"
              font-size="7" font-family="sans-serif" fill="#64748b">{{ unit }}</text>
      </svg>
      <p class="text-slate-500 text-xs mt-0.5 tracking-widest uppercase">{{ label }}</p>
    </div>
  `,
  methods: { arcPath }
})

// ─── CompassDial ──────────────────────────────────────────────────────────────
const CompassDial = defineComponent({
  props: { heading: { type: Number, default: 0 } },
  setup(p) {
    const hdgStr  = computed(() => String(Math.round(p.heading)).padStart(3, '0'))
    const cardinal = computed(() => ['N','NE','E','SE','S','SW','W','NW'][Math.round(p.heading / 45) % 8])
    const ticks   = Array.from({ length: 36 }, (_, i) => i + 1)
    return { hdgStr, cardinal, ticks }
  },
  template: `
    <div class="bg-slate-900 border border-slate-700 rounded-xl p-1 flex flex-col items-center">
      <svg viewBox="0 0 100 100" class="w-full" style="max-height:92px">
        <circle cx="50" cy="50" r="40" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
        <g :transform="'rotate(' + (-heading) + ',50,50)'">
          <line v-for="i in ticks" :key="i"
            :x1="50 + 36*Math.cos((i*10-90)*Math.PI/180)"
            :y1="50 + 36*Math.sin((i*10-90)*Math.PI/180)"
            :x2="50 + (i%3===0?30:33)*Math.cos((i*10-90)*Math.PI/180)"
            :y2="50 + (i%3===0?30:33)*Math.sin((i*10-90)*Math.PI/180)"
            stroke="#475569" stroke-width="0.8"/>
          <text x="50" y="18" text-anchor="middle" font-size="9"
                font-weight="900" fill="#f87171" font-family="sans-serif">N</text>
          <text x="82" y="53" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="sans-serif">E</text>
          <text x="50" y="89" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="sans-serif">S</text>
          <text x="18" y="53" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="sans-serif">W</text>
        </g>
        <polygon points="50,12 47,20 53,20" fill="#60a5fa"/>
        <text x="50" y="73" text-anchor="middle"
              font-size="11" font-family="monospace" font-weight="700" fill="#60a5fa">
          {{ hdgStr }}°
        </text>
        <text x="50" y="83" text-anchor="middle"
              font-size="7" font-family="sans-serif" fill="#64748b">{{ cardinal }}</text>
      </svg>
      <p class="text-slate-500 text-xs mt-0.5 tracking-widest uppercase">HEADING</p>
    </div>
  `
})

// ─── FuelGauge ────────────────────────────────────────────────────────────────
const FuelGauge = defineComponent({
  props: {
    fuel_kg:  { type: Number, default: 0 },
    max_fuel: { type: Number, default: 19500 },
  },
  setup(p) {
    const pct     = computed(() => Math.min(1, Math.max(0, p.fuel_kg / p.max_fuel)))
    const barH    = computed(() => pct.value * 52)
    const barY    = computed(() => 66 - barH.value)
    const barColor= computed(() => pct.value < 0.15 ? '#f87171' : pct.value < 0.30 ? '#fbbf24' : '#34d399')
    const fuelStr = computed(() => Math.round(p.fuel_kg).toLocaleString())
    const pctStr  = computed(() => (pct.value * 100).toFixed(0) + '%')
    return { pct, barH, barY, barColor, fuelStr, pctStr }
  },
  template: `
    <div class="bg-slate-900 border border-slate-700 rounded-xl p-1 flex flex-col items-center">
      <svg viewBox="0 0 100 100" class="w-full" style="max-height:92px">
        <rect x="33" y="14" width="34" height="54" rx="4"
              fill="#0f172a" stroke="#1e293b" stroke-width="1.5"/>
        <rect :x="34" :y="barY" width="32" :height="barH" rx="3"
              :fill="barColor" opacity="0.9"/>
        <line x1="34" y1="27" x2="66" y2="27" stroke="#0f172a" stroke-width="0.8"/>
        <line x1="34" y1="40" x2="66" y2="40" stroke="#0f172a" stroke-width="0.8"/>
        <line x1="34" y1="53" x2="66" y2="53" stroke="#0f172a" stroke-width="0.8"/>
        <rect x="43" y="10" width="14" height="5" rx="2" fill="#334155"/>
        <text x="50" y="78" text-anchor="middle"
              font-size="8" font-family="monospace" font-weight="700"
              :fill="barColor">{{ fuelStr }}</text>
        <text x="50" y="87" text-anchor="middle"
              font-size="7" font-family="sans-serif" fill="#64748b">{{ pctStr }} · kg</text>
      </svg>
      <p class="text-slate-500 text-xs mt-0.5 tracking-widest uppercase">FUEL</p>
    </div>
  `
})
</script>
