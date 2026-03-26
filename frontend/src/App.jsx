import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

/** Node colours by entity type. */
const NODE_COLORS = {
  Customer:     '#4466ff',
  SalesOrder:   '#4488ff',
  Delivery:     '#5599ff',
  BillingDoc:   '#ff4488',
  JournalEntry: '#aa66ff',
  Payment:      '#44cc88',
  Product:      '#ff77aa',
}

/** Node sizes by entity type. */
const NODE_SIZES = {
  Customer: 10,
  SalesOrder: 7,
  Delivery: 6,
  BillingDoc: 6,
  JournalEntry: 5,
  Payment: 5,
  Product: 4,
}

/** Lower-detail node types that can be toggled off for a cleaner view. */
const GRANULAR_TYPES = new Set(['JournalEntry', 'Payment', 'Product'])

/** Hidden keys when inspecting a node. */
const INSPECTOR_HIDDEN_KEYS = new Set([
  'x', 'y', 'vx', 'vy', 'fx', 'fy',
  'index', '__indexColor', 'nodeType', 'label', 'type',
])

function getSessionId() {
  let id = sessionStorage.getItem('o2c_session')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('o2c_session', id)
  }
  return id
}

/** Render minimal markdown bold syntax. */
function renderMarkdown(text) {
  return text?.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || ''
}

// =========================================================================
// Main application component
// =========================================================================

