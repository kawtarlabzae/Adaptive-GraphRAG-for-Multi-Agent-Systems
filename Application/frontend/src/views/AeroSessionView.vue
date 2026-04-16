<template>
  <div class="h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden">

    <!-- ─── Top bar ──────────────────────────────────────────────────────── -->
    <header class="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 flex-shrink-0 z-30">
      <div class="flex items-center gap-3">
        <button @click="$router.push('/')"
                class="text-slate-500 hover:text-slate-200 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
        </button>
        <div class="w-px h-4 bg-slate-700"/>
        <span class="text-white font-semibold text-sm">✈️ {{ session?.config?.name || 'Aero Digital Twin' }}</span>
        <span class="text-slate-500 text-xs font-mono">JFK → LHR</span>
        <span :class="['text-xs px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider', statusClass]">
          {{ store.sessionStatus }}
        </span>
      </div>

      <div class="flex items-center gap-3">
        <!-- Phase chips -->
        <div class="hidden md:flex items-center gap-2">
          <PhaseChip :active="store.phaseStatus.phase1 === 'running'"
                     :done="store.phaseStatus.phase1 === 'completed'"
                     label="Knowledge Build" />
          <PhaseChip :active="store.phaseStatus.phase2 === 'running'"
                     :done="store.phaseStatus.phase2 === 'completed'"
                     label="Flight Ops" />
        </div>
        <!-- Elapsed -->
        <div v-if="store.isRunning" class="text-slate-400 font-mono text-sm bg-slate-800 px-3 py-1 rounded-lg">
          {{ elapsed }}
        </div>
        <!-- Comms badge -->
        <div v-if="store.agentMessages.length"
             class="flex items-center gap-1.5 bg-violet-900/40 border border-violet-700/60 px-2.5 py-1 rounded-lg">
          <span class="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse"/>
          <span class="text-violet-300 text-xs font-mono">{{ store.agentMessages.length }} msgs</span>
        </div>
        <!-- Controls -->
        <button v-if="session?.status === 'created'" @click="startSession"
                class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition-colors flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          Launch
        </button>
        <button v-if="store.isRunning" @click="stopSession"
                class="bg-red-700 hover:bg-red-600 text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition-colors">
          Abort
        </button>
      </div>
    </header>

    <!-- ─── Loading ────────────────────────────────────────────────────── -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"/>
        <p class="text-slate-400 text-sm">Loading session…</p>
      </div>
    </div>

    <!-- ─── Main layout ───────────────────────────────────────────────── -->
    <div v-else-if="session" class="flex-1 min-h-0 flex overflow-hidden">

      <!-- ════════════════════════════════════════════════════════════════
           LEFT PANEL: agents + KPIs + pilot commands
           ═══════════════════════════════════════════════════════════════ -->
      <aside class="w-56 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden flex-shrink-0">
        <!-- Agents -->
        <div class="p-2 border-b border-slate-800 flex-shrink-0">
          <p class="text-slate-500 text-[10px] uppercase tracking-widest font-bold px-1 pb-1.5">Agents</p>
          <div class="space-y-1.5">
            <div v-for="agent in store.agentCards" :key="agent.name"
                 class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span class="text-sm flex-shrink-0">{{ agent.icon || agentIcon(agent.name) }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-[11px] font-semibold text-slate-200 truncate leading-none">{{ agent.display_name || agent.name }}</p>
                <p v-if="agent.focus" class="text-[10px] text-violet-300 truncate leading-none mt-0.5 italic">
                  {{ agent.focus }}
                </p>
                <p v-else class="text-[10px] text-slate-500 truncate leading-none mt-0.5">
                  {{ agent.task || agent.status }}
                </p>
              </div>
              <span class="w-2 h-2 rounded-full flex-shrink-0" :class="statusDot(agent.status)"/>
            </div>
          </div>
        </div>

        <!-- Flight KPIs -->
        <div class="p-2 border-b border-slate-800 flex-shrink-0">
          <p class="text-slate-500 text-[10px] uppercase tracking-widest font-bold px-1 pb-1.5">Flight KPIs</p>
          <div class="space-y-1">
            <div v-for="kpi in kpiRows" :key="kpi.label" class="flex items-center justify-between px-1">
              <span class="text-slate-500 text-[11px]">{{ kpi.label }}</span>
              <span class="font-mono text-[11px] font-bold" :class="kpi.color">{{ kpi.value }}</span>
            </div>
          </div>
        </div>

        <!-- Graph stats -->
        <div class="p-2 border-b border-slate-800 flex-shrink-0">
          <p class="text-slate-500 text-[10px] uppercase tracking-widest font-bold px-1 pb-1.5">Knowledge Graph</p>
          <div class="grid grid-cols-2 gap-1.5">
            <div v-for="s in graphStats" :key="s.label"
                 class="bg-slate-800/50 border border-slate-700/40 rounded-lg p-1.5 text-center">
              <div class="text-sm font-bold text-slate-200 font-mono">{{ s.value }}</div>
              <div class="text-[10px] text-slate-500">{{ s.label }}</div>
            </div>
          </div>
        </div>

        <!-- Pilot command log -->
        <div class="flex-1 min-h-0 overflow-y-auto p-2">
          <p class="text-slate-500 text-[10px] uppercase tracking-widest font-bold px-1 pb-1.5">Pilot Commands</p>
          <div v-if="!store.pilotCommands.length" class="text-slate-600 text-[11px] px-1">Awaiting commands…</div>
          <div v-for="(cmd, i) in store.pilotCommands.slice(0,15)" :key="i"
               class="text-[11px] mb-1 border border-slate-800 rounded-lg p-1.5 bg-slate-800/40">
            <span class="text-blue-400 font-mono font-semibold">{{ cmd.action || 'adjust' }}</span>
            <span v-if="cmd.target_mach" class="text-slate-400 ml-1">M{{ Number(cmd.target_mach).toFixed(3) }}</span>
            <span v-if="cmd.target_alt_ft" class="text-slate-400 ml-1">FL{{ Math.round((Number(cmd.target_alt_ft)||0)/100) }}</span>
            <p v-if="cmd.reasoning" class="text-slate-600 mt-0.5 leading-snug truncate">{{ cmd.reasoning }}</p>
          </div>
        </div>
      </aside>

      <!-- ════════════════════════════════════════════════════════════════
           CENTER: CesiumJS globe + instruments
           ═══════════════════════════════════════════════════════════════ -->
      <main class="flex-1 flex flex-col overflow-hidden min-w-0">
        <div class="flex-1 min-h-0 overflow-hidden relative">
          <CesiumView
            :flight-state="store.flightState"
            :trajectory="store.trajectory"
            :waypoints="store.waypoints"
          />
          <!-- Overlay: current waypoint + anomaly alert -->
          <div class="absolute top-3 left-3 right-3 flex items-start justify-between pointer-events-none">
            <div v-if="store.flightState" class="bg-slate-900/80 backdrop-blur-sm border border-slate-700/60
                       rounded-xl px-3 py-2 text-[11px] font-mono space-y-0.5">
              <div class="text-slate-400">
                <span class="text-slate-300 font-semibold">{{ store.flightState.current_waypoint?.name || 'En Route' }}</span>
                <span class="ml-2">FL{{ Math.round((store.flightState.alt_ft || 35000)/100) }}</span>
                <span class="ml-2">M{{ Number(store.flightState.mach || 0.785).toFixed(3) }}</span>
              </div>
              <div class="text-slate-500">
                Fuel {{ Math.round(store.flightState.fuel_kg || 0) }}kg ·
                {{ store.flightState.phase || 'cruise' }}
              </div>
            </div>
            <div v-if="latestAlert" class="bg-red-950/90 border border-red-800/60 backdrop-blur-sm
                       rounded-xl px-3 py-2 text-[11px] text-red-300 max-w-xs">
              <p class="font-semibold text-red-200 mb-0.5">⚠️ Alert</p>
              <p>{{ latestAlert }}</p>
            </div>
          </div>
        </div>
        <!-- Instruments strip -->
        <div class="flex-shrink-0 bg-slate-900 border-t border-slate-800" style="height:136px">
          <FlightInstruments :flight-state="store.flightState" />
        </div>
      </main>

      <!-- ════════════════════════════════════════════════════════════════
           RIGHT PANEL: tabbed — Comms | Chat | Graph | Pressure | Log
           ═══════════════════════════════════════════════════════════════ -->
      <aside class="w-[380px] flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden">
        <!-- Tab bar -->
        <div class="flex border-b border-slate-800 flex-shrink-0 overflow-x-auto">
          <button v-for="tab in TABS" :key="tab.id" @click="activeTab = tab.id"
                  :class="['flex-shrink-0 px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider transition-colors whitespace-nowrap',
                           activeTab === tab.id
                             ? 'text-blue-400 border-b-2 border-blue-400 -mb-px bg-slate-800/50'
                             : 'text-slate-500 hover:text-slate-300']">
            {{ tab.label }}
            <span v-if="tab.id === 'comms' && store.agentMessages.length"
                  class="ml-1 text-violet-400">{{ store.agentMessages.length }}</span>
          </button>
        </div>

        <!-- Comms tab -->
        <div v-show="activeTab === 'comms'" class="flex-1 min-h-0 overflow-hidden">
          <CommsFeed />
        </div>

        <!-- Chat with Pilot tab -->
        <div v-show="activeTab === 'chat'" class="flex-1 min-h-0 flex flex-col overflow-hidden">
          <AeroChatPanel :session-id="sessionId" />
        </div>

        <!-- Knowledge Graph tab -->
        <div v-show="activeTab === 'graph'" class="flex-1 min-h-0 overflow-hidden">
          <GraphView :nodes="store.graph.nodes" :edges="store.graph.edges" />
        </div>

        <!-- Pressure Loop tab -->
        <div v-show="activeTab === 'pressure'" class="flex-1 min-h-0 overflow-hidden flex flex-col">
          <PressureLoopPanel
            :fuel-history="store.fuelHistory"
            :pressure-events="store.pressureEvents"
            class="flex-1"
          />
        </div>

        <!-- Activity Log tab -->
        <div v-show="activeTab === 'log'" class="flex-1 min-h-0 overflow-hidden">
          <ActivityLog :events="store.events" />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, defineComponent, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/sessionStore'
