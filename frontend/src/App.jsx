import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

const WS_URL = `ws://${window.location.host}/ws/game`

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
// Round tracker
// ---------------------------------------------------------------------------

function RoundTracker({ rounds, currentIndex }) {
  if (!rounds || rounds.length === 0) return null
  return (
    <div className="round-tracker">
      <h2 className="scoreboard-title">Rounds</h2>
      <ul className="round-list">
        {rounds.map((name, i) => {
          const done = i < currentIndex
          const active = i === currentIndex
          return (
            <li key={i} className={`round-item ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
              <span className="round-item-arrow">{active ? '›' : ''}</span>
              <span className="round-item-name">{name}</span>
            </li>
          )
        })}
      </ul>
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

function InputRequest({ request, onSubmit }) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const recorderRef = useRef(null)

  const inactive = !request
  const description = request?.description ?? 'Waiting...'

  const submit = (val) => { onSubmit(val); setValue('') }

  const toggleMic = async () => {
    if (listening) {
      recorderRef.current?.stop()
      return
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    const chunks = []
    recorder.ondataavailable = e => chunks.push(e.data)
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      setListening(false)
      const blob = new Blob(chunks, { type: recorder.mimeType })
      const form = new FormData()
      form.append('audio', blob, 'recording.webm')
      const res = await fetch('/api/transcribe', { method: 'POST', body: form })
      const data = await res.json()
      if (data.text) setValue(data.text)
    }
    recorderRef.current = recorder
    recorder.start()
    setListening(true)
  }

  return (
    <div className={`input-bar ${inactive ? 'inactive' : ''}`}>
      <div className="input-prompt">{request?.field ?? 'your turn'} — {description}</div>
      {request?.choices ? (
        <div className="input-choices">
          {request.choices.map(c => (
            <button key={c} className="choice-btn" onClick={() => submit(c)}>{c}</button>
          ))}
        </div>
      ) : (
        <div className="input-row">
          <input
            className="input-text"
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && value.trim()) submit(value.trim()) }}
            placeholder="Type your response..."
            autoFocus={!inactive}
          />
          <button className={`mic-btn ${listening ? 'active' : ''}`} onClick={toggleMic} title="Voice input">
            {listening ? '◼' : '🎙'}
          </button>
          <button className="input-submit" onClick={() => { if (value.trim()) submit(value.trim()) }}>
            Send
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Lobby
// ---------------------------------------------------------------------------

const MAX_PLAYERS = 12

const LOBBY_STORAGE_KEY = 'lobby_state'

function Lobby({ onStart }) {
  const saved = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')

  const [tabs, setTabs] = useState({})
  const [activeTab, setActiveTab] = useState('')
  const [selected, setSelected] = useState(saved.selected || [])
  const [mode, setMode] = useState(saved.mode || 'watch')
  const [humanName, setHumanName] = useState(saved.humanName || '')
  const [customNames, setCustomNames] = useState(saved.customNames || [])
  const [customInput, setCustomInput] = useState('')

  useEffect(() => {
    localStorage.setItem(LOBBY_STORAGE_KEY, JSON.stringify({ selected, mode, humanName, customNames }))
  }, [selected, mode, humanName, customNames])

  const addCustom = () => {
    const name = customInput.trim()
    if (!name || customNames.includes(name)) return
    setCustomNames([...customNames, name])
    if (selected.length < MAX_PLAYERS) setSelected([...selected, name])
    setCustomInput('')
  }

  const removeCustom = (name) => {
    setCustomNames(customNames.filter(n => n !== name))
    setSelected(selected.filter(n => n !== name))
  }

  useEffect(() => {
    fetch('/api/characters')
      .then(r => r.json())
      .then(data => {
        setTabs(data.tabs)
        setActiveTab(Object.keys(data.tabs)[0])
      })
  }, [])

  const toggle = (name) => {
    if (selected.includes(name)) {
      setSelected(selected.filter(n => n !== name))
    } else if (selected.length < MAX_PLAYERS) {
      setSelected([...selected, name])
    }
  }

  const canStart = selected.length >= 2 && (mode === 'watch' || humanName.trim())

  return (
    <div className="lobby">
      <h1 className="lobby-title">THE GAME</h1>

      <div className="lobby-selected">
        <span className="lobby-selected-label">Players ({selected.length}/{MAX_PLAYERS})</span>
        <div className="lobby-chips">
          {selected.map(name => (
            <span key={name} className="chip">
              {name}
              <button className="chip-remove" onClick={() => toggle(name)}>×</button>
            </span>
          ))}
          {selected.length === 0 && <span className="lobby-hint">Select players below</span>}
        </div>
      </div>

      <div className="lobby-tabs">
        {Object.keys(tabs).map(tab => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
        <button
          className={`tab-btn ${activeTab === 'Custom' ? 'active' : ''}`}
          onClick={() => setActiveTab('Custom')}
        >
          Custom
        </button>
      </div>

      {activeTab === 'Custom' && (
        <div className="custom-input-row">
          <input
            className="lobby-name-input"
            placeholder="Enter a name..."
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') addCustom() }}
          />
          <button className="input-submit" onClick={addCustom}>Add</button>
        </div>
      )}

      <div className="lobby-grid">
        {(activeTab === 'Custom' ? customNames : (tabs[activeTab] || [])).map(name => (
          activeTab === 'Custom' ? (
            <span key={name} className="name-btn-wrap">
              <button
                className={`name-btn ${selected.includes(name) ? 'selected' : ''}`}
                onClick={() => toggle(name)}
                disabled={!selected.includes(name) && selected.length >= MAX_PLAYERS}
              >
                {name}
              </button>
              <button className="name-btn-remove" onClick={() => removeCustom(name)}>×</button>
            </span>
          ) : (
            <button
              key={name}
              className={`name-btn ${selected.includes(name) ? 'selected' : ''}`}
              onClick={() => toggle(name)}
              disabled={!selected.includes(name) && selected.length >= MAX_PLAYERS}
            >
              {name}
            </button>
          )
        ))}
        {activeTab === 'Custom' && customNames.length === 0 && (
          <span className="lobby-hint">Add names above</span>
        )}
      </div>

      <div className="lobby-footer">
        <div className="lobby-mode">
          <label className="mode-opt">
            <input type="radio" name="mode" value="watch" checked={mode === 'watch'} onChange={() => setMode('watch')} />
            Watch only
          </label>
          <label className="mode-opt">
            <input type="radio" name="mode" value="play" checked={mode === 'play'} onChange={() => setMode('play')} />
            Play as:
          </label>
          {mode === 'play' && (
            <input
              className="lobby-name-input"
              placeholder="Your name"
              value={humanName}
              onChange={e => setHumanName(e.target.value)}
              autoFocus
            />
          )}
        </div>
        <button
          className="lobby-start-btn"
          disabled={!canStart}
          onClick={() => onStart({ names: selected, humanName: mode === 'play' ? humanName.trim() : null })}
        >
          Start Game
        </button>
      </div>
    </div>
  )
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
  const [inputRequest, setInputRequest] = useState(null)
  const [phaseRounds, setPhaseRounds] = useState([])
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0)

  const wsRef = useRef(null)
  const colorMapRef = useRef({})
  const bottomRef = useRef(null)
  const feedRef = useRef(null)

  const addEvent = useCallback((evt) => {
    setEvents(prev => [...prev, evt])
  }, [])

  const startGame = useCallback(({ names = [], humanName = null } = {}) => {
    if (wsRef.current) return
    setStatus('connecting')
    setEvents([])
    setScores({})
    colorMapRef.current = {}

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'start', names, human_name: humanName }))
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
      if (evt.type === 'input_request') {
        setInputRequest(evt)
        return
      }
      if (evt.type === 'phase_rounds') {
        setPhaseRounds(evt.rounds)
        setCurrentRoundIndex(0)
        return
      }
      if (evt.type === 'phase_round_index') {
        setCurrentRoundIndex(evt.index)
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

  const submitInput = useCallback((value) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'input_response', value }))
      setInputRequest(null)
    }
  }, [])

  // Auto-scroll only if near bottom
  useEffect(() => {
    const feed = feedRef.current
    if (!feed) return
    const isNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 150
    if (isNearBottom) setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
  }, [events, inputRequest])

  const visibleEvents = showPrivate
    ? events
    : events.filter(e => e.type !== 'private_thought' && e.type !== 'system_private')

  if (status === 'idle') {
    return <Lobby onStart={startGame} />
  }

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
          <span className={`start-btn status-${status}`} style={{ cursor: 'default' }}>
            {status === 'connecting' && 'Connecting…'}
            {status === 'running' && 'Running…'}
            {status === 'done' && '✓ Done'}
            {status === 'error' && '⚠ Error'}
          </span>
        </div>
      </header>

      <div className="app-body">
        <div className="feed-col">
          <main className="feed" ref={feedRef}>
            {visibleEvents.map((evt, i) => (
              <Message key={i} event={evt} colorMap={colorMapRef.current} />
            ))}
            <div ref={bottomRef} />
          </main>
          <InputRequest request={inputRequest} onSubmit={submitInput} />
        </div>

        <aside className="sidebar">
          <Scoreboard scores={scores} evicted={evicted}/>
          <RoundTracker rounds={phaseRounds} currentIndex={currentRoundIndex} />
        </aside>
      </div>
    </div>
  )
}
