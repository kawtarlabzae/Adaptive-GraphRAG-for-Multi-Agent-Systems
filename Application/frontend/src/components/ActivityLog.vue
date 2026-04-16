<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 flex-shrink-0">
      <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Activity Log</p>
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400">{{ displayEvents.length }} events</span>
        <button @click="filterAll = !filterAll" :class="['text-xs px-2 py-0.5 rounded-md transition-colors', filterAll ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-500']">
          All
        </button>
      </div>
    </div>

    <!-- Log entries -->
    <div ref="logRef" class="flex-1 min-h-0 overflow-y-auto px-3 py-2 space-y-1 mono text-xs">
      <TransitionGroup name="log-item">
        <div v-for="(ev, i) in displayEvents" :key="i"
             :class="['px-2.5 py-1.5 rounded-lg flex items-start gap-2 border', eventClass(ev)]">
          <span class="flex-shrink-0 mt-0.5">{{ eventIcon(ev) }}</span>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span v-if="ev.agent" class="badge badge-neutral text-xs font-normal">{{ ev.agent_icon }} {{ ev.agent_display || ev.agent }}</span>
              <span class="text-xs opacity-50">{{ formatTime(ev.timestamp) }}</span>
            </div>
            <p class="text-xs mt-0.5 leading-relaxed break-words">{{ eventMessage(ev) }}</p>
          </div>
        </div>
      </TransitionGroup>
      <div v-if="displayEvents.length === 0" class="text-center text-slate-300 py-8">
        Waiting for events…
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({ events: { type: Array, default: () => [] } })
const logRef = ref(null)
const filterAll = ref(true)

const SHOW_TYPES = [
  'session.started', 'phase.started', 'phase.completed',
  'agent.started', 'agent.thinking', 'agent.completed', 'agent.error',
  'agent.conflict_found', 'agent.node_added', 'agent.edge_added',
  'agent.node_pruned', 'agent.scenario_result', 'agent.path_computed',
  'omniverse.started', 'omniverse.command_applied', 'omniverse.llm_command',
  'omniverse.completed', 'session.completed', 'session.error',
]

const displayEvents = computed(() => {
  const evs = filterAll.value ? props.events : props.events.filter(e => SHOW_TYPES.includes(e.type))
  return evs.slice(-80).reverse()
})

function eventClass(ev) {
  const t = ev.type || ''
  if (t.includes('error')) return 'border-red-100 bg-red-50 text-red-700'
  if (t.includes('completed') || t.includes('phase.completed')) return 'border-emerald-100 bg-emerald-50 text-emerald-700'
  if (t.includes('conflict_found')) return 'border-amber-100 bg-amber-50 text-amber-700'
  if (t.includes('node_pruned')) return 'border-orange-100 bg-orange-50 text-orange-700'
  if (t.includes('omniverse')) return 'border-cyan-100 bg-cyan-50 text-cyan-700'
  if (t.includes('phase.started') || t.includes('session.started')) return 'border-brand-100 bg-brand-50 text-brand-700'
  if (t.includes('thinking')) return 'border-amber-100 bg-amber-50/50 text-amber-600'
  return 'border-slate-100 bg-white text-slate-600'
}

function eventIcon(ev) {
  const t = ev.type || ''
  if (t.includes('conflict'))    return '⚔️'
  if (t.includes('node_added'))  return '⬡'
  if (t.includes('edge_added'))  return '→'
  if (t.includes('node_pruned')) return '✂️'
  if (t.includes('scenario'))    return '🎭'
  if (t.includes('path'))        return '🧭'
  if (t.includes('omniverse'))   return '⬡'
  if (t.includes('error'))       return '❌'
  if (t.includes('completed'))   return '✅'
  if (t.includes('thinking'))    return '💭'
  if (t.includes('started'))     return '▶️'
  if (t.includes('phase'))       return '🔄'
  return '•'
}

function eventMessage(ev) {
  const d = ev.data || {}
  const t = ev.type || ''

  if (t === 'agent.thinking')        return d.thought || '…'
  if (t === 'agent.started')         return d.message || 'Starting…'
  if (t === 'agent.completed')       return d.message || 'Completed.'
  if (t === 'agent.conflict_found')  return `Conflict: ${d.topic} — ${d.source_a?.slice(0, 40)}… vs ${d.source_b?.slice(0, 40)}…`
  if (t === 'agent.node_added')      return `Node: ${d.node?.label} (${d.node?.type})`
  if (t === 'agent.edge_added')      return `Edge: ${d.edge?.from_node} →[${d.edge?.type}]→ ${d.edge?.to_node}`
  if (t === 'agent.node_pruned')     return `Pruned: ${d.label} (utility=${d.utility_score})`
  if (t === 'agent.scenario_result') return `Scenario ${d.passed ? '✓' : '✗'} (conf=${d.confidence?.toFixed(2)}): ${d.query?.slice(0, 60)}…`
  if (t === 'agent.path_computed')   return `Path: ${d.start_node} → [${d.paths?.length || 0} paths found]`
  if (t === 'phase.started')         return `Phase ${d.phase}: ${d.message}`
  if (t === 'phase.completed')       return `Phase ${d.phase} complete — ${d.message}`
  if (t === 'session.started')       return d.message || 'Session started'
  if (t === 'session.completed')     return `Pipeline complete! LCA=${(d.metrics?.logical_chain_accuracy * 100 || 0).toFixed(0)}% CE=${(d.metrics?.context_efficiency * 100 || 0).toFixed(0)}%`
  if (t === 'omniverse.started')     return d.message || 'Omniverse ready'
  if (t === 'omniverse.command_applied') return `CMD: ${d.command?.command} → ${d.result?.message}`
  if (t === 'omniverse.llm_command') return `LLM→ ${d.command?.command}: ${d.command?.parameters?.reason?.slice(0, 60) || '…'}`
  if (t === 'omniverse.completed')   return d.message || 'Simulation done'
  if (t === 'session.error')         return `Error: ${d.message}`
  if (t === 'documents.ready')       return `Documents ready: ${d.total_chunks} chunks`
  return d.message || t
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return '' }
}

// Auto-scroll on new events
watch(() => props.events.length, async () => {
  await nextTick()
  // log is reversed so no scroll needed
})
</script>

<style scoped>
.log-item-enter-active { transition: all 0.2s ease-out; }
.log-item-enter-from   { opacity: 0; transform: translateY(-4px); }
</style>