import CesiumView        from '@/components/CesiumView.vue'
import FlightInstruments from '@/components/FlightInstruments.vue'
import PressureLoopPanel from '@/components/PressureLoopPanel.vue'
import GraphView         from '@/components/GraphView.vue'
import ActivityLog       from '@/components/ActivityLog.vue'
import CommsFeed         from '@/components/CommsFeed.vue'

// ─── AeroChatPanel ────────────────────────────────────────────────────────────
const AeroChatPanel = defineComponent({
  props: { sessionId: String },
  setup(props) {
    const store   = useSessionStore()
    const input   = ref('')
    const sending = ref(false)
    const chatEl  = ref(null)

    const messages = computed(() => store.aeroChatMessages)

    watch(messages, async () => {
      await nextTick()
      if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
    })

    async function send() {
      const msg = input.value.trim()
      if (!msg || sending.value) return
      sending.value = true
      input.value = ''
      await store.sendAeroChat(props.sessionId, msg)
      sending.value = false
    }

    function onKey(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
    }

    return { messages, input, sending, chatEl, send, onKey }
  },
  template: `
    <div class="h-full flex flex-col bg-slate-900">
      <!-- Header -->
      <div class="flex-shrink-0 px-3 py-2 border-b border-slate-800 flex items-center gap-2">
        <span class="text-lg">✈️</span>
        <div>
          <p class="text-xs font-semibold text-slate-200">Pilot Agent</p>
          <p class="text-[10px] text-slate-500">Boeing 737-800 · JFK→LHR</p>
        </div>
        <div class="ml-auto flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"/>
          <span class="text-[10px] text-emerald-400">Online</span>
        </div>
      </div>

      <!-- Messages -->
      <div ref="chatEl" class="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        <!-- Welcome -->
        <div v-if="!messages.length" class="text-center py-6">
          <p class="text-3xl mb-2">✈️</p>
          <p class="text-sm font-semibold text-slate-300">AI Pilot Agent</p>
          <p class="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Ask me anything about the flight — fuel burn, turbulence, routing decisions, or current status.
          </p>
        </div>

        <div v-for="(msg, i) in messages" :key="i">
          <!-- User bubble -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-3 py-2 text-xs">
              {{ msg.content }}
            </div>
          </div>
          <!-- Pilot bubble -->
          <div v-else class="flex gap-2">
            <div class="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm flex-shrink-0">
              ✈️
            </div>
            <div class="flex-1 min-w-0">
              <div v-if="msg.error" class="bg-red-950/60 border border-red-900/60 rounded-xl px-3 py-2 text-xs text-red-300">
                {{ msg.error }}
              </div>
              <div v-else-if="msg.content === '' && !msg.error" class="flex items-center gap-1 py-2">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:0ms"/>
                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:100ms"/>
                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:200ms"/>
              </div>
              <div v-else class="bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm px-3 py-2 text-xs text-slate-200 space-y-2">
                <p class="leading-relaxed">{{ msg.content }}</p>
                <!-- Confidence bar -->
                <div v-if="msg.confidence != null" class="flex items-center gap-2">
                  <div class="flex-1 bg-slate-700 rounded-full h-1">
                    <div class="h-1 rounded-full bg-blue-400 transition-all" :style="{ width: (msg.confidence * 100) + '%' }"/>
                  </div>
                  <span class="text-[10px] text-slate-500 font-mono">{{ (msg.confidence * 100).toFixed(0) }}%</span>
                </div>
                <!-- Reasoning chain -->
                <details v-if="msg.reasoning_chain?.length" class="text-[10px]">
                  <summary class="text-slate-500 cursor-pointer hover:text-slate-400 select-none">
                    Reasoning chain ({{ msg.reasoning_chain.length }} steps)
                  </summary>
                  <ol class="mt-1.5 pl-3 space-y-1 list-decimal list-inside text-slate-400">
                    <li v-for="(step, si) in msg.reasoning_chain" :key="si">{{ step }}</li>
                  </ol>
                </details>
                <!-- Nodes used -->
                <div v-if="msg.nodes_used?.length" class="flex flex-wrap gap-1">
                  <span v-for="node in msg.nodes_used.slice(0,5)" :key="node.id || node"
                        class="px-1.5 py-0.5 bg-slate-700/80 border border-slate-600 rounded text-[10px] text-slate-300 font-mono">
                    {{ node.label || node.id || node }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="flex-shrink-0 p-3 border-t border-slate-800">
        <div class="flex gap-2 items-end">
          <textarea
            v-model="input"
            @keydown="onKey"
            rows="2"
            :disabled="sending"
            placeholder="Ask the Pilot Agent…"
            class="flex-1 resize-none bg-slate-800 border border-slate-700 rounded-xl px-3 py-2
                   text-xs text-slate-100 placeholder-slate-600 focus:outline-none
                   focus:border-blue-500 disabled:opacity-50 transition-colors"
          />
          <button @click="send" :disabled="sending || !input.trim()"
                  class="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white
                         rounded-xl px-3 py-2 text-xs font-semibold transition-colors flex-shrink-0">
            Send
          </button>
        </div>
      </div>
    </div>
  `,
})

