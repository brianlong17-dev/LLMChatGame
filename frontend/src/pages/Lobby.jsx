import { useState, useEffect } from 'react'

const MAX_PLAYERS = 12
const LOBBY_STORAGE_KEY = 'lobby_state'

export default function Lobby({ onStart }) {
  const saved = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')

  const [tabs, setTabs] = useState({})
  const [activeTab, setActiveTab] = useState('')
  const [selected, setSelected] = useState(saved.selected || [])
  const [mode, setMode] = useState(saved.mode || 'watch')
  const [humanName, setHumanName] = useState(saved.humanName || '')
  const [customNames, setCustomNames] = useState(saved.customNames || [])
  const [customInput, setCustomInput] = useState('')
  const [gameEnabled, setGameEnabled] = useState(false)

  useEffect(() => {
    localStorage.setItem(LOBBY_STORAGE_KEY, JSON.stringify({ selected, mode, humanName, customNames }))
  }, [selected, mode, humanName, customNames])

  useEffect(() => {
    fetch('/api/characters')
      .then(r => r.json())
      .then(data => {
        setTabs(data.tabs)
        setActiveTab(Object.keys(data.tabs)[0])
      })
    fetch('/api/flags')
      .then(r => r.json())
      .then(data => setGameEnabled(data.game_enabled))
  }, [])

  const toggle = (name) => {
    if (selected.includes(name)) {
      setSelected(selected.filter(n => n !== name))
    } else if (selected.length < MAX_PLAYERS) {
      setSelected([...selected, name])
    }
  }

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

  const canStart = gameEnabled && selected.length >= 2 && (mode === 'watch' || humanName.trim())

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
          {gameEnabled ? 'Start Game' : 'Coming Soon'}
        </button>
      </div>
    </div>
  )
}
