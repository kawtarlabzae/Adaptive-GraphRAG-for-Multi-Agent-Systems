<template>
  <div class="h-full flex flex-col bg-slate-900 text-slate-100">
    <!-- Header -->
    <div class="flex-shrink-0 px-5 py-3 border-b border-slate-800">
      <p class="text-sm font-semibold text-slate-100">Knowledge Chat</p>
      <p class="text-xs text-slate-400">Query the knowledge graph with natural language</p>
    </div>

    <!-- Messages -->
    <div ref="scrollEl" class="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
      <!-- Empty state -->
      <div v-if="store.chatMessages.length === 0" class="h-full flex items-center justify-center">
        <div class="text-center text-slate-600 px-6">
          <div class="text-4xl mb-3">💬</div>
          <p class="text-sm font-medium text-slate-400 mb-1">Ask anything about the documents</p>
          <p class="text-xs text-slate-600">Your agents have built a knowledge graph — query it here.</p>
        </div>
      </div>

      <TransitionGroup name="msg" tag="div" class="space-y-4">
        <div v-for="(msg, i) in store.chatMessages" :key="i">
          <!-- User bubble -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[80%] bg-violet-600/80 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm">
              {{ msg.content }}
              <p class="text-violet-300 text-[10px] mt-1 text-right">{{ msg.ts }}</p>
            </div>
          </div>

          <!-- Assistant bubble -->
          <div v-else class="space-y-2">
            <div class="max-w-[90%] bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-md px-4 py-3 text-sm">
              <!-- Error -->
              <div v-if="msg.error" class="text-red-400 text-sm">
                <span class="font-medium">Error:</span> {{ msg.error }}
              </div>
              <!-- Answer -->
              <template v-else>
                <p class="text-slate-100 leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>

                <!-- Confidence -->
                <div v-if="msg.confidence" class="mt-2 flex items-center gap-2">
                  <div class="h-1.5 flex-1 bg-slate-700 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all"
                         :class="msg.confidence > 0.7 ? 'bg-emerald-500' : msg.confidence > 0.4 ? 'bg-amber-500' : 'bg-red-500'"
                         :style="{ width: `${(msg.confidence * 100).toFixed(0)}%` }" />
                  </div>
                  <span class="text-xs text-slate-400 flex-shrink-0">{{ (msg.confidence * 100).toFixed(0) }}% conf.</span>
                </div>

                <!-- Reasoning chain -->
                <details v-if="msg.reasoning_chain?.length" class="mt-3">
                  <summary class="text-xs text-slate-400 hover:text-slate-200 cursor-pointer select-none">
                    🔗 Reasoning chain ({{ msg.reasoning_chain.length }} step{{ msg.reasoning_chain.length !== 1 ? 's' : '' }})
                  </summary>
                  <ol class="mt-2 space-y-1 pl-3 border-l border-slate-700">
                    <li v-for="(step, si) in msg.reasoning_chain" :key="si"
                        class="text-xs text-slate-400 leading-relaxed">
                      <span class="text-slate-500 mr-1">{{ si + 1 }}.</span>{{ step }}
                    </li>
                  </ol>
                </details>

                <!-- Retrieved nodes -->
                <details v-if="msg.nodes_used?.length" class="mt-2">
                  <summary class="text-xs text-slate-400 hover:text-slate-200 cursor-pointer select-none">
                    ⬡ Graph nodes used ({{ msg.nodes_used.length }})
                  </summary>
                  <div class="mt-2 flex flex-wrap gap-1.5">
                    <span v-for="node in msg.nodes_used" :key="node.id"
                          class="inline-flex items-center gap-1 bg-slate-700/60 border border-slate-600 rounded-md px-2 py-0.5 text-[10px] text-slate-300">
                      <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: nodeColor(node.type) }" />
                      {{ node.label }}
                    </span>
                  </div>
                </details>
              </template>

              <p class="text-slate-500 text-[10px] mt-2">{{ msg.ts }}</p>
            </div>
          </div>
        </div>
      </TransitionGroup>

      <!-- Typing indicator -->
      <div v-if="sending" class="flex gap-2 items-center text-xs text-slate-500 pl-1">
        <span class="flex gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:0ms" />
          <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:150ms" />
          <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:300ms" />
        </span>
        Querying knowledge graph…
      </div>
    </div>

    <!-- Input -->
    <div class="flex-shrink-0 p-4 border-t border-slate-800">
      <form @submit.prevent="sendMessage" class="flex gap-2">
        <input
          v-model="input"
          :disabled="sending"
          placeholder="Ask about the documents…"
          class="flex-1 min-w-0 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500
                 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 disabled:opacity-50 transition"
        />
        <button type="submit" :disabled="sending || !input.trim()"
                class="px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed
                       text-sm font-medium text-white transition-colors flex-shrink-0">
          Send
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'

const props = defineProps({ sessionId: { type: String, required: true } })

const store = useSessionStore()
const input = ref('')
const sending = ref(false)
const scrollEl = ref(null)

watch(store.chatMessages, async () => {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}, { deep: true })

async function sendMessage() {
  const msg = input.value.trim()
  if (!msg || sending.value) return
  input.value = ''
  sending.value = true
  try {
    await store.sendChat(props.sessionId, msg)
  } finally {
    sending.value = false
    await nextTick()
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  }
}

const NODE_COLORS = {
  concept: '#8b5cf6', process: '#06b6d4', variable: '#f59e0b',
  entity: '#10b981', metric: '#ef4444',
}
function nodeColor(type) { return NODE_COLORS[type] || '#64748b' }
</script>

<style scoped>
.msg-enter-active { transition: all 0.25s ease; }
.msg-enter-from   { opacity: 0; transform: translateY(8px); }
</style>