// ─── PhaseChip ────────────────────────────────────────────────────────────────
const PhaseChip = defineComponent({
  props: ['active', 'done', 'label'],
  template: `
    <div class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium"
         :class="done ? 'bg-emerald-900/50 text-emerald-400' : active ? 'bg-blue-900/50 text-blue-300' : 'bg-slate-800 text-slate-500'">
      <span class="w-1.5 h-1.5 rounded-full"
            :class="done ? 'bg-emerald-400' : active ? 'bg-blue-400 animate-pulse' : 'bg-slate-600'"/>
      {{ label }}
    </div>
  `,
})

// ─── Setup ───────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'comms',    label: 'Agent Comms' },
  { id: 'chat',     label: '✈️ Chat'      },
  { id: 'graph',    label: 'Graph'        },
  { id: 'pressure', label: 'Pressure'     },
  { id: 'log',      label: 'Log'          },
]

const route     = useRoute()
const router    = useRouter()
const store     = useSessionStore()
const sessionId = route.params.id
const session   = computed(() => store.current)
const loading   = ref(true)
const activeTab = ref('comms')

const statusClass = computed(() => ({
  created:   'bg-slate-700 text-slate-300',
  running:   'bg-blue-900 text-blue-300',
  completed: 'bg-emerald-900 text-emerald-300',
  stopped:   'bg-amber-900 text-amber-300',
  error:     'bg-red-900 text-red-300',
})[store.sessionStatus] || 'bg-slate-700 text-slate-300')

