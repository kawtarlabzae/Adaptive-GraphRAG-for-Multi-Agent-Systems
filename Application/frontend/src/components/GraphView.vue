<template>
  <div class="relative w-full h-full bg-slate-50 overflow-hidden">
    <!-- Toolbar -->
    <div class="absolute top-3 left-3 z-10 flex items-center gap-2">
      <div class="bg-white/90 backdrop-blur-sm rounded-xl shadow-sm border border-slate-200 px-3 py-2 flex items-center gap-3 text-xs text-slate-600">
        <span class="font-semibold text-brand-600">{{ nodes.length }}</span> nodes ·
        <span class="font-semibold text-cyan-600">{{ edges.length }}</span> edges
        <div v-if="stabilizing" class="flex items-center gap-1.5 ml-1 text-amber-600">
          <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> Stabilising…
        </div>
      </div>
      <button @click="fitGraph" class="bg-white/90 backdrop-blur-sm rounded-xl shadow-sm border border-slate-200 p-2 text-slate-500 hover:text-brand-600 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
      </button>
    </div>

    <!-- Legend -->
    <div class="absolute top-3 right-3 z-10 bg-white/90 backdrop-blur-sm rounded-xl shadow-sm border border-slate-200 p-3">
      <p class="text-xs font-semibold text-slate-500 mb-2">Node Types</p>
      <div class="space-y-1">
        <div v-for="t in nodeTypes" :key="t.type" class="flex items-center gap-2 text-xs text-slate-600">
          <span class="w-3 h-3 rounded-full flex-shrink-0" :style="{ background: t.color }"></span>
          {{ t.label }}
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="nodes.length === 0" class="absolute inset-0 flex items-center justify-center">
      <div class="text-center text-slate-300">
        <div class="text-6xl mb-3">⬡</div>
        <p class="text-lg font-semibold">Knowledge Graph</p>
        <p class="text-sm">Start a session to watch the graph grow in real-time</p>
      </div>
    </div>

    <!-- Graph container -->
    <div ref="container" class="w-full h-full" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
})

const container = ref(null)
const stabilizing = ref(false)
let network = null
let visNodes = null
let visEdges = null
let _resizeObserver = null

const NODE_COLORS = {
  molecule:             { background: '#818cf8', border: '#4f46e5', hover: '#6366f1' },
  process:              { background: '#34d399', border: '#059669', hover: '#10b981' },
  variable:             { background: '#fbbf24', border: '#d97706', hover: '#f59e0b' },
  condition:            { background: '#c084fc', border: '#9333ea', hover: '#a855f7' },
  technology:           { background: '#60a5fa', border: '#2563eb', hover: '#3b82f6' },
  biological_component: { background: '#4ade80', border: '#16a34a', hover: '#22c55e' },
  metric:               { background: '#f87171', border: '#dc2626', hover: '#ef4444' },
  entity:               { background: '#94a3b8', border: '#64748b', hover: '#78909c' },
}

const EDGE_COLORS = {
  AFFECTS:       '#94a3b8',
  CAUSES:        '#f87171',
  REQUIRES:      '#60a5fa',
  PROMOTES:      '#34d399',
  INHIBITS:      '#fbbf24',
  CONTROLS:      '#a78bfa',
  PRODUCES:      '#4ade80',
  DETERMINES:    '#fb923c',
  INCREASES_WITH:'#67e8f9',
  INDUCES:       '#f472b6',
}

const nodeTypes = [
  { type: 'molecule',   label: 'Molecule',    color: '#818cf8' },
  { type: 'process',    label: 'Process',     color: '#34d399' },
  { type: 'variable',   label: 'Variable',    color: '#fbbf24' },
  { type: 'condition',  label: 'Condition',   color: '#c084fc' },
  { type: 'technology', label: 'Technology',  color: '#60a5fa' },
  { type: 'metric',     label: 'Metric',      color: '#f87171' },
  { type: 'entity',     label: 'Entity',      color: '#94a3b8' },
]

