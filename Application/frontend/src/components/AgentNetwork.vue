<template>
  <div class="h-full flex flex-col bg-slate-950">
    <div class="px-3 py-2 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
      <p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">Agent Network</p>
      <span class="text-[10px] text-slate-600">{{ agentCount }} agents · {{ edgeCount }} comms</span>
    </div>
    <div ref="containerEl" class="flex-1 min-h-0 relative" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const store       = useSessionStore()
const containerEl = ref(null)

let network    = null
let nodesDS    = null
let edgesDS    = null
let _ro        = null
let _fitted    = false
let _edgeUid   = 0

// Map each known agent to a color
const AGENT_COLOR = {
  pilot:      { background: '#4c1d95', border: '#7c3aed', font: '#ddd6fe' },
  navigator:  { background: '#0c4a6e', border: '#0ea5e9', font: '#bae6fd' },
  engineer:   { background: '#064e3b', border: '#10b981', font: '#a7f3d0' },
  conflict:   { background: '#7f1d1d', border: '#ef4444', font: '#fca5a5' },
  synthesizer:{ background: '#1e1b4b', border: '#818cf8', font: '#c7d2fe' },
  user:       { background: '#1c1917', border: '#78716c', font: '#e7e5e0' },
  system:     { background: '#1e293b', border: '#64748b', font: '#cbd5e1' },
}

const DEFAULT_COLOR = { background: '#1e293b', border: '#475569', font: '#94a3b8' }

const agentCount = computed(() => nodesDS ? nodesDS.length : 0)
const edgeCount  = computed(() => edgesDS  ? edgesDS.length  : 0)

function getOrCreateNode(sender, display, icon) {
  if (!nodesDS) return
  if (!nodesDS.get(sender)) {
    const c = AGENT_COLOR[sender] || DEFAULT_COLOR
    nodesDS.add({
      id:    sender,
      label: `${icon}\n${display}`,
      color: { background: c.background, border: c.border, highlight: { background: c.border, border: '#fff' } },
      font:  { color: c.font, size: 11, face: 'monospace', multi: true },
      shape: 'box',
      margin: 8,
      borderWidth: 1.5,
    })
  }
}

function addEdge(msg) {
  if (!edgesDS || !msg.sender || !msg.receiver) return
  const target = msg.receiver === 'all' ? '__broadcast__' : msg.receiver

  // Ensure broadcast node exists
  if (msg.receiver === 'all' && !nodesDS.get('__broadcast__')) {
    nodesDS.add({
      id: '__broadcast__', label: '📡\nAll',
      color: { background: '#0f172a', border: '#334155' },
      font: { color: '#64748b', size: 10, face: 'monospace', multi: true },
      shape: 'ellipse',
      margin: 6,
    })
  }

  const edgeColor = {
    alert:    '#ef4444',
    finding:  '#f59e0b',
    decision: '#8b5cf6',
    summary:  '#10b981',
    status:   '#64748b',
    request:  '#06b6d4',
    entities: '#6366f1',
  }[msg.msg_type] || '#475569'

  _edgeUid++
  edgesDS.add({
    id:     `e${_edgeUid}`,
    from:   msg.sender,
    to:     target,
    arrows: 'to',
    color:  { color: edgeColor, highlight: '#fff', opacity: 0.8 },
    width:  1.5,
    smooth: { type: 'curvedCW', roundness: 0.2 },
    label:  msg.msg_type,
    font:   { color: edgeColor, size: 9, face: 'monospace', strokeWidth: 0 },
    title:  msg.content?.slice(0, 120),
  })

  // Flash the source node
  const node = nodesDS.get(msg.sender)
  if (node) {
    const c = AGENT_COLOR[msg.sender] || DEFAULT_COLOR
    nodesDS.update({ id: msg.sender, color: { background: '#fff', border: c.border } })
    setTimeout(() => {
      if (nodesDS?.get(msg.sender)) {
        nodesDS.update({ id: msg.sender, color: { background: c.background, border: c.border } })
      }
    }, 400)
  }
}

function initNetwork() {
  if (!containerEl.value || network) return

  nodesDS = new DataSet([])
  edgesDS = new DataSet([])

  const options = {
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -60, springLength: 120, springConstant: 0.04 },
      stabilization: { iterations: 80 },
    },
    interaction: { dragNodes: true, zoomView: true, tooltipDelay: 200 },
    layout: { improvedLayout: true },
    edges: { smooth: { enabled: true, type: 'dynamic' } },
    nodes: { borderWidthSelected: 2.5 },
  }

  network = new Network(containerEl.value, { nodes: nodesDS, edges: edgesDS }, options)

  // ResizeObserver to handle flex layout resolution
  _ro = new ResizeObserver((entries) => {
    const { width, height } = entries[0].contentRect
    if (width > 10 && height > 10 && !_fitted) {
      _fitted = true
      network.redraw()
      network.fit()
    }
  })
  _ro.observe(containerEl.value)

  // Seed existing messages
  for (const msg of store.agentMessages) {
    getOrCreateNode(msg.sender, msg.sender_display, msg.sender_icon)
    addEdge(msg)
  }
}

// Watch for new messages
watch(() => store.agentMessages.length, (newLen, oldLen) => {
  if (!network) return
  for (let i = oldLen; i < newLen; i++) {
    const msg = store.agentMessages[i]
    if (!msg) continue
    getOrCreateNode(msg.sender, msg.sender_display, msg.sender_icon)
    if (msg.receiver !== 'all' && msg.receiver) {
      // Ensure receiver node exists too (may not have been seen yet)
      getOrCreateNode(msg.receiver, msg.receiver, '🤖')
    }
    addEdge(msg)
  }
})

onMounted(() => {
  initNetwork()
})

onUnmounted(() => {
  _ro?.disconnect()
  network?.destroy()
  network = null
  nodesDS = null
  edgesDS = null
})
</script>