// Auto-switch to chat tab once phase 2 is ready
watch(() => store.phase2Ready, (val) => {
  if (val) activeTab.value = 'chat'
})

// Auto-switch to comms when first message arrives (if still on comms)
watch(() => store.agentMessages.length, (len) => {
  if (len === 1) activeTab.value = 'comms'
})

// Latest pressure alert for overlay
const latestAlert = computed(() => {
  const alerts = store.agentMessages.filter(m => m.msg_type === 'alert').slice(-1)
  return alerts[0]?.content?.slice(0, 120) || null
})

const kpiRows = computed(() => [
  { label: 'Fuel Efficiency', value: fmtKpi('fuel_efficiency', '%', 100), color: 'text-emerald-400' },
  { label: 'Know. Latency',   value: fmtKpi('knowledge_latency_ms', 'ms', 1), color: 'text-blue-400' },
  { label: 'Context Utility', value: fmtKpi('context_utility', '%', 100), color: 'text-violet-400' },
])

const graphStats = computed(() => [
  { label: 'Nodes',     value: store.metrics.total_nodes },
  { label: 'Edges',     value: store.metrics.total_edges },
  { label: 'Conflicts', value: store.metrics.conflicts_detected },
  { label: 'Pressure',  value: store.pressureEvents.length },
])

