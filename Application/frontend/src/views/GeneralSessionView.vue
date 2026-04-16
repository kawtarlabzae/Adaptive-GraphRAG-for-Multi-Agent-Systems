<template>
  <div class="h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden">

    <!-- ── Header ───────────────────────────────────────────────────── -->
    <header class="flex-shrink-0 h-14 flex items-center gap-4 px-5 border-b border-slate-800 bg-slate-900">
      <button @click="router.push('/')"
              class="text-slate-400 hover:text-slate-100 transition-colors flex-shrink-0"
              title="Back to home">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
      </button>
      <div class="w-px h-5 bg-slate-700 flex-shrink-0" />
      <div class="w-7 h-7 bg-gradient-to-br from-violet-500 to-cyan-500 rounded-lg flex items-center justify-center text-sm select-none">⬡</div>
      <div class="flex-1 min-w-0">
        <p class="font-semibold text-sm text-slate-100 truncate">{{ sess?.config?.name || 'Custom Session' }}</p>
        <p class="text-xs text-slate-400">
          {{ store.agentCards.length }} agent(s) ·
          {{ store.graph.nodes.length }} nodes · {{ store.graph.edges.length }} edges
          <span v-if="store.agentMessages.length" class="ml-2 text-violet-400">
            · {{ store.agentMessages.length }} comms
          </span>
        </p>
      </div>

      <div class="hidden sm:flex items-center gap-2">
        <PhaseChip :active="!store.phase2Ready" :done="store.phase2Ready" label="Phase 1 — Build" />
        <svg class="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
        </svg>
        <PhaseChip :active="store.phase2Ready" :done="false" label="Phase 2 — Testing" />
      </div>

      <!-- Center panel toggle (phase 1 only) -->
      <div v-if="!store.phase2Ready" class="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
        <button
          v-for="view in CENTER_VIEWS" :key="view.id"
          @click="centerView = view.id"
          :class="[
            'px-2.5 py-1 rounded text-xs font-medium transition-colors',
            centerView === view.id ? 'bg-slate-600 text-white' : 'text-slate-400 hover:text-slate-200',
          ]"
          :title="view.label"
        >{{ view.icon }} {{ view.label }}</button>
      </div>

      <button @click="stopSession"
              class="px-3 py-1.5 rounded-lg text-xs border border-slate-700 text-slate-300
                     hover:bg-red-900/40 hover:border-red-700 hover:text-red-300 transition-colors">
        ■ Stop
      </button>
    </header>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- PHASE 1: 3-column — Agents | Center (Graph/Network) | Right   -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <div v-if="!store.phase2Ready" class="flex-1 min-h-0 flex">

      <!-- ── Col 1: Agents sidebar ──────────────────────────────────── -->
      <aside class="w-56 flex-shrink-0 flex flex-col border-r border-slate-800 bg-slate-900">
        <div class="px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
          <p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">Agents</p>
          <span class="text-[10px] text-slate-500">{{ completedCount }}/{{ store.agentCards.length }}</span>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto p-2 space-y-1.5">
          <button
            v-for="agent in store.agentCards" :key="agent.name"
            @click="selectedAgent = agent.name"
            :class="[
              'w-full text-left rounded-xl border p-2.5 transition-all',
              selectedAgent === agent.name
                ? 'border-violet-500/60 bg-violet-900/25'
                : 'border-slate-700/50 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800',
            ]"
          >
            <div class="flex items-center gap-2">
              <div :class="[
                'w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0',
                (agent.status === 'active' || agent.status === 'thinking') ? 'animate-bounce' : '',
              ]" :style="{ background: agentIconBg(agent.status) }">
                {{ agent.icon }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1">
                  <span class="text-[11px] font-semibold text-slate-100 truncate">{{ agent.display_name }}</span>
                  <span :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', statusDot(agent.status)]" />
                </div>
                <!-- Show emergent focus if assigned, else fallback to task/status -->
                <p v-if="agent.focus" class="text-[10px] text-violet-300 truncate italic">
                  {{ agent.focus }}
                </p>
                <p v-else class="text-[10px] text-slate-500 truncate">
                  {{ agent.task || agent.status }}
                </p>
                <div v-if="agent.status === 'active' || agent.status === 'thinking'"
                     class="mt-1 h-0.5 bg-slate-700 rounded-full overflow-hidden">
                  <div :class="['h-full rounded-full transition-all duration-500',
                               agent.status === 'thinking' ? 'bg-amber-400 animate-pulse' : 'bg-violet-500']"
                       :style="{ width: `${Math.max(5, (agent.progress || 0) * 100)}%` }" />
                </div>
              </div>
            </div>
            <div v-if="agentHasStats(agent)" class="mt-1.5 flex gap-2 pl-9">
              <span v-if="agent.stats?.nodes_added" class="text-[10px] text-violet-300">+{{ agent.stats.nodes_added }}N</span>
              <span v-if="agent.stats?.edges_added" class="text-[10px] text-cyan-300">+{{ agent.stats.edges_added }}E</span>
            </div>
          </button>
        </div>

        <!-- Bottom: stats + advance -->
        <div class="p-3 border-t border-slate-800 space-y-2">
          <div class="grid grid-cols-2 gap-1.5">
            <div class="bg-slate-800 rounded-lg py-1.5 text-center">
              <p class="text-base font-bold text-violet-400">{{ store.graph.nodes.length }}</p>
              <p class="text-[9px] text-slate-500">Nodes</p>
            </div>
            <div class="bg-slate-800 rounded-lg py-1.5 text-center">
              <p class="text-base font-bold text-cyan-400">{{ store.graph.edges.length }}</p>
              <p class="text-[9px] text-slate-500">Edges</p>
            </div>
          </div>
          <Transition name="fade">
            <button v-if="store.phase1Waiting" @click="advance"
                    class="w-full py-2 rounded-xl bg-violet-600 hover:bg-violet-500
                           text-xs font-semibold text-white transition-colors shadow-lg shadow-violet-900/30">
              ▶ Start Testing
            </button>
            <p v-else class="text-[10px] text-slate-600 text-center">{{ phaseHint }}</p>
          </Transition>
        </div>
      </aside>

      <!-- ── Col 2: Toggleable center panel ───────────────────────── -->
      <div class="flex-1 overflow-hidden relative border-r border-slate-800">
        <GraphView
          v-if="centerView === 'graph'"
          :nodes="store.graph.nodes"
          :edges="store.graph.edges"
        />
        <AgentNetwork v-else-if="centerView === 'network'" />
      </div>

      <!-- ── Col 3: Right panel (Agent output OR CommsFeed) ────────── -->
      <div class="w-72 flex-shrink-0 min-h-0 flex flex-col border-l border-slate-800">
        <!-- Tab bar -->
        <div class="flex border-b border-slate-800 flex-shrink-0">
          <button
            v-for="tab in RIGHT_TABS" :key="tab.id"
            @click="rightTab = tab.id"
            :class="[
              'flex-1 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors',
              rightTab === tab.id
                ? 'text-violet-400 border-b-2 border-violet-500 -mb-px bg-slate-900/50'
                : 'text-slate-600 hover:text-slate-400',
            ]"
          >{{ tab.label }}</button>
        </div>
        <div class="flex-1 min-h-0">
          <AgentOutputPanel v-if="rightTab === 'output'" :agent-name="selectedAgent" />
          <CommsFeed v-else-if="rightTab === 'comms'" />
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- PHASE 2: Graph | Chat                                         -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <div v-else class="flex-1 min-h-0 flex">
      <!-- Knowledge Graph -->
      <div class="flex-1 overflow-hidden relative">
        <GraphView :nodes="store.graph.nodes" :edges="store.graph.edges" />
      </div>
      <!-- Right: stacked CommsFeed + Chat -->
      <div class="w-[420px] flex-shrink-0 border-l border-slate-800 flex flex-col">
        <!-- Comms strip (top 40%) -->
        <div class="flex-[0_0_40%] min-h-0 border-b border-slate-800">
          <CommsFeed />
        </div>
        <!-- Chat (bottom 60%) -->
        <div class="flex-1 min-h-0">
          <ChatPanel :session-id="sessionId" />
        </div>
      </div>
    </div>

    <!-- Phase transition overlay -->
    <Transition name="overlay">
      <div v-if="transitioning"
           class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center">
        <div class="text-center">
          <div class="text-5xl mb-4 animate-pulse">🔄</div>
          <p class="text-lg font-semibold text-violet-300">Entering Testing Phase…</p>
          <p class="text-sm text-slate-400 mt-2">Setting up the chat interface</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, defineComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/sessionStore'
