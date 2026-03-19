import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

const WS_URL = 'ws://localhost:8000/ws/game'

const SPEAKER_COLORS = [
  '#e07b54', '#5b8dd9', '#67b37d', '#c97bc4',
  '#d4a84b', '#5bbccc', '#d9706a', '#8d7fd9',
]

function getSpeakerColor(name, colorMap) {
  if (!colorMap[name]) {
    const idx = Object.keys(colorMap).length % SPEAKER_COLORS.length
    colorMap[name] = SPEAKER_COLORS[idx]
  }
  return colorMap[name]
}

// ---------------------------------------------------------------------------
// Message renderers
// ---------------------------------------------------------------------------

function PhaseHeader({ phase_number }) {
  return (
    <div className="msg phase-header">
      <span className="phase-label">— PHASE {phase_number} —</span>
    </div>
  )
}

function RoundHeader({ round_number, scores }) {
  return (
    <div className="msg round-header">
      <span className="round-label">Round {round_number}</span>
      {scores && <span className="round-scores">{scores}</span>}
    </div>
  )
}

function PublicAction({ speaker, message, color }) {
  const isSystem = speaker === 'SYSTEM' || speaker === 'HOST'
  return (
    <div className={`msg public-action ${isSystem ? 'system' : ''}`}>
      {!isSystem && (
        <span className="speaker" style={{ color }}>{speaker}</span>
      )}
      {isSystem && <span className="speaker system-speaker">{speaker}</span>}
      <span className="message-text">{message}</span>
    </div>
  )
}

function RoundSummary({ summary }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="msg round-summary">
      <button className="summary-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▼' : '▶'} Round Summary
      </button>
      {open && <p className="summary-text">{summary}</p>}
    </div>
  )
}

function PrivateThought({ speaker, message, color }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="msg private-thought">
      <button className="thought-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▼' : '▶'}{' '}
        <span style={{ color }}>{speaker}</span>
        <span className="thought-label"> (thinking...)</span>
      </button>
      {open && <p className="thought-text">{message}</p>}
    </div>
  )
}

function SystemPrivate({ message }) {
  return (
    <div className="msg system-private">
      <span className="sys-icon">⚙</span>
      <span className="sys-text">{message}</span>
    </div>
  )
}

function GameOver({ winner }) {
  return (
    <div className="msg game-over">
      <span className="trophy">🏆</span>
      <span className="winner-text">{winner} wins!</span>
    </div>
  )
}

function ErrorMsg({ message }) {
  return (
    <div className="msg error-msg">
      <span className="error-icon">⚠</span> {message}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Scoreboard sidebar
// ---------------------------------------------------------------------------

function Scoreboard({ scores, evicted }) {
  if (!scores || Object.keys(scores).length === 0) return null
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1])
  return (
    <div className="scoreboard">
      <h2 className="scoreboard-title">Scores</h2>
      <ol className="score-list">
        {sorted.map(([name, score], i) => (
          <li key={name} className="score-row">
            <span className="score-rank">{i + 1}</span>
            <span className="score-name">{name}</span>
            <span className="score-pts">{score}</span>
          </li>
        ))}
      </ol>
      <div className="graveyard">
        <h2 className="scoreboard-title">Graveyard</h2>
        {evicted.map(name => (
          <div key={name} className="evicted-row"> ☠ {name}</div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Message dispatcher
// ---------------------------------------------------------------------------

function Message({ event, colorMap }) {
  switch (event.type) {
    case 'phase_header':
      return <PhaseHeader {...event} />
    case 'round_start':
      return <RoundHeader {...event} />
    case 'public_action':
      return (
        <PublicAction
          {...event}
          color={getSpeakerColor(event.speaker, colorMap)}
        />
      )
    case 'round_summary':
      return <RoundSummary {...event} />
    case 'private_thought':
      return (
        <PrivateThought
          {...event}
          color={getSpeakerColor(event.speaker, colorMap)}
        />
      )
    case 'system_private':
      return <SystemPrivate {...event} />
    case 'game_intro':
      return <PublicAction speaker="HOST" message={event.message} color="#aaa" />
    case 'game_over':
      return <GameOver winner={event.winner} />
    case 'error':
      return <ErrorMsg message={event.message} />
    // points_update handled separately via scoreboard — skip in log
    case 'points_update':
    case 'turn_header':
    case 'phase_intro':
    case 'evicted_update':
      return null
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [status, setStatus] = useState('idle') // idle | connecting | running | done | error
  const [events, setEvents] = useState([])
  const [scores, setScores] = useState({})
  const [evicted, setEvicted] = useState([])
  const [showPrivate, setShowPrivate] = useState(true)

  const wsRef = useRef(null)
  const colorMapRef = useRef({})
  const bottomRef = useRef(null)

  const addEvent = useCallback((evt) => {
    setEvents(prev => [...prev, evt])
  }, [])

  const startGame = useCallback(() => {
    if (wsRef.current) return
    setStatus('connecting')
    setEvents([])
    setScores({})
    colorMapRef.current = {}

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'start' }))
      setStatus('running')
    }

    ws.onmessage = (e) => {
      const evt = JSON.parse(e.data)
      if (evt.type === 'points_update') {
        setScores(evt.scores)
        return
      }
      if (evt.type === 'evicted_update') {
        setEvicted(evt.evicted_names)
        return
      }
      if (evt.type === 'game_over') {
        setStatus('done')
      }
      if (evt.type === 'error') {
        setStatus('error')
      }
      addEvent(evt)
    }

    ws.onclose = () => {
      wsRef.current = null
      setStatus(s => s === 'running' ? 'done' : s)
    }

    ws.onerror = () => {
      setStatus('error')
      addEvent({ type: 'error', message: 'WebSocket connection failed. Is the server running?' })
      wsRef.current = null
    }
  }, [addEvent])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const visibleEvents = showPrivate
    ? events
    : events.filter(e => e.type !== 'private_thought' && e.type !== 'system_private')

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">THE GAME</h1>
        <div className="header-controls">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showPrivate}
              onChange={e => setShowPrivate(e.target.checked)}
            />
            Show private thoughts
          </label>
          <button
            className={`start-btn status-${status}`}
            onClick={startGame}
            disabled={status === 'connecting' || status === 'running'}
          >
            {status === 'idle' && 'Start Game'}
            {status === 'connecting' && 'Connecting…'}
            {status === 'running' && 'Running…'}
            {status === 'done' && 'Play Again'}
            {status === 'error' && 'Retry'}
          </button>
        </div>
      </header>

      <div className="app-body">
        <main className="feed">
          {events.length === 0 && status === 'idle' && (
            <div className="empty-state">
              <p>Press <strong>Start Game</strong> to begin.</p>
            </div>
          )}
          {visibleEvents.map((evt, i) => (
            <Message key={i} event={evt} colorMap={colorMapRef.current} />
          ))}
          <div ref={bottomRef} />
        </main>

        <aside className="sidebar">
          <Scoreboard scores={scores} evicted={evicted}/>
        </aside>
      </div>
    </div>
  )
}