function fmtKpi(key, unit, mult) {
  const v = store.flightKpis[key]
  if (v == null) return '—'
  return (v * mult).toFixed(key === 'knowledge_latency_ms' ? 0 : 1) + ' ' + unit
}

// Elapsed timer
const elapsed = ref('0:00')
let _startTime = null
let _timerInterval = null

function startTimer() {
  _startTime = Date.now()
  _timerInterval = setInterval(() => {
    const sec = Math.floor((Date.now() - _startTime) / 1000)
    elapsed.value = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
  }, 1000)
}

onMounted(async () => {
  store.reset()
  try {
    await store.loadSession(sessionId)
    if (store.current?.status === 'running') {
      store.connectWs(sessionId)
      startTimer()
    } else if (store.current?.status === 'created') {
      // Auto-start aviation sessions
      await store.startSession(sessionId)
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
  clearInterval(_timerInterval)
})

async function startSession() {
  await store.startSession(sessionId)
  startTimer()
}

async function stopSession() {
  await store.stopSession(sessionId)
  clearInterval(_timerInterval)
}

function agentIcon(name) {
  return { pilot: '✈️', navigator: '🗺️', engineer: '🔧',
           conflict: '⚔️', synthesizer: '🔬', scenario: '🧪',
           pruning: '✂️', pathfinder: '🔍' }[name] || '🤖'
}

function statusDot(status) {
  return {
    active:    'bg-blue-400 animate-pulse',
    thinking:  'bg-amber-400 animate-pulse',
    completed: 'bg-emerald-400',
    error:     'bg-red-400',
    idle:      'bg-slate-600',
  }[status] || 'bg-slate-600'
}
</script>