import AgentOutputPanel from '@/components/AgentOutputPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import GraphView from '@/components/GraphView.vue'
import CommsFeed from '@/components/CommsFeed.vue'
import AgentNetwork from '@/components/AgentNetwork.vue'

const PhaseChip = defineComponent({
  props: { active: Boolean, done: Boolean, label: String },
  template: `
    <span :class="[
      'px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
      active ? 'bg-violet-600 text-white' :
      done   ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800' :
               'bg-slate-800 text-slate-500',
    ]">{{ label }}</span>
  `,
})

const CENTER_VIEWS = [
  { id: 'graph',   icon: '⬡', label: 'Graph'   },
  { id: 'network', icon: '🕸', label: 'Network'  },
]

const RIGHT_TABS = [
  { id: 'output', label: 'Output' },
  { id: 'comms',  label: 'Comms'  },
]

const route  = useRoute()
const router = useRouter()
const store  = useSessionStore()

const sessionId     = computed(() => route.params.id)
const sess          = computed(() => store.current)
const selectedAgent = ref(null)
const transitioning = ref(false)
const centerView    = ref('graph')
const rightTab      = ref('output')

const completedCount = computed(() =>
  store.agentCards.filter(a => a.status === 'completed').length
)

const phaseHint = computed(() => {
  if (store.phaseStatus.phase1 === 'running') return 'Phase 1 running…'
  if (store.phaseStatus.phase1 === 'completed') return 'Phase 1 complete'
  return 'Session starting…'
})