export default function App() {
  const graphRef = useRef(null)
  const chatEndRef = useRef(null)
  const sessionId = useMemo(() => getSessionId(), [])

  // --- State ---------------------------------------------------------------
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [highlightLinks, setHighlightLinks] = useState(new Set())
  const [minimized, setMinimized] = useState(false)
  const [showGranular, setShowGranular] = useState(true)

  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: 'Hi! I can help you analyze the **Order to Cash** process. Ask me anything about customers, orders, deliveries, invoices, or payments.',
  }])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  // --- Data fetching -------------------------------------------------------
  useEffect(() => {
    fetch(`${API_BASE}/graph`)
      .then(r => r.json())
      .then(data => {
        setGraphData({
          nodes: (data.nodes || []).map(n => ({ ...n, nodeType: n.type })),
          links: (data.edges || []).map(e => ({
            source: e.source, target: e.target, relation: e.relation,
          })),
        })
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Auto-scroll chat to latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Configure forces and zoom-to-fit after initial load
  useEffect(() => {
    if (!loading && graphRef.current && graphData.nodes.length > 0) {
      const fg = graphRef.current
      fg.d3Force('charge').strength(-120).distanceMax(400)
      fg.d3Force('link').distance(80)
      fg.d3Force('center').strength(0.05)
      fg.d3ReheatSimulation()
      setTimeout(() => fg.zoomToFit(400, 80), 1500)
    }
  }, [loading, graphData])

  // --- Interactions --------------------------------------------------------
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
    const nodeIds = new Set([node.id])
    const linkIds = new Set()
    graphData.links.forEach((l, i) => {
      const s = typeof l.source === 'object' ? l.source.id : l.source
      const t = typeof l.target === 'object' ? l.target.id : l.target
      if (s === node.id || t === node.id) {
        nodeIds.add(s)
        nodeIds.add(t)
        linkIds.add(i)
      }
    })
    setHighlightNodes(nodeIds)
    setHighlightLinks(linkIds)
  }, [graphData])

  const clearSelection = useCallback(() => {
    setSelectedNode(null)
    setHighlightNodes(new Set())
    setHighlightLinks(new Set())
  }, [])

  /** Highlight graph nodes that match query results. */
  const highlightQueryResults = useCallback((results) => {
    if (!results?.length || !graphRef.current) return
    const ids = new Set()
    results.forEach(row => {
      Object.values(row).forEach(val => {
        if (val == null) return
        const v = String(val)
        graphData.nodes.forEach(n => {
          if (n.id === v || n.id?.includes(v)) ids.add(n.id)
        })
      })
    })
    if (ids.size > 0) {
      const linkIds = new Set()
      graphData.links.forEach((l, i) => {
        const s = typeof l.source === 'object' ? l.source.id : l.source
        const t = typeof l.target === 'object' ? l.target.id : l.target
        if (ids.has(s) || ids.has(t)) {
          ids.add(s)
          ids.add(t)
          linkIds.add(i)
        }
      })
      setHighlightNodes(ids)
      setHighlightLinks(linkIds)
    }
  }, [graphData])

  const handleSend = async () => {
    const msg = input.trim()
    if (!msg || sending) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setSending(true)
    clearSelection()
    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-session-id': sessionId },
        body: JSON.stringify({ message: msg }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, {
        role: 'assistant', content: data.answer, sql: data.sql, results: data.results,
      }])
      highlightQueryResults(data.results)
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant', content: 'Connection error. Please try again.',
      }])
    }
    setSending(false)
  }

  // --- Canvas rendering callbacks ------------------------------------------
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const type = node.nodeType || 'Product'
    const color = NODE_COLORS[type] || '#4466ff'
    const size = NODE_SIZES[type] || 4
    const isHighlighted = highlightNodes.size > 0 && highlightNodes.has(node.id)
    const isSelected = selectedNode?.id === node.id

    // Glow ring for highlighted / selected nodes
    if (isHighlighted || isSelected) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI)
      ctx.fillStyle = color + '30'
      ctx.fill()
    }

    // Main circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
    ctx.fillStyle = isHighlighted || isSelected ? color : color + 'cc'
    ctx.fill()

    // Border
    ctx.strokeStyle = isHighlighted || isSelected ? '#fff' : color + '60'
    ctx.lineWidth = isSelected ? 2 : 0.5
    ctx.stroke()

    // Label (visible when zoomed in or node is highlighted)
    if (globalScale > 1.5 || isHighlighted || isSelected) {
      const label = node.label || node.id
      const fontSize = Math.max(10 / globalScale, 2)
      ctx.font = `600 ${fontSize}px Inter, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillStyle = isHighlighted || isSelected ? '#ffffff' : '#b0b8d0'
      ctx.fillText(label, node.x, node.y + size + 2)
    }
  }, [highlightNodes, selectedNode])

  const nodePointerAreaPaint = useCallback((node, color, ctx) => {
    const size = NODE_SIZES[node.nodeType] || 4
    ctx.beginPath()
    ctx.arc(node.x, node.y, size + 2, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()
  }, [])

  const linkColor = useCallback((link) => {
    const idx = graphData.links.indexOf(link)
    return highlightLinks.has(idx)
      ? 'rgba(120, 180, 255, 1)'
      : 'rgba(80, 140, 255, 0.35)'
  }, [highlightLinks, graphData])

  const linkWidth = useCallback((link) => {
    const idx = graphData.links.indexOf(link)
    return highlightLinks.has(idx) ? 2.5 : 0.8
  }, [highlightLinks, graphData])

  // --- Filtered data (toggle granular nodes) --------------------------------
  const filteredData = useMemo(() => {
    if (showGranular) return graphData
    const filteredNodes = graphData.nodes.filter(n => !GRANULAR_TYPES.has(n.nodeType))
    const nodeIds = new Set(filteredNodes.map(n => n.id))
    const filteredLinks = graphData.links.filter(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source
      const t = typeof l.target === 'object' ? l.target.id : l.target
      return nodeIds.has(s) && nodeIds.has(t)
    })
    return { nodes: filteredNodes, links: filteredLinks }
  }, [graphData, showGranular])

  // =========================================================================
  // Render
  // =========================================================================
  return (
    <div className="app-root">
      {/* Top Navigation */}
      <nav className="top-nav">
        <div className="nav-left">
          <div className="nav-logo">◈</div>
          <span className="nav-sep">/</span>
          <span className="nav-crumb">Mapping</span>
          <span className="nav-sep">/</span>
          <span className="nav-crumb active">Order to Cash</span>
        </div>
        <div className="nav-right">
          <span className="nav-stat">{graphData.nodes.length} nodes</span>
          <span className="nav-dot">·</span>
          <span className="nav-stat">{graphData.links.length} edges</span>
        </div>
      </nav>

      <div className="main-content">
        {/* Graph Panel */}
        <div className="graph-panel">
          <div className="graph-controls">
            <button
              className={`ctrl-btn ${minimized ? 'active' : ''}`}
              onClick={() => setMinimized(!minimized)}
            >
              {minimized ? 'Expand' : 'Minimize'}
            </button>
            <button
              className={`ctrl-btn ${!showGranular ? 'active' : ''}`}
              onClick={() => setShowGranular(!showGranular)}
            >
              {showGranular ? 'Hide' : 'Show'} Granular Overlay
            </button>
          </div>

          {loading ? (
            <div className="loading-screen">
              <div className="loader">
                <div className="loader-ring" />
                <div className="loader-ring r2" />
                <div className="loader-ring r3" />
                <div className="loader-core" />
              </div>
              <div className="loader-text">Mapping Order-to-Cash flow…</div>
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={filteredData}
              backgroundColor="#080818"
              nodeCanvasObject={nodeCanvasObject}
              nodePointerAreaPaint={nodePointerAreaPaint}
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={1.2}
              linkDirectionalParticleSpeed={0.003}
              linkDirectionalParticleColor={() => 'rgba(120,180,255,0.6)'}
              onNodeClick={handleNodeClick}
              onBackgroundClick={clearSelection}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.25}
              warmupTicks={150}
              cooldownTicks={300}
              enableZoomInteraction={true}
              enablePanInteraction={true}
              linkCurvature={0.1}
            />
          )}

          {/* Legend */}
          <div className={`legend ${minimized ? 'hidden' : ''}`}>
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="legend-item">
                <div className="legend-orb" style={{ background: color }} />
                <span className="legend-type">{type}</span>
              </div>
            ))}
          </div>

          {/* Node Inspector Card */}
          {selectedNode && (
            <div className="inspector">
              <div className="inspector-top">
                <span
                  className="inspector-badge"
                  style={{
                    color: NODE_COLORS[selectedNode.nodeType] || '#4466ff',
                    borderColor: NODE_COLORS[selectedNode.nodeType] || '#4466ff',
                  }}
                >
                  {selectedNode.nodeType}
                </span>
                <button className="inspector-x" onClick={clearSelection}>✕</button>
              </div>
              <div className="inspector-name">{selectedNode.label || selectedNode.id}</div>
              <div
                className="inspector-line"
                style={{ background: NODE_COLORS[selectedNode.nodeType] || '#4466ff' }}
              />
              <div className="inspector-body">
                {Object.entries(selectedNode)
                  .filter(([k]) => !INSPECTOR_HIDDEN_KEYS.has(k))
                  .map(([k, v]) => (
                    <div key={k} className="inspector-row">
                      <span className="ikey">{k}</span>
                      <span className="ival">{v == null ? '—' : String(v)}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="chat-head">
            <div className="chat-head-title">Chat with Graph</div>
            <div className="chat-head-sub">Order to Cash</div>
          </div>

          <div className="chat-identity">
            <div className="ai-avatar">D</div>
            <div>
              <div className="ai-name">Doge AI</div>
              <div className="ai-role">Graph Agent</div>
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'assistant' && <div className="msg-avatar">D</div>}
                {m.role === 'user' && <div className="msg-avatar user-avatar">You</div>}
                <div className="msg-body">
                  <div className="msg-sender">{m.role === 'assistant' ? 'Doge AI' : 'You'}</div>
                  <div
                    className="msg-text"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(m.content) }}
                  />
                  {m.sql && (
                    <div className="msg-sql">
                      <div className="sql-tag">SQL QUERY</div>
                      <code>{m.sql}</code>
                    </div>
                  )}
                  {m.results?.length > 0 && (
                    <div className="msg-table-wrap">
                      <table className="msg-table">
                        <thead>
                          <tr>{Object.keys(m.results[0]).map(c => <th key={c}>{c}</th>)}</tr>
                        </thead>
                        <tbody>
                          {m.results.slice(0, 8).map((row, ri) => (
                            <tr key={ri}>
                              {Object.values(row).map((v, ci) => (
                                <td key={ci}>{v == null ? '—' : String(v)}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {m.results.length > 8 && (
                        <div className="table-more">+{m.results.length - 8} more rows</div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="msg assistant">
                <div className="msg-avatar">D</div>
                <div className="msg-body">
                  <div className="msg-sender">Doge AI</div>
                  <div className="typing"><span /><span /><span /></div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-bottom">
            <div className="chat-status">
              <span className="status-dot" />
              Doge AI is awaiting instructions
            </div>
            <div className="chat-input-row">
              <textarea
                className="chat-input"
                placeholder="Analyze anything…"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                disabled={sending}
                rows={1}
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={sending || !input.trim()}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
