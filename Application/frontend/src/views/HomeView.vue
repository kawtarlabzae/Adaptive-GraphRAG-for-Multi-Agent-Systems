<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
    <!-- Header -->
    <header class="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-40">
      <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-gradient-to-br from-brand-500 to-cyan-500 rounded-lg flex items-center justify-center text-white text-lg">⬡</div>
          <div>
            <h1 class="font-bold text-slate-900 text-lg leading-none">KnowledgeCore</h1>
            <p class="text-xs text-slate-500 leading-none mt-0.5">GraphRAG · Digital Twins</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 text-xs">
            <span :class="['status-dot', neo4jOk ? 'active' : 'error']" />
            <span class="text-slate-500">Neo4j</span>
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span :class="['status-dot', ollamaOk ? 'active' : 'idle']" />
            <span class="text-slate-500">Ollama</span>
          </div>
          <button @click="showWizard = true" class="btn-primary">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            New Session
          </button>
        </div>
      </div>
    </header>

    <div class="max-w-6xl mx-auto px-6 py-12">
      <!-- Hero -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center gap-2 bg-brand-50 text-brand-700 px-4 py-1.5 rounded-full text-sm font-medium mb-4">
          <span>🔬</span> Modular Knowledge-as-a-Component Framework
        </div>
        <h2 class="text-4xl font-bold text-slate-900 mb-3">
          Adaptive Multi-Agent
          <span class="gradient-text"> GraphRAG</span>
        </h2>
        <p class="text-slate-500 max-w-xl mx-auto text-lg">
          Build high-fidelity knowledge graphs from documents using a two-phase multi-agent architecture,
          then deploy them as modular firmware for Digital Twin reasoning.
        </p>
      </div>

      <!-- Architecture cards -->
      <div class="grid grid-cols-3 gap-4 mb-12">
        <div class="card p-5">
          <div class="text-2xl mb-2">⚔️</div>
          <h3 class="font-semibold text-slate-900 mb-1">Phase 1 — Study Room</h3>
          <p class="text-sm text-slate-500">Conflict Agent + Synthesizer Agent detect contradictions and build the High-Fidelity Consensus Graph.</p>
        </div>
        <div class="card p-5">
          <div class="text-2xl mb-2">✂️</div>
          <h3 class="font-semibold text-slate-900 mb-1">Phase 2 — Engineering Lab</h3>
          <p class="text-sm text-slate-500">Scenario Agent + Pruning Agent stress-test the graph and produce a Task-Optimised sub-graph.</p>
        </div>
        <div class="card p-5">
          <div class="text-2xl mb-2">🌿</div>
          <h3 class="font-semibold text-slate-900 mb-1">Digital Twin</h3>
          <p class="text-sm text-slate-500">Pathfinder Agent drives NVIDIA Omniverse Smart Vineyard simulation via graph-traversal decisions.</p>
        </div>
      </div>

      <!-- Sessions list -->
      <div v-if="store.sessions.length">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-slate-900">Previous Sessions</h3>
          <span class="text-xs text-slate-400">{{ store.sessions.length }} session(s)</span>
        </div>
        <div class="grid gap-3">
          <div v-for="sess in store.sessions" :key="sess.id"
               class="card p-4 flex items-center justify-between hover:shadow-md transition-shadow cursor-pointer"
               @click="openSession(sess.id)">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center text-lg">
                {{ sess.config.domain === 'aviation' ? '✈️' : sess.config.domain === 'custom' ? '⚙️' : '🔬' }}
              </div>
              <div>
                <p class="font-medium text-slate-900 text-sm">{{ sess.config.name }}</p>
                <p class="text-xs text-slate-400">{{ sess.config.domain }} · {{ sess.config.model }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span :class="['badge', statusBadgeClass(sess.status)]">{{ sess.status }}</span>
              <button @click.stop="store.deleteSession(sess.id)" class="text-slate-300 hover:text-red-400 transition-colors">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-16">
        <div class="text-5xl mb-4">🧪</div>
        <p class="text-slate-400 mb-4">No sessions yet. Create your first GraphRAG session.</p>
        <button @click="showWizard = true" class="btn-primary">Create First Session</button>
      </div>
    </div>

    <!-- Wizard modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showWizard" class="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
             @click.self="showWizard = false">
          <StepWizard @close="showWizard = false" @created="onSessionCreated" />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/sessionStore'
import StepWizard from '@/components/StepWizard.vue'

const router = useRouter()
const store = useSessionStore()
const showWizard = ref(false)

const neo4jOk = computed(() => store.systemStatus.neo4j?.includes('connected'))
const ollamaOk = computed(() => store.systemStatus.ollama?.includes('available'))

onMounted(() => {
  store.fetchStatus()
  store.fetchSessions()
})

function sessionRoute(id) {
  const sess = store.sessions.find(s => s.id === id)
  const domain = sess?.config?.domain
  if (domain === 'aviation') return `/aero/${id}`
  if (domain === 'custom')   return `/general/${id}`
  return `/session/${id}`
}

function openSession(id) {
  router.push(sessionRoute(id))
}

function onSessionCreated(session) {
  showWizard.value = false
  const domain = session.config?.domain
  let route = `/session/${session.id}`
  if (domain === 'aviation') route = `/aero/${session.id}`
  if (domain === 'custom')   route = `/general/${session.id}`
  router.push(route)
}

function statusBadgeClass(status) {
  return {
    created: 'badge-neutral', running: 'badge-info',
    completed: 'badge-success', stopped: 'badge-warning',
    error: 'badge-danger'
  }[status] || 'badge-neutral'
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
