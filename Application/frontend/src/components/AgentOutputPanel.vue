<template>
  <div class="h-full flex flex-col bg-slate-950 text-slate-100">
    <!-- Panel header -->
    <div class="flex-shrink-0 px-5 py-3 border-b border-slate-800 flex items-center gap-3">
      <span class="text-base">{{ agentIcon }}</span>
      <div>
        <p class="text-sm font-semibold text-slate-100">{{ agentDisplayName || 'Select an agent' }}</p>
        <p class="text-xs text-slate-400">Real-time output stream</p>
      </div>
      <span class="ml-auto text-xs text-slate-500">{{ events.length }} event(s)</span>
    </div>

    <!-- Empty state -->
    <div v-if="!agentName" class="flex-1 flex items-center justify-center">
      <div class="text-center text-slate-600">
        <div class="text-4xl mb-3">👈</div>
        <p class="text-sm">Click an agent to view its output</p>
      </div>
    </div>

    <div v-else-if="events.length === 0" class="flex-1 flex items-center justify-center">
      <div class="text-center text-slate-600">
        <div class="text-4xl mb-3 animate-pulse">⏳</div>
        <p class="text-sm">Waiting for agent output…</p>
      </div>
    </div>

    <!-- Event stream -->
    <div v-else ref="scrollEl" class="flex-1 min-h-0 overflow-y-auto p-4 space-y-2 font-mono text-xs">
      <TransitionGroup name="event-slide">
        <div v-for="(ev, i) in events" :key="i"
             :class="['rounded-lg px-3 py-2 border-l-2 flex gap-2', rowClass(ev.type)]">
          <span class="flex-shrink-0 mt-0.5">{{ rowIcon(ev.type) }}</span>
          <div class="flex-1 min-w-0">
            <span class="text-slate-400 mr-2">{{ fmtTs(ev.ts) }}</span>
            <span :class="labelClass(ev.type)" class="font-semibold mr-2 uppercase tracking-wide text-[10px]">{{ rowLabel(ev.type, ev.data) }}</span>
            <span class="text-slate-200 break-words">{{ rowMessage(ev) }}</span>

            <!-- Node detail -->
            <div v-if="ev.type === 'agent.node_added' && ev.data?.node" class="mt-1 text-slate-400">
              <span class="text-violet-400">{{ ev.data.node.label }}</span>
              <span class="mx-1 text-slate-600">·</span>
              <span class="text-cyan-400">{{ ev.data.node.type }}</span>
              <span v-if="ev.data.node.description" class="mx-1 text-slate-600">·</span>
              <span v-if="ev.data.node.description" class="text-slate-400">{{ ev.data.node.description }}</span>
            </div>

            <!-- Edge detail -->
            <div v-if="ev.type === 'agent.edge_added' && ev.data?.edge" class="mt-1 text-slate-400">
              <span class="text-violet-400">{{ ev.data.edge.from_node }}</span>
              <span class="mx-1 text-slate-500">→</span>
              <span class="text-violet-400">{{ ev.data.edge.to_node }}</span>
              <span class="mx-1 text-slate-600">·</span>
              <span class="text-amber-400">{{ ev.data.edge.type }}</span>
              <span class="ml-1 text-slate-500">(w={{ (ev.data.edge.weight || 1).toFixed(2) }})</span>
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const props = defineProps({
  agentName: { type: String, default: null },
})

const store = useSessionStore()
const scrollEl = ref(null)

const events = computed(() =>
  props.agentName ? (store.agentOutputs[props.agentName] || []) : []
)

const agentCard = computed(() =>
  store.agentCards.find(a => a.name === props.agentName)
)

const agentDisplayName = computed(() => agentCard.value?.display_name || props.agentName)
const agentIcon = computed(() => agentCard.value?.icon || '🤖')

watch(events, async () => {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}, { deep: true })

function rowClass(type) {
  switch (type) {
    case 'agent.thinking':   return 'bg-amber-950/30 border-amber-600/50 text-amber-100'
    case 'agent.output':     return 'bg-emerald-950/30 border-emerald-600/50 text-emerald-100'
    case 'agent.node_added': return 'bg-violet-950/30 border-violet-600/50 text-violet-100'
    case 'agent.edge_added': return 'bg-cyan-950/30 border-cyan-600/50 text-cyan-100'
    case 'agent.started':    return 'bg-slate-800/50 border-slate-600/50 text-slate-300'
    case 'agent.completed':  return 'bg-emerald-950/50 border-emerald-500 text-emerald-200'
    case 'agent.error':      return 'bg-red-950/30 border-red-600/50 text-red-200'
    default:                 return 'bg-slate-800/30 border-slate-700/50 text-slate-300'
  }
}

function rowIcon(type) {
  switch (type) {
    case 'agent.thinking':   return '💭'
    case 'agent.output':     return '💡'
    case 'agent.node_added': return '⬡'
    case 'agent.edge_added': return '↔'
    case 'agent.started':    return '▶'
    case 'agent.completed':  return '✓'
    case 'agent.error':      return '✗'
    default:                 return '·'
  }
}

function rowLabel(type, data) {
  if (type === 'agent.output') return data?.output_type || 'output'
  return type.replace('agent.', '')
}

function labelClass(type) {
  switch (type) {
    case 'agent.thinking':   return 'text-amber-400'
    case 'agent.output':     return 'text-emerald-400'
    case 'agent.node_added': return 'text-violet-400'
    case 'agent.edge_added': return 'text-cyan-400'
    case 'agent.completed':  return 'text-emerald-300'
    case 'agent.error':      return 'text-red-400'
    default:                 return 'text-slate-400'
  }
}

function rowMessage(ev) {
  const d = ev.data || {}
  switch (ev.type) {
    case 'agent.thinking':   return d.thought || ''
    case 'agent.output':     return d.message || ''
    case 'agent.node_added': return ''  // shown in detail block
    case 'agent.edge_added': return ''  // shown in detail block
    case 'agent.started':    return d.message || 'Agent started'
    case 'agent.completed':  return d.message || 'Completed'
    case 'agent.error':      return d.message || 'Error'
    default:                 return JSON.stringify(d).slice(0, 120)
  }
}

function fmtTs(ts) {
  if (!ts) return ''
  try { return new Date(ts).toLocaleTimeString('en-US', { hour12: false }) }
  catch { return '' }
}
</script>

<style scoped>
.event-slide-enter-active { transition: all 0.2s ease; }
.event-slide-enter-from   { opacity: 0; transform: translateY(6px); }
</style>
