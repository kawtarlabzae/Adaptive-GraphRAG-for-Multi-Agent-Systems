<template>
  <div class="h-screen flex flex-col bg-slate-50 overflow-hidden">
    <!-- Top bar -->
    <header class="border-b border-slate-200 bg-white flex-shrink-0 z-40 h-14">
      <div class="h-full px-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button @click="$router.push('/')" class="text-slate-400 hover:text-slate-700 transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
          </button>
          <div class="w-px h-5 bg-slate-200" />
          <div class="w-7 h-7 bg-gradient-to-br from-brand-500 to-cyan-500 rounded-lg flex items-center justify-center text-white text-sm">⬡</div>
          <div>
            <h1 class="font-semibold text-slate-900 text-sm leading-none">{{ session?.config?.name || 'Session' }}</h1>
            <p class="text-xs text-slate-400 leading-none mt-0.5 mono">{{ sessionId.slice(0, 8) }}</p>
          </div>
          <span :class="['badge ml-2', statusBadgeClass]">{{ store.sessionStatus }}</span>
        </div>

        <div class="flex items-center gap-3">
          <!-- Phase indicators -->
          <div class="hidden md:flex items-center gap-2">
            <PhaseChip :phase="1" :status="store.phaseStatus.phase1" label="Study Room" />
            <PhaseChip :phase="2" :status="store.phaseStatus.phase2" label="Eng. Lab" />
          </div>
          <!-- Timer -->
          <div v-if="store.isRunning" class="mono text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-lg">
            {{ elapsed }}
          </div>
          <!-- Action buttons -->
          <button v-if="session?.status === 'created'" @click="startSession" class="btn-primary">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            Start Session
          </button>
          <button v-if="store.isRunning" @click="stopSession" class="btn-danger">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
            Stop
          </button>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p class="text-slate-500">Loading session…</p>
      </div>
    </div>

    <!-- Main dashboard -->
    <div v-else-if="session" class="flex-1 min-h-0 flex overflow-hidden">
      <!-- Left: Agent cards -->
      <aside class="w-72 border-r border-slate-200 bg-white overflow-y-auto flex-shrink-0 p-3 space-y-2">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1 pb-1">Agents</p>
        <AgentCard v-for="agent in store.agentCards" :key="agent.name" :agent="agent" />

        <!-- KPI metrics (shown after completion) -->
        <div v-if="store.isCompleted || store.metrics.total_nodes > 0" class="mt-4">
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1 pb-2">KPI Metrics</p>
          <div class="space-y-2">
            <MetricRow label="Logical Chain Accuracy" :value="store.metrics.logical_chain_accuracy" format="pct" color="indigo" />
            <MetricRow label="Context Efficiency" :value="store.metrics.context_efficiency" format="pct" color="emerald" />
            <MetricRow label="Hallucination Rate" :value="store.metrics.hallucination_rate" format="pct" color="red" invert />
          </div>
          <div class="grid grid-cols-2 gap-2 mt-3">
            <StatTile label="Nodes" :value="store.metrics.total_nodes" icon="⬡" />
            <StatTile label="Edges" :value="store.metrics.total_edges" icon="→" />
            <StatTile label="Conflicts" :value="store.metrics.conflicts_detected" icon="⚔️" />
            <StatTile label="Pruned" :value="store.metrics.pruned_nodes" icon="✂️" />
          </div>
        </div>

        <!-- Uploaded files -->
        <div v-if="session.files?.length" class="mt-4">
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1 pb-2">Documents</p>
          <div v-for="f in session.files" :key="f"
               class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-slate-50 text-xs text-slate-600">
            <span>📄</span> {{ f }}
          </div>
        </div>
      </aside>

      <!-- Center: Graph -->
      <main class="flex-1 overflow-hidden relative">
        <GraphView :nodes="store.graph.nodes" :edges="store.graph.edges" />
      </main>

      <!-- Right: Omniverse + Activity log -->
      <aside class="w-96 border-l border-slate-200 bg-white flex flex-col flex-shrink-0 overflow-hidden">
        <!-- Omniverse panel: fixed ratio via flex-[0_0_55%] -->
        <div class="flex-[0_0_55%] min-h-0 border-b border-slate-200 overflow-hidden">
          <OmniverseView />
        </div>
        <!-- Activity log: takes remaining space, scrolls internally -->
        <div class="flex-1 min-h-0 overflow-hidden flex flex-col">
          <ActivityLog :events="store.events" />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/sessionStore'
