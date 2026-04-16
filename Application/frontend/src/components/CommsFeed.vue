<template>
  <div class="h-full flex flex-col bg-slate-900">
    <div class="px-3 py-2 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
      <p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">Agent Comms</p>
      <span class="text-[10px] text-slate-600">{{ messages.length }} msg{{ messages.length !== 1 ? 's' : '' }}</span>
    </div>

    <!-- Filter bar -->
    <div class="px-2 py-1.5 border-b border-slate-800 flex gap-1 flex-wrap flex-shrink-0">
      <button
        v-for="f in FILTERS" :key="f.value"
        @click="activeFilter = activeFilter === f.value ? null : f.value"
        :class="[
          'px-2 py-0.5 rounded text-[10px] font-medium transition-colors',
          activeFilter === f.value ? f.activeClass : 'bg-slate-800 text-slate-400 hover:bg-slate-700',
        ]"
      >{{ f.label }}</button>
    </div>

    <!-- Message stream -->
    <div ref="feedEl" class="flex-1 min-h-0 overflow-y-auto p-2 space-y-1.5">
      <TransitionGroup name="msg">
        <div
          v-for="msg in filtered" :key="msg._id"
          :class="['rounded-lg px-2.5 py-2 border text-[11px]', msgStyle(msg.msg_type)]"
        >
          <!-- Header row -->
          <div class="flex items-center gap-1.5 mb-0.5">
            <span class="text-sm leading-none">{{ msg.sender_icon }}</span>
            <span class="font-semibold text-slate-200">{{ msg.sender_display }}</span>
            <span class="text-slate-600">→</span>
            <span class="text-slate-400">{{ msg.receiver === 'all' ? 'everyone' : msg.receiver }}</span>
            <span :class="['ml-auto px-1.5 py-0.5 rounded text-[9px] font-bold uppercase', badgeClass(msg.msg_type)]">
              {{ msg.msg_type }}
            </span>
          </div>
          <!-- Content -->
          <p class="text-slate-300 leading-relaxed">{{ msg.content }}</p>
          <!-- Timestamp -->
          <p class="text-[9px] text-slate-600 mt-1">{{ formatTime(msg.ts) }}</p>
        </div>
      </TransitionGroup>

      <div v-if="filtered.length === 0" class="flex items-center justify-center h-24 text-slate-600 text-xs">
        No messages yet
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const store   = useSessionStore()
const feedEl  = ref(null)
const activeFilter = ref(null)

const FILTERS = [
  { value: 'alert',    label: '🚨 Alert',   activeClass: 'bg-red-900/60 text-red-300 border border-red-800' },
  { value: 'finding',  label: '🔍 Finding', activeClass: 'bg-amber-900/60 text-amber-300 border border-amber-800' },
  { value: 'decision', label: '✅ Decision', activeClass: 'bg-violet-900/60 text-violet-300 border border-violet-800' },
  { value: 'status',   label: '📡 Status',  activeClass: 'bg-slate-700 text-slate-300 border border-slate-600' },
  { value: 'summary',  label: '📋 Summary', activeClass: 'bg-emerald-900/60 text-emerald-300 border border-emerald-800' },
]

// Give each message a stable unique id for TransitionGroup
let _uid = 0
const messages = computed(() => {
  return store.agentMessages.map(m => ({ ...m, _id: m._id ?? (_uid++, _uid) }))
})

const filtered = computed(() => {
  if (!activeFilter.value) return messages.value
  return messages.value.filter(m => m.msg_type === activeFilter.value)
})

// Auto-scroll to bottom when new messages arrive
watch(filtered, async () => {
  await nextTick()
  if (feedEl.value) {
    feedEl.value.scrollTop = feedEl.value.scrollHeight
  }
})

function msgStyle(type) {
  return {
    alert:    'bg-red-950/40 border-red-900/60',
    finding:  'bg-amber-950/40 border-amber-900/60',
    decision: 'bg-violet-950/40 border-violet-900/60',
    status:   'bg-slate-800/60 border-slate-700/60',
    summary:  'bg-emerald-950/40 border-emerald-900/60',
    request:  'bg-cyan-950/40 border-cyan-900/60',
    entities: 'bg-indigo-950/40 border-indigo-900/60',
  }[type] || 'bg-slate-800/60 border-slate-700/60'
}

function badgeClass(type) {
  return {
    alert:    'bg-red-900/80 text-red-300',
    finding:  'bg-amber-900/80 text-amber-300',
    decision: 'bg-violet-900/80 text-violet-300',
    status:   'bg-slate-700 text-slate-400',
    summary:  'bg-emerald-900/80 text-emerald-300',
    request:  'bg-cyan-900/80 text-cyan-300',
    entities: 'bg-indigo-900/80 text-indigo-300',
  }[type] || 'bg-slate-700 text-slate-400'
}

function formatTime(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}
</script>

<style scoped>
.msg-enter-active { transition: all 0.25s ease; }
.msg-enter-from   { opacity: 0; transform: translateY(-6px); }
.msg-leave-active { transition: opacity 0.15s ease; }
.msg-leave-to     { opacity: 0; }
</style>
