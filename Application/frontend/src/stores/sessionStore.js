import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api/client'

const WS_BASE = `ws://${window.location.hostname}:8000`

export const useSessionStore = defineStore('session', () => {
  // ── State ───────────────────────────────────────────────────────────
  const sessions   = ref([])
  const current    = ref(null)   // active Session object
  const events     = ref([])     // all received events for current session
  const graph      = ref({ nodes: [], edges: [] })
  const agentCards = ref([])
  const metrics    = ref({
    logical_chain_accuracy: 0,
    context_efficiency: 0,
    hallucination_rate: 0,
    total_nodes: 0,
    total_edges: 0,
    pruned_nodes: 0,
    conflicts_detected: 0,
    scenarios_passed: 0,
  })
  const omniverseState  = ref(null)
  const omniverseLog    = ref([])
  const omniverseCommands = ref([])
  const phaseStatus     = ref({ current: 0, phase1: 'pending', phase2: 'pending' })
  const systemStatus    = ref({ neo4j: '…', ollama: '…', omniverse: '…' })

  // ── Custom domain state ──────────────────────────────────────────────
  const agentOutputs   = ref({})   // { agentName: [{ type, data, ts }, ...] }
  const chatMessages   = ref([])   // [{ role, content, reasoning_chain, nodes_used, confidence, ts, error }]
  const aeroChatMessages = ref([]) // same structure but for aviation pilot chat
  const agentMessages  = ref([])   // all agent.message bus events (inter-agent comms)
  const phase1Waiting  = ref(false) // true when phase.waiting received
  const phase2Ready    = ref(false) // true when phase2.ready received

  // ── Aviation state ───────────────────────────────────────────────────
  const flightState     = ref(null)   // latest AircraftState dict
  const trajectory      = ref([])     // [{lat, lon, alt_ft}]
  const waypoints       = ref([])     // [{id, lat, lon}]
  const pressureEvents  = ref([])     // [{tick, delta, f_predicted, f_actual, latency_ms}]
  const fuelHistory     = ref([])     // [{tick, f_predicted, f_actual}]
  const pilotCommands   = ref([])     // last N pilot commands
  const flightKpis      = ref({ fuel_efficiency: null, knowledge_latency_ms: null, context_utility: null })

  let _ws = null
  let _reconnectTimer = null

  // ── Getters ──────────────────────────────────────────────────────────
  const sessionStatus = computed(() => current.value?.status ?? 'idle')
  const isRunning     = computed(() => sessionStatus.value === 'running')
  const isCompleted   = computed(() => sessionStatus.value === 'completed')

  // ── Actions ──────────────────────────────────────────────────────────

  async function fetchStatus() {
    try {
      const { data } = await api.getStatus()
      systemStatus.value = data
    } catch { /* ignore */ }
  }

  async function fetchSessions() {
    try {
      const { data } = await api.listSessions()
      sessions.value = data
    } catch { /* ignore */ }
  }

  async function createSession(config) {
    const { data } = await api.createSession(config)
    sessions.value.unshift(data)
    return data
  }

  async function deleteSession(id) {
    await api.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (current.value?.id === id) {
      current.value = null
      disconnectWs()
    }
  }

  async function loadSession(id) {
    const { data } = await api.getSession(id)
    current.value = data
    agentCards.value = data.agents || []
    events.value = data.events || []
    // Load graph state
    try {
      const gData = await api.getGraph(id)
      graph.value.nodes = gData.data.nodes || []
      graph.value.edges = gData.data.edges || []
    } catch { /* ignore */ }
    return data
  }

  async function uploadFile(sessionId, file) {
    const { data } = await api.uploadFile(sessionId, file)
    if (current.value?.id === sessionId) {
      if (!current.value.files) current.value.files = []
      if (!current.value.files.includes(data.filename))
        current.value.files.push(data.filename)
    }
    return data
  }

  async function removeFile(sessionId, filename) {
    await api.removeFile(sessionId, filename)
    if (current.value?.id === sessionId)
      current.value.files = current.value.files.filter(f => f !== filename)
  }

  async function startSession(id) {
    await api.startSession(id)
    if (current.value?.id === id) current.value.status = 'running'
    connectWs(id)
  }

  async function stopSession(id) {
    await api.stopSession(id)
    if (current.value?.id === id) current.value.status = 'stopped'
    disconnectWs()
  }

  // ── WebSocket ─────────────────────────────────────────────────────────

  function connectWs(sessionId) {
    disconnectWs()
    _ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`)

    _ws.onopen = () => console.log('[WS] connected', sessionId)

    _ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        if (event.type === 'ping') return
        handleEvent(event)
      } catch { /* ignore malformed */ }
    }

    _ws.onerror = (e) => console.warn('[WS] error', e)

    _ws.onclose = () => {
      console.log('[WS] closed')
      if (current.value?.status === 'running') {
        _reconnectTimer = setTimeout(() => connectWs(sessionId), 3000)
      }
    }
  }

  function disconnectWs() {
    clearTimeout(_reconnectTimer)
    if (_ws) { _ws.close(); _ws = null }
  }

  // ── Event Handler ────────────────────────────────────────────────────

  function handleEvent(event) {
    const { type, data, agent: agentName } = event

    // Append to event log (limit to 300)
    events.value.push(event)
    if (events.value.length > 300) events.value.shift()

    // ── Per-agent output capture (for GeneralSessionView) ──
    if (agentName && ['agent.thinking', 'agent.output', 'agent.node_added',
                       'agent.edge_added', 'agent.started', 'agent.completed',
                       'agent.error'].includes(type)) {
      if (!agentOutputs.value[agentName]) agentOutputs.value[agentName] = []
      agentOutputs.value[agentName].push({ type, data, ts: event.timestamp || new Date().toISOString() })
      if (agentOutputs.value[agentName].length > 300)
        agentOutputs.value[agentName].shift()
    }

    // ── Agent state ──
    if (agentName && type.startsWith('agent.')) {
      const card = agentCards.value.find(a => a.name === agentName)
      if (card) {
        if (type === 'agent.started')   { card.status = 'active';    card.task = data?.message || '' }
        if (type === 'agent.thinking')  { card.status = 'thinking';  card.task = data?.thought || '' }
        if (type === 'agent.progress')  { card.status = 'active';    card.progress = data?.progress || 0; card.task = data?.task || '' }
        if (type === 'agent.completed') {
          card.status = 'completed'; card.progress = 1
          if (data?.stats) card.stats = { ...card.stats, ...data.stats }
        }
        if (type === 'agent.error')     card.status = 'error'
      }
    }

    // ── Graph updates ──
    if (type === 'agent.node_added' && data?.node) {
      const n = data.node
      if (!graph.value.nodes.find(x => x.id === n.id))
        graph.value.nodes.push(n)
      metrics.value.total_nodes = graph.value.nodes.length
    }

    if (type === 'agent.edge_added' && data?.edge) {
      const e = data.edge
      if (!graph.value.edges.find(x => x.id === e.id))
        graph.value.edges.push(e)
      metrics.value.total_edges = graph.value.edges.length
    }

    if (type === 'agent.node_pruned' && data?.node_id) {
      graph.value.nodes = graph.value.nodes.filter(n => n.id !== data.node_id)
      graph.value.edges = graph.value.edges.filter(
        e => e.from_node !== data.node_id && e.to_node !== data.node_id
      )
      metrics.value.pruned_nodes = (metrics.value.pruned_nodes || 0) + 1
    }

    // ── Research agent role negotiation result ──
    if (type === 'agent.role_assigned' && data) {
      const card = agentCards.value.find(a => a.name === data.agent)
      if (card) {
        card.focus = data.focus
        card.task  = `Focus: ${data.focus}`
      }
    }

    // ── Agent message bus (inter-agent communications) ──
    if (type === 'agent.message' && data) {
      agentMessages.value.push(data)
      if (agentMessages.value.length > 500) agentMessages.value.shift()
    }

    // ── Phase tracking ──
    if (type === 'phase.started') {
      phaseStatus.value.current = data?.phase
      if (data?.phase === 1) phaseStatus.value.phase1 = 'running'
      if (data?.phase === 2) phaseStatus.value.phase2 = 'running'
    }
    if (type === 'phase.completed') {
      if (data?.phase === 1) phaseStatus.value.phase1 = 'completed'
      if (data?.phase === 2) phaseStatus.value.phase2 = 'completed'
    }
    if (type === 'phase.waiting') phase1Waiting.value = true
    if (type === 'phase2.ready')  { phase2Ready.value = true; phase1Waiting.value = false }

    // ── Omniverse ──
    if (type === 'omniverse.sensor_update' && data?.state) {
      omniverseState.value = data.state
    }
    if (type === 'omniverse.started') {
      omniverseLog.value.push({ ts: now(), msg: data?.message || 'Omniverse started', type: 'info' })
    }
    if (type === 'omniverse.command_applied') {
      omniverseCommands.value.unshift({ ts: now(), ...data?.command, result: data?.result })
      if (omniverseCommands.value.length > 20) omniverseCommands.value.pop()
      if (data?.result?.usd_update)
        omniverseLog.value.push({ ts: now(), msg: data.result.usd_update, type: 'usd' })
    }
    if (type === 'omniverse.llm_command') {
      const cmd = data?.command
      if (cmd) {
        omniverseCommands.value.unshift({
          ts: now(),
          command: cmd.command,
          parameters: cmd.parameters,
          predicted_outcome: cmd.predicted_outcome,
          confidence: cmd.confidence,
          source: 'LLM→Graph',
        })
        omniverseLog.value.push({
          ts: now(),
          msg: `LLM→ ${cmd.command}: ${cmd.parameters?.reason || ''}`,
          type: 'command',
        })
      }
    }
    if (type === 'omniverse.completed') {
      omniverseLog.value.push({ ts: now(), msg: 'Simulation loop completed.', type: 'success' })
    }

    // ── Final metrics ──
    if (type === 'session.completed' && data?.metrics) {
      metrics.value = { ...metrics.value, ...data.metrics }
      if (current.value) current.value.status = 'completed'
    }
    if (type === 'session.error') {
      if (current.value) current.value.status = 'error'
    }

    // ── Conflict ──
    if (type === 'agent.conflict_found') {
      metrics.value.conflicts_detected = (metrics.value.conflicts_detected || 0) + 1
    }

    // ── Aviation ──────────────────────────────────────────────────────
    if (type === 'flight.started') {
      if (data?.waypoints) waypoints.value = data.waypoints
    }

    if (type === 'flight.state_update' && data) {
      // data IS the state dict (flat, no nesting)
      flightState.value = data
      trajectory.value.push({ lat: data.lat, lon: data.lon, alt_ft: data.alt_ft })
      if (trajectory.value.length > 500) trajectory.value.shift()
      if (data.tick != null) {
        fuelHistory.value.push({
          tick: data.tick,
          f_predicted: data.fuel_predicted ?? data.fuel_kg,
          f_actual: data.fuel_kg,
        })
        if (fuelHistory.value.length > 200) fuelHistory.value.shift()
      }
    }

    if (type === 'flight.pilot_command' && data?.command) {
      pilotCommands.value.unshift({ ts: now(), ...data.command, subgraph_size: data.subgraph_size })
      if (pilotCommands.value.length > 30) pilotCommands.value.pop()
    }

    if (type === 'flight.pressure_signal' && data?.pressure) {
      const p = data.pressure
      pressureEvents.value.push({
        tick: data.tick ?? p.tick,
        delta: p.pressure_delta,
        f_predicted: p.f_predicted,
        f_actual: p.f_actual,
        latency_ms: p.knowledge_latency_ms,
      })
      if (p.knowledge_latency_ms != null)
        flightKpis.value.knowledge_latency_ms = p.knowledge_latency_ms
    }

    if (type === 'flight.arrived' && data) {
      // compute a simple fuel efficiency metric
      const fuelUsed = data.fuel_used_kg || 0
      const dist = data.distance_flown_nm || 1
      flightKpis.value.fuel_efficiency = Math.min(1, (dist / fuelUsed) * 10)
    }

    if (type === 'agent.waypoint_planned' && data?.waypoints) {
      waypoints.value = data.waypoints
    }
  }

  function reset() {
    disconnectWs()
    current.value = null
    events.value = []
    graph.value = { nodes: [], edges: [] }
    agentCards.value = []
    omniverseState.value = null
    omniverseLog.value = []
    omniverseCommands.value = []
    phaseStatus.value = { current: 0, phase1: 'pending', phase2: 'pending' }
    metrics.value = {
      logical_chain_accuracy: 0, context_efficiency: 0, hallucination_rate: 0,
      total_nodes: 0, total_edges: 0, pruned_nodes: 0,
      conflicts_detected: 0, scenarios_passed: 0,
    }
    // aviation
    flightState.value = null
    trajectory.value = []
    waypoints.value = []
    pressureEvents.value = []
    fuelHistory.value = []
    pilotCommands.value = []
    flightKpis.value = { fuel_efficiency: null, knowledge_latency_ms: null, context_utility: null }
    // custom domain
    agentOutputs.value = {}
    chatMessages.value = []
    aeroChatMessages.value = []
    agentMessages.value = []
    phase1Waiting.value = false
    phase2Ready.value = false
  }

  async function advancePhase(id) {
    await api.advancePhase(id)
    phase1Waiting.value = false
  }

  async function sendChat(id, message) {
    chatMessages.value.push({ role: 'user', content: message, ts: now() })
    try {
      const { data } = await api.chatQuery(id, message)
      chatMessages.value.push({
        role: 'assistant',
        content: data.answer || '',
        reasoning_chain: data.reasoning_chain || [],
        nodes_used: data.nodes_used || [],
        confidence: data.confidence || 0,
        ts: now(),
        error: data.error || null,
      })
    } catch (e) {
      chatMessages.value.push({
        role: 'assistant',
        content: '',
        error: e.message || 'Request failed',
        ts: now(),
      })
    }
  }

  async function sendAeroChat(id, message) {
    aeroChatMessages.value.push({ role: 'user', content: message, ts: now() })
    try {
      const { data } = await api.aeroChatQuery(id, message)
      aeroChatMessages.value.push({
        role: 'assistant',
        content: data.answer || '',
        reasoning_chain: data.reasoning_chain || [],
        nodes_used: data.nodes_used || [],
        confidence: data.confidence || 0,
        ts: now(),
        error: data.error || null,
      })
    } catch (e) {
      aeroChatMessages.value.push({
        role: 'assistant',
        content: '',
        error: e.message || 'Request failed',
        ts: now(),
      })
    }
  }

  return {
    sessions, current, events, graph, agentCards, metrics,
    omniverseState, omniverseLog, omniverseCommands,
    phaseStatus, systemStatus,
    // aviation
    flightState, trajectory, waypoints, pressureEvents, fuelHistory, pilotCommands, flightKpis,
    // custom domain
    agentOutputs, chatMessages, aeroChatMessages, agentMessages, phase1Waiting, phase2Ready,
    sessionStatus, isRunning, isCompleted,
    fetchStatus, fetchSessions,
    createSession, deleteSession, loadSession,
    uploadFile, removeFile,
    startSession, stopSession,
    connectWs, disconnectWs,
    advancePhase, sendChat, sendAeroChat,
    reset,
  }
})

function now() {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}
