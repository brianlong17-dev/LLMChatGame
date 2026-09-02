import { useState, useEffect, useRef } from 'react'
import { LOBBY_STORAGE_KEY } from '../utils/settings'

const LEVEL_PRESENTATION = {
  quickstart: {
    displayName: 'Tutorial',
    tagline: 'Learn the format',
    minutes: '5 min',
    description: 'A guided one-on-one round of Rock-Paper-Scissors that walks you through chatting, voting, and how a round resolves — before you jump into a real game.',
  },
  beginner: {
    displayName: 'Intro',
    tagline: 'Fast & tactical',
    minutes: '10 min',
    recommended: false,
    description: "A six-player, six-phase game. You'll need to navigate the group's dynamics to win.",
  },
  '8p': {
    displayName: 'Intermediate',
    tagline: 'Bigger alliances',
    minutes: '15 min',
    description: 'Eight players elect leaders and protect allies — more room for social dynamics to unfold.',
  },
}

const STEP_LABELS = ['You', 'Level', 'Cast', 'Review']

const HARD_CAP = 12

export default function Lobby({ onStart, initialStep = 0, onInitialStepUsed }) {
  const saved = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')

  const [step, setStep] = useState(initialStep)

  useEffect(() => {
    if (initialStep) onInitialStepUsed?.()
  }, [])
  const [heroExpanded, setHeroExpanded] = useState(false)

  useEffect(() => {
    if (step !== 0 || heroExpanded) return
    const onKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.key.length !== 1) return
      e.preventDefault()
      setHumanName(e.key)
      setHeroExpanded(true)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [step, heroExpanded])
  const [tabs, setTabs] = useState({})
  const [activeTab, setActiveTab] = useState('')
  const [selected, setSelected] = useState(saved.selected || [])
  const [playing, setPlaying] = useState(saved.playing !== undefined ? saved.playing : true)
  const [humanName, setHumanName] = useState(saved.humanName || '')
  const [customNames, setCustomNames] = useState(saved.customNames || [])
  const [customInput, setCustomInput] = useState('')
  const [query, setQuery] = useState('')
  const [models, setModels] = useState(saved.models || {})
  const [modelOptions, setModelOptions] = useState([])
  const [gameEnabled, setGameEnabled] = useState(false)
  const [levels, setLevels] = useState([])
  const [selectedLevel, setSelectedLevel] = useState(saved.selectedLevel || null)
  const [turnstileEnabled, setTurnstileEnabled] = useState(null)
  const [turnstileToken, setTurnstileToken] = useState(null)
  const turnstileRef = useRef(null)

  useEffect(() => {
    if (!turnstileEnabled || step !== 3) return
    let widgetId = null
    const renderWidget = () => {
      if (turnstileRef.current) {
        widgetId = window.turnstile.render(turnstileRef.current, {
          sitekey: '0x4AAAAAADhT2idZkL-1k2P0',
          appearance: 'interaction-only',
          callback: (token) => setTurnstileToken(token),
          'expired-callback': () => setTurnstileToken(null),
          'error-callback': () => setTurnstileToken(null),
        })
      }
    }
    if (window.turnstile) {
      renderWidget()
    } else {
      window.onTurnstileLoad = renderWidget
    }
    return () => {
      if (widgetId !== null) window.turnstile?.remove(widgetId)
    }
  }, [turnstileEnabled, step])

  useEffect(() => {
    const prev = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')
    localStorage.setItem(LOBBY_STORAGE_KEY, JSON.stringify({ ...prev, selected, playing, humanName, customNames, selectedLevel, models }))
  }, [selected, playing, humanName, customNames, selectedLevel, models])

  useEffect(() => {
    fetch('/api/characters')
      .then(r => r.json())
      .then(data => {
        setTabs(data.tabs)
        setActiveTab(Object.keys(data.tabs)[0])
      })
    fetch('/api/flags')
      .then(r => r.json())
      .then(data => {
        setGameEnabled(data.game_enabled)
        setTurnstileEnabled(data.turnstile_enabled)
      })
    fetch('/api/levels')
      .then(r => r.json())
      .then(data => {
        const unlocked = data.levels.filter(l => !l.locked)
        setLevels(unlocked)
        const ids = unlocked.map(l => l.id)
        if (!ids.includes(selectedLevel)) {
          const recommended = unlocked.find(l => LEVEL_PRESENTATION[l.id]?.recommended)
          setSelectedLevel(recommended?.id ?? unlocked[0]?.id ?? null)
        }
      })
      .catch(err => console.error('Error fetching levels:', err))
    fetch('/api/models')
      .then(r => r.json())
      .then(data => setModelOptions(data.models))
      .catch(err => console.error('Error fetching models:', err))
  }, [])

  const selectedLevelObj = levels.find(l => l.id === selectedLevel)
  const maxPlayers = selectedLevelObj?.max_players || 12
  const minPlayers = selectedLevelObj?.min_players || 2
  const maxAI = maxPlayers - (playing ? 1 : 0)
  const selectCap = Math.max(maxAI, HARD_CAP - (playing ? 1 : 0))
  const minAI = Math.max(0, minPlayers - (playing ? 1 : 0))
  const defaultModelId = (modelOptions.find(m => m.default) || modelOptions[0])?.id || ''

  const levelDisplayName = (level) => LEVEL_PRESENTATION[level.id]?.displayName || level.name

  const removeAI = (name) => {
    setSelected(selected.filter(n => n !== name))
  }

  const toggle = (name) => {
    if (selected.includes(name)) {
      removeAI(name)
    } else if (selected.length < selectCap) {
      setSelected([...selected, name])
    }
  }

  const randomize = () => {
    const pool = [...new Set([...Object.values(tabs).flat(), ...customNames])]
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[pool[i], pool[j]] = [pool[j], pool[i]]
    }
    setSelected(pool.slice(0, Math.max(0, maxAI)))
  }

  const clearCast = () => setSelected([])

  const chooseLevel = (id) => {
    setSelectedLevel(id)
  }

  const setModel = (name, value) => setModels({ ...models, [name]: value })

  const addCustom = () => {
    const name = customInput.trim()
    if (!name) return
    const lower = name.toLowerCase()
    const allNames = [...customNames, ...Object.values(tabs).flat()]
    const existing = allNames.find(n => n.toLowerCase() === lower)
    if (existing) {
      toggle(existing)
      setCustomInput('')
      return
    }
    setCustomNames([...customNames, name])
    if (selected.length < selectCap) setSelected([...selected, name])
    setCustomInput('')
  }

  const removeCustom = (name) => {
    setCustomNames(customNames.filter(n => n !== name))
    removeAI(name)
  }

  const addFromSearch = () => {
    const name = query.trim()
    if (!name || selected.length >= selectCap) return
    setCustomNames([...customNames, name])
    setSelected([...selected, name])
    setQuery('')
  }

  const q = query.trim().toLowerCase()
  const allNames = [...new Set([...Object.values(tabs).flat(), ...customNames])]
  const tabNames = activeTab === 'All'
    ? allNames
    : activeTab === 'Custom'
      ? customNames
      : (tabs[activeTab] || [])
  const filtered = q ? allNames.filter(n => n.toLowerCase().includes(q)) : tabNames

  const castNames = selected.slice(0, maxAI)
  const castSubText = selectedLevelObj
    ? `${levelDisplayName(selectedLevelObj)} needs ${minAI === maxAI ? maxAI : `${minAI}–${maxAI}`} more ${maxAI === 1 ? 'player' : 'players'}${playing ? ' alongside you.' : '.'}`
    : ''

  const remainingToMin = Math.max(0, minAI - selected.length)
  const castDisabled = remainingToMin > 0
  const canStart = gameEnabled && castNames.length >= minAI && selectedLevel && (!playing || humanName.trim()) && !!defaultModelId && (!turnstileEnabled || turnstileToken)

  const goto = (target) => { if (target < step) setStep(target) }
  const back = () => setStep(Math.max(0, step - 1))

  const handleStart = () => {
    if (!canStart) return
    const modelMap = {}
    castNames.forEach(n => { modelMap[n] = models[n] || defaultModelId })
    onStart({ names: castNames, humanName: playing ? humanName.trim() : null, levelId: selectedLevel, turnstileToken, models: modelMap })
  }

  return (
    <div className="lobby-flow">
      {step > 0 && (
        <div className="lobby-topbar">
          <div className="lobby-topbar-right">
            <div className="lobby-stepper">
              {STEP_LABELS.map((label, i) => {
                const isActive = step === i
                const isDone = step > i
                return (
                  <button
                    key={label}
                    className={`lobby-step ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}
                    onClick={() => isDone && goto(i)}
                    disabled={!isDone && !isActive}
                  >
                    {String(i + 1).padStart(2, '0')} {label}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      <div className={`lobby-content ${step === 2 ? 'lobby-content-wide' : ''}`} key={step}>

        {step === 0 && (
          <div className="lobby-hero">
            {!heroExpanded ? (
              <>
                <button className="lobby-hero-hook" onClick={() => setHeroExpanded(true)}>
                  Enter the chat<span className="lobby-cursor" aria-hidden="true" />
                </button>
                <div className="lobby-hero-tagline">A social survival game, played out entirely in a live chat feed.</div>
              </>
            ) : (
              <div className="lobby-hero-prompt">
                <div className="lobby-hero-prompt-row">
                  <span className="lobby-hero-caret" aria-hidden="true">&gt;</span>
                  <input
                    className="lobby-hero-input"
                    value={humanName}
                    maxLength={40}
                    placeholder="your name"
                    aria-label="Your name"
                    onChange={e => setHumanName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && humanName.trim()) setStep(1) }}
                    autoFocus
                  />
                </div>
                {humanName.trim() && (
                  <button className="lobby-hero-continue" onClick={() => setStep(1)}>Continue →</button>
                )}
              </div>
            )}
          </div>
        )}

        {step === 1 && (
          <div className="lobby-step-body">
            <div className="lobby-step-label sc-label">01 — Level</div>
            <div className="lobby-step-heading">Choose a level</div>
            <div className="lobby-step-sub">Pick a format. You can change this later.</div>
            <div className="level-list">
              {levels.map((level, i) => {
                const p = LEVEL_PRESENTATION[level.id] || {}
                const isSel = selectedLevel === level.id
                return (
                  <button
                    key={level.id}
                    className={`level-row ${isSel ? 'selected' : ''}`}
                    onClick={() => chooseLevel(level.id)}
                  >
                    <span className="level-row-marker">{isSel ? '▸' : String(i + 1).padStart(2, '0')}</span>
                    <span className="level-row-main">
                      <span className="level-row-title">
                        <span className="level-row-name">{levelDisplayName(level)}</span>
                        {p.tagline && <span className="level-row-tagline sc-label">{p.tagline}</span>}
                        {p.recommended && <span className="level-row-badge">start here</span>}
                      </span>
                      <span className="level-row-description">{p.description || level.description}</span>
                    </span>
                    <span className="level-row-meta">
                      <span>{level.min_players === level.max_players ? level.max_players : `${level.min_players}–${level.max_players}`} players</span>
                      {p.minutes && <span>{p.minutes}</span>}
                    </span>
                  </button>
                )
              })}
            </div>
            <div className="lobby-footer-nav">
              <button className="lobby-back-link" onClick={back}>← Back</button>
              <button className="lobby-start-btn" disabled={!selectedLevel} onClick={() => selectedLevel && setStep(2)}>
                Continue →
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="lobby-step-body">
            <div className="lobby-step-label sc-label">02 — Cast</div>
            <div className="lobby-step-heading">Build your cast</div>
            <div className="lobby-step-sub">{castSubText}</div>

            <div className="lobby-selected">
              <span className="lobby-selected-label sc-label">
                {Math.min(selected.length, maxAI)} / {maxAI} selected
                <button className="lobby-dice" onClick={randomize} title="Randomly fill players" aria-label="Randomly fill players">
                  <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2.5 14 V5.5 L5 3 H13.5 V11.5 L11 14 Z" />
                    <path d="M2.5 5.5 H11 M11 5.5 L13.5 3 M11 5.5 V14" />
                    <circle cx="4.9" cy="7.7" r="0.9" fill="currentColor" stroke="none" />
                    <circle cx="8.6" cy="11.8" r="0.9" fill="currentColor" stroke="none" />
                    <circle cx="12.2" cy="8.4" r="0.75" fill="currentColor" stroke="none" />
                  </svg>
                </button>
                {selected.length > 0 && (
                  <button className="lobby-clear" onClick={clearCast} title="Clear cast" aria-label="Clear cast">
                    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
                      <path d="M4 4 L12 12 M12 4 L4 12" />
                    </svg>
                  </button>
                )}
              </span>
              <div className="lobby-progress-track">
                <div className="lobby-progress-fill" style={{ width: `${Math.min(100, (Math.min(selected.length, maxAI) / Math.max(1, maxAI)) * 100)}%` }} />
              </div>
              <div className="lobby-chips">
                {playing && <span className="chip chip-human">{humanName.trim()} (you)</span>}
                {selected.map((name, i) => (
                  <span key={name} className={`chip ${i >= maxAI ? 'inactive' : ''}`} title={i >= maxAI ? 'Inactive at this level — will rejoin if you pick a bigger level' : undefined}>
                    {name}
                    <button className="chip-remove" onClick={() => toggle(name)}>×</button>
                  </span>
                ))}
                {selected.length === 0 && <span className="lobby-hint">{maxAI === 1 ? (playing ? 'Select a partner below' : 'Select a player below') : 'Select players below'}</span>}
              </div>
            </div>

            <div className="lobby-search">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <circle cx="5.5" cy="5.5" r="4" stroke="var(--text-dim)" strokeWidth="1.3" />
                <path d="M8.7 8.7L12 12" stroke="var(--text-dim)" strokeWidth="1.3" strokeLinecap="round" />
              </svg>
              <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search cast..." />
              {query && <button className="lobby-search-x" onClick={() => setQuery('')}>×</button>}
            </div>

            {!q && (
              <div className="lobby-tabs">
                {Object.keys(tabs).map(tab => (
                  <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
                    {tab}
                  </button>
                ))}
                <button className={`tab-btn ${activeTab === 'Custom' ? 'active' : ''}`} onClick={() => setActiveTab('Custom')}>Custom</button>
              </div>
            )}

            {!q && activeTab === 'Custom' && (
              <div className="custom-input-row">
                <div className="name-input-wrapper">
                  <input
                    className="lobby-name-input"
                    placeholder="Enter a name..."
                    value={customInput}
                    maxLength={40}
                    onChange={e => setCustomInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') addCustom() }}
                  />
                  <span className={`name-char-count${customInput.length >= 40 ? ' at-limit' : ''}`}>
                    {customInput.length}/40
                  </span>
                </div>
                <button className="input-submit" onClick={addCustom}>Add</button>
              </div>
            )}

            {q && filtered.length === 0 && (
              <div className="custom-input-row">
                <button className="input-submit" onClick={addFromSearch} disabled={selected.length >= selectCap}>
                  + Add “{query.trim()}”
                </button>
              </div>
            )}

            <div className="lobby-grid">
              {filtered.map(name => {
                const selectedIndex = selected.indexOf(name)
                const isSelected = selectedIndex !== -1
                const isInactive = isSelected && selectedIndex >= maxAI
                const isDisabled = !isSelected && selected.length >= selectCap
                const isCustom = !q && activeTab === 'Custom'
                const btnClass = `name-btn ${isSelected ? 'selected' : ''} ${isInactive ? 'inactive' : ''}`
                return isCustom ? (
                  <span key={name} className="name-btn-wrap">
                    <button className={btnClass} onClick={() => toggle(name)} disabled={isDisabled} title={isInactive ? 'Inactive at this level' : undefined}>
                      {name}
                    </button>
                    <button className="name-btn-remove" onClick={() => removeCustom(name)}>×</button>
                  </span>
                ) : (
                  <button key={name} className={btnClass} onClick={() => toggle(name)} disabled={isDisabled} title={isInactive ? 'Inactive at this level' : undefined}>
                    {name}
                  </button>
                )
              })}
              {!q && activeTab === 'Custom' && customNames.length === 0 && <span className="lobby-hint">Add names above</span>}
              {!q && activeTab !== 'Custom' && filtered.length === 0 && <span className="lobby-hint">No matches</span>}
            </div>

            <div className="lobby-footer-nav lobby-footer-nav-3col">
              <button className="lobby-back-link" onClick={back}>← Back</button>
              <button className="lobby-back-link lobby-mode-toggle" onClick={() => setPlaying(!playing)}>
                {playing ? 'Watch only?' : 'Play along?'}
              </button>
              <button className="lobby-start-btn" disabled={castDisabled} onClick={() => !castDisabled && setStep(3)}>
                {castDisabled ? `Select ${remainingToMin} more` : 'Review →'}
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="lobby-step-body">
            <div className="lobby-step-label sc-label">03 — Review</div>
            <div className="lobby-step-heading">Review</div>
            <div className="lobby-step-sub">Confirm your setup before entering the chat.</div>

            <div className="lobby-recap-panel">
              <div className="lobby-recap-row">
                <span className="lobby-recap-label sc-label">{playing ? 'Your name' : 'Your role'}</span>
                <span>{playing ? humanName.trim() : 'Watching only'}</span>
              </div>
              <div className="lobby-recap-row"><span className="lobby-recap-label sc-label">Level</span><span>{selectedLevelObj ? levelDisplayName(selectedLevelObj) : '—'}</span></div>
            </div>

            <div className="lobby-review-cast">
              <div className="lobby-review-header sc-label">Cast</div>
              {castNames.map(name => (
                <div key={name} className="lobby-review-row">
                  <span className="lobby-review-name">{name}</span>
                  <select className="lobby-model-select" value={models[name] || defaultModelId} onChange={e => setModel(name, e.target.value)}>
                    {modelOptions.map(opt => <option key={opt.id} value={opt.id}>{opt.name}</option>)}
                  </select>
                </div>
              ))}
            </div>

            {turnstileEnabled && <div ref={turnstileRef} style={{ display: 'flex', justifyContent: 'center' }} />}

            <div className="lobby-footer-nav">
              <button className="lobby-back-link" onClick={back}>← Back</button>
              <button className="lobby-start-btn" disabled={!canStart} onClick={handleStart}>
                {!gameEnabled ? 'Coming Soon' : 'Start Game'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