import AgentCard from '@/components/AgentCard.vue'
import GraphView from '@/components/GraphView.vue'
import OmniverseView from '@/components/OmniverseView.vue'
import ActivityLog from '@/components/ActivityLog.vue'

const PhaseChip = {
  props: ['phase', 'status', 'label'],
  template: `
    <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium"
         :class="{
           'bg-slate-100 text-slate-500': status === 'pending',
           'bg-brand-50 text-brand-700': status === 'running',
           'bg-emerald-50 text-emerald-700': status === 'completed',
         }">
      <span class="w-1.5 h-1.5 rounded-full" :class="{
        'bg-slate-400': status === 'pending',
        'bg-brand-500 animate-pulse': status === 'running',
        'bg-emerald-500': status === 'completed',
      }"></span>
      Phase {{ phase }} · {{ label }}
    </div>
  `
}

const MetricRow = {
  props: ['label', 'value', 'format', 'color', 'invert'],
  template: `
    <div>
      <div class="flex justify-between text-xs mb-1">
        <span class="text-slate-500">{{ label }}</span>
        <span class="font-semibold" :class="valueColor">{{ displayValue }}</span>
      </div>
      <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all duration-500"
             :class="barColor" :style="{ width: barWidth }"></div>
      </div>
    </div>
  `,
  computed: {
    displayValue() { return this.format === 'pct' ? `${(this.value * 100).toFixed(1)}%` : this.value },
    barWidth() { return `${Math.min(this.value * 100, 100)}%` },
    barColor() {
      if (this.invert) return this.value < 0.05 ? 'bg-emerald-400' : this.value < 0.15 ? 'bg-amber-400' : 'bg-red-400'
      const c = this.color
      return c === 'indigo' ? 'bg-brand-500' : c === 'emerald' ? 'bg-emerald-500' : 'bg-red-400'
    },
    valueColor() { return this.invert ? (this.value < 0.05 ? 'text-emerald-600' : 'text-red-600') : `text-slate-700` }
  }
}

const StatTile = {
  props: ['label', 'value', 'icon'],
  template: `
    <div class="bg-slate-50 rounded-xl p-3 text-center">
      <div class="text-lg">{{ icon }}</div>
      <div class="text-lg font-bold text-slate-900">{{ value }}</div>
      <div class="text-xs text-slate-400">{{ label }}</div>
    </div>
  `
}

const route = useRoute()
const router = useRouter()
const store = useSessionStore()
const sessionId = route.params.id
const session = computed(() => store.current)
const loading = ref(true)

const statusBadgeClass = computed(() => ({
  created: 'badge-neutral', running: 'badge-info',
  completed: 'badge-success', stopped: 'badge-warning', error: 'badge-danger'
})[store.sessionStatus] || 'badge-neutral')

// Elapsed timer
const elapsed = ref('0:00')
let _startTime = null
let _timerInterval = null

function startTimer() {
  _startTime = Date.now()
  _timerInterval = setInterval(() => {
    const sec = Math.floor((Date.now() - _startTime) / 1000)
    const m = Math.floor(sec / 60)
    const s = sec % 60
    elapsed.value = `${m}:${s.toString().padStart(2, '0')}`
  }, 1000)
}

function stopTimer() {
  clearInterval(_timerInterval)
}

onMounted(async () => {
  store.reset()
  try {
    await store.loadSession(sessionId)
    if (store.current?.status === 'running') {
      store.connectWs(sessionId)
      startTimer()
    }
  } catch {
    router.push('/')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  store.disconnectWs()
  stopTimer()
})

async function startSession() {
  await store.startSession(sessionId)
  startTimer()
}

async function stopSession() {
  await store.stopSession(sessionId)
  stopTimer()
}
</script>
