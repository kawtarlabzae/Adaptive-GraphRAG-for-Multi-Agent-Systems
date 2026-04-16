<template>
  <div @click="$emit('select', agent.name)" :class="[
    'rounded-xl border p-3 transition-all duration-300',
    clickable ? 'cursor-pointer' : '',
    selected ? 'ring-2 ring-violet-500 ring-offset-1' : '',
    agent.status === 'active' ? 'border-brand-200 bg-brand-50 shadow-sm ring-pulse' :
    agent.status === 'thinking' ? 'border-amber-200 bg-amber-50' :
    agent.status === 'completed' ? 'border-emerald-200 bg-emerald-50' :
    agent.status === 'error' ? 'border-red-200 bg-red-50' :
    agent.status === 'skipped' ? 'border-slate-100 bg-slate-50 opacity-50' :
    'border-slate-200 bg-white'
  ]">
    <div class="flex items-start gap-2.5">
      <!-- Icon -->
      <div :class="[
        'w-8 h-8 rounded-lg flex items-center justify-center text-base flex-shrink-0 transition-transform',
        agent.status === 'active' || agent.status === 'thinking' ? 'animate-bounce' : ''
      ]" :style="{ background: iconBg }">
        {{ agent.icon }}
      </div>

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5 mb-0.5">
          <span class="text-xs font-semibold text-slate-800 truncate">{{ agent.display_name }}</span>
          <span :class="['status-dot flex-shrink-0', agent.status]" />
          <span :class="['badge text-xs ml-auto flex-shrink-0', phaseClass]">P{{ agent.phase }}</span>
        </div>

        <!-- Status text -->
        <p v-if="agent.task" class="text-xs text-slate-500 truncate leading-relaxed">{{ agent.task }}</p>
        <p v-else class="text-xs text-slate-400 capitalize">{{ agent.status }}</p>

        <!-- Progress bar -->
        <div v-if="agent.status === 'active' || agent.status === 'thinking'" class="mt-2 h-1 bg-white/70 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500"
               :class="agent.status === 'thinking' ? 'bg-amber-400 animate-pulse' : 'bg-brand-500'"
               :style="{ width: `${Math.max(5, (agent.progress || 0) * 100)}%` }" />
        </div>
        <div v-else-if="agent.status === 'completed'" class="mt-2 h-1 bg-emerald-200 rounded-full overflow-hidden">
          <div class="h-full w-full bg-emerald-500 rounded-full" />
        </div>

        <!-- Mini stats -->
        <div v-if="hasStats" class="flex gap-2 mt-2 flex-wrap">
          <StatChip v-if="agent.stats?.nodes_added"    :val="agent.stats.nodes_added"    label="nodes" />
          <StatChip v-if="agent.stats?.edges_added"    :val="agent.stats.edges_added"    label="edges" />
          <StatChip v-if="agent.stats?.conflicts_found" :val="agent.stats.conflicts_found" label="conflicts" />
          <StatChip v-if="agent.stats?.nodes_pruned"   :val="agent.stats.nodes_pruned"   label="pruned" />
          <StatChip v-if="agent.stats?.paths_computed" :val="agent.stats.paths_computed" label="paths" />
          <StatChip v-if="agent.stats?.scenarios_tested" :val="agent.stats.scenarios_tested" label="scenarios" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const StatChip = {
  props: ['val', 'label'],
  template: '<span class="inline-flex items-center gap-1 text-xs bg-white/80 border border-slate-200 px-1.5 py-0.5 rounded-md text-slate-600"><b>{{ val }}</b> {{ label }}</span>'
}

const props = defineProps({ agent: Object, selected: Boolean, clickable: Boolean })
defineEmits(['select'])

const iconBg = computed(() => ({
  idle: '#f1f5f9', thinking: '#fef3c7', active: '#e0e7ff',
  completed: '#d1fae5', error: '#fee2e2', skipped: '#f1f5f9'
})[props.agent.status] || '#f1f5f9')

const phaseClass = computed(() =>
  props.agent.phase === 1 ? 'badge-purple' : 'badge-info'
)

const hasStats = computed(() => {
  const s = props.agent.stats
  return s && Object.values(s).some(v => v > 0)
})
</script>