function toVisNode(n) {
  const colors = NODE_COLORS[n.type] || NODE_COLORS.entity
  return {
    id: n.id,
    label: n.label,
    title: `<b>${n.label}</b><br>${n.description || ''}${n.type ? `<br><i>${n.type}</i>` : ''}`,
    color: colors,
    size: 14 + (n.confidence || 1) * 6,
    font: { color: '#1e293b', size: 12, face: 'Inter, sans-serif' },
    borderWidth: 2,
    shadow: { enabled: true, size: 5, color: 'rgba(0,0,0,0.08)' },
  }
}

function toVisEdge(e) {
  const color = EDGE_COLORS[e.type] || '#94a3b8'
  return {
    id: e.id,
    from: e.from_node,
    to: e.to_node,
    label: e.type,
    title: e.condition ? `${e.type} (${e.condition})` : e.type,
    color: { color, highlight: color, hover: color, opacity: e.is_hard_edge ? 1.0 : 0.75 },
    width: e.is_hard_edge ? 3 : 1.5 + (e.weight || 1) * 1.5,
    dashes: !e.is_hard_edge,
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
    smooth: { type: 'cubicBezier', forceDirection: 'none', roundness: 0.5 },
    font: { size: 9, color: '#64748b', align: 'middle', background: 'rgba(255,255,255,0.8)' },
  }
}

function initNetwork() {
  if (!container.value) return
  visNodes = new DataSet([])
  visEdges = new DataSet([])

  const options = {
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -60,
        centralGravity: 0.005,
        springLength: 160,
        springConstant: 0.05,
        damping: 0.4,
        avoidOverlap: 0.8,
      },
      stabilization: { iterations: 200, fit: true, updateInterval: 25 },
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      navigationButtons: false,
      keyboard: false,
    },
    nodes: { borderWidth: 2 },
    edges: { selectionWidth: 3 },
  }

  network = new Network(container.value, { nodes: visNodes, edges: visEdges }, options)

  network.on('stabilizationProgress', () => { stabilizing.value = true })
  network.on('stabilizationIterationsDone', () => { stabilizing.value = false })
  network.on('stabilized', () => { stabilizing.value = false })
}

function fitGraph() {
  network?.fit({ animation: { duration: 800, easingFunction: 'easeInOutQuad' } })
}

// Watch for new nodes
watch(() => props.nodes, (newNodes) => {
  if (!visNodes) return
  const currentIds = new Set(visNodes.getIds())
  newNodes.forEach(n => {
    if (!currentIds.has(n.id)) visNodes.add(toVisNode(n))
    else visNodes.update(toVisNode(n))
  })
  // Remove deleted nodes
  currentIds.forEach(id => {
    if (!newNodes.find(n => n.id === id)) visNodes.remove(id)
  })
}, { deep: true })

// Watch for new edges
watch(() => props.edges, (newEdges) => {
  if (!visEdges) return
  const currentIds = new Set(visEdges.getIds())
  newEdges.forEach(e => {
    if (!currentIds.has(e.id)) {
      try { visEdges.add(toVisEdge(e)) } catch { /* skip invalid */ }
    }
  })
  currentIds.forEach(id => {
    if (!newEdges.find(e => e.id === id)) visEdges.remove(id)
  })
}, { deep: true })

onMounted(async () => {
  await nextTick()
  initNetwork()

  // Seed initial data
  if (props.nodes.length) visNodes.add(props.nodes.map(toVisNode))
  if (props.edges.length) props.edges.forEach(e => { try { visEdges.add(toVisEdge(e)) } catch {} })

  // ResizeObserver: vis-network initialises into a 0×0 canvas when the
  // parent is a flex item whose dimensions aren't resolved yet at mount time.
  // Whenever the container gets real pixel dimensions we redraw + fit.
  if (container.value && typeof ResizeObserver !== 'undefined') {
    let _fitted = false
    _resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      if (width > 0 && height > 0 && network) {
        network.redraw()
        if (!_fitted) { network.fit(); _fitted = true }
      }
    })
    _resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  _resizeObserver?.disconnect()
  network?.destroy()
})
</script>