// Auto-switch to comms tab when messages arrive
watch(() => store.agentMessages.length, (len) => {
  if (len > 0 && rightTab.value === 'output') rightTab.value = 'comms'
})

watch(() => store.phase2Ready, (val) => {
  if (val) {
    transitioning.value = true
    setTimeout(() => { transitioning.value = false }, 1500)
  }
})

// Auto-select first agent
watch(() => store.agentCards, (cards) => {
  if (cards.length && !selectedAgent.value)
    selectedAgent.value = cards[0].name
}, { immediate: true })

onMounted(async () => {
  store.reset()
  let session
  try {
    session = await store.loadSession(sessionId.value)
  } catch {
    router.push('/')
    return
  }
  if (session.status === 'created') {
    await store.startSession(sessionId.value)
  } else {
    store.connectWs(sessionId.value)
  }
})

onUnmounted(() => {
  store.disconnectWs()
})

async function advance() {
  await store.advancePhase(sessionId.value)
}

async function stopSession() {
  await store.stopSession(sessionId.value)
  router.push('/')
}

function agentIconBg(status) {
  return ({
    idle: '#1e293b', thinking: '#451a03', active: '#2e1065',
    completed: '#052e16', error: '#450a0a', skipped: '#1e293b',
  })[status] || '#1e293b'
}

function statusDot(status) {
  return ({
    idle: 'bg-slate-600', thinking: 'bg-amber-400 animate-pulse',
    active: 'bg-violet-400 animate-pulse', completed: 'bg-emerald-400',
    error: 'bg-red-400', skipped: 'bg-slate-700',
  })[status] || 'bg-slate-600'
}

function agentHasStats(agent) {
  const s = agent.stats
  return s && (s.nodes_added > 0 || s.edges_added > 0)
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }

.overlay-enter-active, .overlay-leave-active { transition: opacity 0.4s ease; }
.overlay-enter-from, .overlay-leave-to       { opacity: 0; }
</style>
