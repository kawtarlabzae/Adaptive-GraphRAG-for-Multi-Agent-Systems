<template>
  <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-slide-up">
    <!-- Header -->
    <div class="bg-gradient-to-r from-brand-600 to-cyan-500 px-8 py-6 text-white">
      <h2 class="text-xl font-bold">New GraphRAG Session</h2>
      <p class="text-white/70 text-sm mt-1">{{ stepDescriptions[step - 1] }}</p>
      <div class="flex items-center gap-2 mt-4">
        <template v-for="n in 4" :key="n">
          <div class="flex items-center gap-2">
            <div :class="[
              'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all',
              step > n ? 'bg-white text-brand-700' :
              step === n ? 'bg-white/30 text-white ring-2 ring-white' :
              'bg-white/10 text-white/50'
            ]">
              <svg v-if="step > n" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
              </svg>
              <span v-else>{{ n }}</span>
            </div>
            <span class="text-xs text-white/60 hidden sm:block">{{ stepLabels[n - 1] }}</span>
          </div>
          <div v-if="n < 4" class="flex-1 h-px bg-white/20" />
        </template>
      </div>
    </div>

    <!-- Body -->
    <div class="px-8 py-6" style="min-height: 340px">
      <Transition name="step" mode="out-in">

        <!-- Step 1: Session Info -->
        <div v-if="step === 1" key="1" class="space-y-4">
          <div>
            <label class="label">Session Name <span class="text-red-400">*</span></label>
            <input v-model="form.name" class="input" placeholder="e.g. Aviation Safety Research" maxlength="80" />
          </div>
          <div>
            <label class="label">Description</label>
            <textarea v-model="form.description" class="input resize-none" rows="2"
                      placeholder="Optional description…" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Domain</label>
              <select v-model="form.domain" class="input">
                <option value="viticulture">🍇 Smart Viticulture</option>
                <option value="aviation">✈️ Aero Digital Twin (JFK→LHR)</option>
                <option value="agriculture">🌾 Precision Agriculture</option>
                <option value="custom">⚙️ Custom Domain</option>
              </select>
            </div>
            <div>
              <label class="label">LLM Model</label>
              <select v-model="form.model" class="input">
                <option value="llama3.2">llama3.2 (recommended)</option>
                <option value="llama3">llama3</option>
                <option value="mistral">mistral</option>
                <option value="gemma2">gemma2</option>
                <option value="phi3">phi3</option>
              </select>
            </div>
          </div>

          <!-- Domain hints -->
          <div v-if="isResearchNetwork"
               class="flex items-start gap-2 bg-violet-50 text-violet-800 rounded-xl p-3 text-sm">
            <span class="text-lg flex-shrink-0">{{ form.domain === 'aviation' ? '✈️' : '⚙️' }}</span>
            <div>
              <p class="font-semibold mb-0.5">Self-Organizing Research Network</p>
              <p class="text-violet-700 text-xs">
                Agents start with no assigned roles. They <strong>negotiate their own specialisations</strong>
                through the Agent Message Bus, then collectively build the knowledge graph.
                This session investigates how emergent agent roles affect knowledge extraction quality.
              </p>
            </div>
          </div>
          <div v-else class="flex items-center gap-2 bg-blue-50 text-blue-700 rounded-xl p-3 text-sm">
            <span>ℹ️</span>
            The <strong>{{ form.domain }}</strong> domain includes a pre-seeded knowledge base
            with specialized agents (Conflict, Synthesizer, Scenario, Pruning, Pathfinder).
          </div>
        </div>

        <!-- Step 2a: Standard agent config (viticulture / agriculture) -->
        <div v-else-if="step === 2 && !isResearchNetwork" key="2" class="space-y-3">
          <p class="text-sm text-slate-500 mb-2">
            Select agents for your pipeline. Phase 1 builds the graph; Phase 2 optimises it.
          </p>
          <div v-for="agent in agentConfig" :key="agent.key"
               class="flex items-start gap-3 p-3 rounded-xl border transition-colors"
               :class="form.agents.includes(agent.key) ? 'border-brand-300 bg-brand-50' : 'border-slate-200 bg-white'">
            <input type="checkbox" :id="agent.key" :value="agent.key" v-model="form.agents"
                   class="mt-1 w-4 h-4 text-brand-600 rounded" />
            <label :for="agent.key" class="flex-1 cursor-pointer">
              <div class="flex items-center gap-2">
                <span>{{ agent.icon }}</span>
                <span class="font-medium text-slate-900 text-sm">{{ agent.name }}</span>
                <span :class="['badge text-xs', agent.phase === 1 ? 'badge-purple' : 'badge-info']">Phase {{ agent.phase }}</span>
              </div>
              <p class="text-xs text-slate-500 mt-0.5 ml-6">{{ agent.description }}</p>
            </label>
          </div>
          <div class="flex items-start gap-3 p-3 rounded-xl border mt-2"
               :class="form.omniverse_enabled ? 'border-emerald-300 bg-emerald-50' : 'border-slate-200 bg-white'">
            <input type="checkbox" id="omniverse" v-model="form.omniverse_enabled"
                   class="mt-1 w-4 h-4 text-emerald-600 rounded" />
            <label for="omniverse" class="cursor-pointer">
              <div class="font-medium text-slate-900 text-sm flex items-center gap-2">
                <span>⬡</span> NVIDIA Omniverse Digital Twin
                <span class="badge badge-success">Recommended</span>
              </div>
              <p class="text-xs text-slate-500 mt-0.5">Enable Smart Vineyard simulation with real-time LLM-driven decisions.</p>
            </label>
          </div>
        </div>

        <!-- Step 2b: Research network config (custom + aviation) -->
        <div v-else-if="step === 2 && isResearchNetwork" key="2r" class="space-y-5">

          <!-- Agent count -->
          <div>
            <label class="label flex items-center justify-between">
              <span>Number of Research Agents</span>
              <span class="text-brand-600 font-bold text-lg">{{ form.num_agents }}</span>
            </label>
            <input v-model.number="form.num_agents" type="range" min="2" max="8" step="1"
                   class="w-full h-2 rounded-full accent-brand-600 cursor-pointer" />
            <div class="flex justify-between text-xs text-slate-400 mt-1">
              <span>2 (minimal)</span><span>5 (recommended)</span><span>8 (dense)</span>
            </div>
            <p class="text-xs text-slate-500 mt-2">
              Agents negotiate their own focus areas — no roles are pre-assigned.
            </p>
          </div>

          <!-- Research goal -->
          <div>
            <label class="label">Research Goal <span class="text-red-400">*</span></label>
            <textarea v-model="form.research_goal" class="input resize-none" rows="3"
                      :placeholder="goalPlaceholder" />
            <p class="text-xs text-slate-400 mt-1">
              Shared goal the agent network collectively pursues. Agents read this during role negotiation.
            </p>
          </div>

          <!-- Agent preview -->
          <div>
            <p class="label mb-2">Agent Preview</p>
            <div class="flex flex-wrap gap-2">
              <div v-for="i in form.num_agents" :key="i"
                   class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-violet-200 bg-violet-50">
                <span class="text-sm">{{ ICONS[(i - 1) % ICONS.length] }}</span>
                <span class="text-xs font-medium text-violet-700">Agent {{ i - 1 }}</span>
                <span class="text-[10px] text-violet-400 italic">role TBD</span>
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-2">
              Roles emerge during Phase 1 through Agent Message Bus negotiation.
            </p>
          </div>
        </div>

        <!-- Step 3: File Upload -->
        <div v-else-if="step === 3" key="3" class="space-y-4">
          <div @dragover.prevent @drop.prevent="onDrop"
               class="border-2 border-dashed rounded-xl p-8 text-center transition-colors"
               :class="dragging ? 'border-brand-400 bg-brand-50' : 'border-slate-200 hover:border-brand-300'">
            <div class="text-4xl mb-2">📂</div>
            <p class="font-medium text-slate-700 mb-1">Drop documents here</p>
            <p class="text-xs text-slate-400 mb-3">PDF, TXT, Markdown — research papers, technical manuals</p>
            <label class="btn-secondary cursor-pointer">
              Browse Files
              <input type="file" multiple accept=".pdf,.txt,.md,.csv" class="hidden" @change="onFileSelect" />
            </label>
          </div>

          <div v-if="localFiles.length" class="space-y-2">
            <div v-for="(f, i) in localFiles" :key="i"
                 class="flex items-center gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-lg">{{ fileIcon(f) }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">{{ f.name }}</p>
                <p class="text-xs text-slate-400">{{ fileSize(f.size) }}</p>
              </div>
              <button @click="removeLocalFile(i)" class="text-slate-300 hover:text-red-400 transition-colors">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <div v-if="isResearchNetwork" class="bg-violet-50 text-violet-700 rounded-xl p-3 text-sm flex gap-2">
            <span>💡</span>
            <span>
              Documents are distributed across agents. Each agent reads a distinct slice,
              then shares findings via the Agent Message Bus.
              <span v-if="form.domain === 'aviation'">
                The aviation knowledge base is pre-seeded — additional documents enrich the graph.
              </span>
            </span>
          </div>
          <div v-else class="bg-amber-50 text-amber-700 rounded-xl p-3 text-sm flex gap-2">
            <span>💡</span>
            <span>If no files are uploaded, the session will use the built-in <strong>viticulture knowledge base</strong>.</span>
          </div>
        </div>

        <!-- Step 4: Configuration + Review -->
        <div v-else-if="step === 4" key="4" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Chunk Size (tokens)</label>
              <input v-model.number="form.chunk_size" type="number" class="input" min="200" max="2000" step="50" />
            </div>
            <div>
              <label class="label">Confidence Threshold</label>
              <input v-model.number="form.confidence_threshold" type="number" class="input" min="0.1" max="1.0" step="0.05" />
            </div>
          </div>

          <!-- Summary -->
          <div class="bg-slate-50 rounded-xl p-4 space-y-2 text-sm">
            <p class="font-semibold text-slate-700 mb-2">Session Summary</p>
            <Row label="Name"   :value="form.name" />
            <Row label="Domain" :value="form.domain" />
            <Row label="Model"  :value="form.model" />
            <Row v-if="isResearchNetwork"
                 label="Agents"  :value="`${form.num_agents} self-organizing research agents`" />
            <Row v-else
                 label="Agents"  :value="`${form.agents.length} enabled`" />
            <Row label="Files"  :value="localFiles.length ? localFiles.length + ' file(s)' : 'Built-in KB'" />
            <Row v-if="!isResearchNetwork"
                 label="Omniverse" :value="form.omniverse_enabled ? '✅ Enabled' : '❌ Disabled'" />
            <Row v-if="isResearchNetwork && form.research_goal"
                 label="Goal" :value="form.research_goal.slice(0, 60) + (form.research_goal.length > 60 ? '…' : '')" />
          </div>
        </div>

      </Transition>
    </div>

    <!-- Footer -->
    <div class="border-t border-slate-100 px-8 py-4 flex items-center justify-between">
      <button v-if="step > 1" @click="step--" class="btn-secondary">← Back</button>
      <div v-else />
      <div class="flex items-center gap-3">
        <button @click="$emit('close')" class="text-sm text-slate-400 hover:text-slate-700">Cancel</button>
        <button v-if="step < 4" @click="nextStep" class="btn-primary" :disabled="!canNext">
          Continue →
        </button>
        <button v-else @click="submit" class="btn-primary" :disabled="creating">
          <span v-if="creating" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          {{ creating ? 'Creating…' : '🚀 Create & Open' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const emit = defineEmits(['close', 'created'])
const store = useSessionStore()
const step = ref(1)
const creating = ref(false)
const dragging  = ref(false)
const localFiles = ref([])

const stepLabels = ['Info', 'Agents', 'Files', 'Config']
const stepDescriptions = [
  'Name your session and choose the knowledge domain',
  'Configure the research network',
  'Upload research documents (optional)',
  'Advanced settings and review',
]

const ICONS = ['🔬', '🧠', '📡', '🔍', '💡', '🧩', '📊', '⚡']

const form = ref({
  name: '',
  description: '',
  domain: 'viticulture',
  model: 'llama3.2',
  agents: ['conflict', 'synthesizer', 'scenario', 'pruning', 'pathfinder'],
  omniverse_enabled: true,
  chunk_size: 500,
  confidence_threshold: 0.7,
  utility_threshold: 0.3,
  // Research network fields
  num_agents: 4,
  research_goal: '',
})

const isResearchNetwork = computed(() =>
  form.value.domain === 'custom' || form.value.domain === 'aviation'
)

const goalPlaceholder = computed(() =>
  form.value.domain === 'aviation'
    ? 'e.g. Build a causal knowledge graph for B737-800 fuel efficiency and anomaly detection on transatlantic routes'
    : 'e.g. Extract causal relationships and key concepts from the uploaded research papers'
)

const agentConfig = [
  { key: 'conflict',    name: 'Conflict Agent',    phase: 1, icon: '⚔️', description: 'Detects contradictions and conflicting claims between sources.' },
  { key: 'synthesizer', name: 'Synthesizer Agent', phase: 1, icon: '🔬', description: 'Extracts entities & relationships and builds the consensus graph.' },
  { key: 'scenario',    name: 'Scenario Agent',    phase: 2, icon: '🎭', description: 'Generates multi-hop queries to stress-test graph depth.' },
  { key: 'pruning',     name: 'Pruning Agent',     phase: 2, icon: '✂️', description: 'Removes low-utility nodes to optimise context efficiency.' },
  { key: 'pathfinder',  name: 'Pathfinder Agent',  phase: 2, icon: '🧭', description: 'Probabilistic graph walks for precise sub-graph retrieval.' },
]

const Row = {
  props: ['label', 'value'],
  template: `<div class="flex justify-between">
    <span class="text-slate-500">{{ label }}</span>
    <span class="font-medium text-slate-800 text-right max-w-xs truncate">{{ value }}</span>
  </div>`
}

const canNext = computed(() => {
  if (step.value === 1) return form.value.name.trim().length >= 2
  if (step.value === 2) {
    if (isResearchNetwork.value) return form.value.research_goal.trim().length >= 5
    return form.value.agents.length > 0
  }
  return true
})

function nextStep() {
  if (canNext.value) step.value++
}

function onDrop(e) {
  dragging.value = false
  addFiles(Array.from(e.dataTransfer.files))
}

function onFileSelect(e) {
  addFiles(Array.from(e.target.files))
  e.target.value = ''
}

function addFiles(files) {
  const allowed = ['.pdf', '.txt', '.md', '.csv']
  files.forEach(f => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (allowed.includes(ext) && !localFiles.value.find(x => x.name === f.name))
      localFiles.value.push(f)
  })
}

function removeLocalFile(i) { localFiles.value.splice(i, 1) }

function fileIcon(f) {
  return { pdf: '📕', txt: '📄', md: '📝', csv: '📊' }[f.name.split('.').pop().toLowerCase()] || '📄'
}

function fileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

async function submit() {
  creating.value = true
  try {
    const session = await store.createSession(form.value)
    for (const file of localFiles.value)
      await store.uploadFile(session.id, file)
    emit('created', session)
  } catch (e) {
    console.error('Create session error', e)
    alert('Failed to create session. Is the backend running?')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.step-enter-active, .step-leave-active { transition: all 0.2s ease; }
.step-enter-from { opacity: 0; transform: translateX(12px); }
.step-leave-to   { opacity: 0; transform: translateX(-12px); }
</style>
