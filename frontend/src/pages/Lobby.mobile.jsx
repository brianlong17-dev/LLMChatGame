import { useState, useEffect, useRef } from 'react'
import MobileNav from '../components/MobileNav'
import './Lobby.mobile.css'
import { LOBBY_STORAGE_KEY } from '../utils/settings'

// Mobile lobby for The Chat Survivor.
// Same data contract as the desktop Lobby:
//   • fetches /api/characters, /api/levels, /api/flags
//   • persists to localStorage 'lobby_state' (shape stays desktop-compatible)
//   • calls onStart({ names, humanName, levelId, turnstileToken })
// Difference from desktop: Watch/Play is an explicit fork. Tapping PLAY opens a
// name sheet; confirming seats "You" at the front (humanIndex 0). You can't be
// reordered — switch back via the toggle or the You chip's ×.

const HARD_CAP = 12

export default function LobbyMobile({ onStart }) {
  const saved = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')

  const [tabs, setTabs] = useState({})
  const [activeTab, setActiveTab] = useState('')
  const [selected, setSelected] = useState(saved.selected || [])
  const [mode, setMode] = useState(null) // null = unchosen; 'watch' | 'play'
  const [playing, setPlaying] = useState(false)
  const [humanName, setHumanName] = useState(saved.humanName || '')
  const [customNames, setCustomNames] = useState(saved.customNames || [])
  const [customInput, setCustomInput] = useState('')
  const [query, setQuery] = useState('')
  const [gameEnabled, setGameEnabled] = useState(false)
  const [levels, setLevels] = useState([])
  const [selectedLevel, setSelectedLevel] = useState(null) // TODO: restore saved.selectedLevel once testing done
  const [turnstileEnabled, setTurnstileEnabled] = useState(null)
  const [turnstileToken, setTurnstileToken] = useState(null)
  const [playOpen, setPlayOpen] = useState(false)
  const [playClosing, setPlayClosing] = useState(false)
  const turnstileRef = useRef(null)
  const levelsRef = useRef(null)
  const nameInputRef = useRef(null)

  const scrollLevelToStart = (btn, behavior = 'smooth') => {
    const c = levelsRef.current
    if (!c || !btn) return
    const delta = btn.getBoundingClientRect().left - c.getBoundingClientRect().left - 16
    c.scrollTo({ left: c.scrollLeft + delta, behavior })
  }

  // ── Turnstile (identical to desktop) ──
  useEffect(() => {
    if (!turnstileEnabled) return
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
    if (window.turnstile) renderWidget()
    else window.onTurnstileLoad = renderWidget
    return () => { if (widgetId !== null) window.turnstile?.remove(widgetId) }
  }, [turnstileEnabled])

  // ── Persist (desktop-compatible shape) ──
  useEffect(() => {
    const prev = JSON.parse(localStorage.getItem(LOBBY_STORAGE_KEY) || '{}')
    localStorage.setItem(LOBBY_STORAGE_KEY, JSON.stringify({
      ...prev, selected, humanIndex: playing ? 0 : null, humanName, customNames, selectedLevel,
    }))
  }, [selected, playing, humanName, customNames, selectedLevel])

  // ── On first reveal, scroll the stored level to the front ──
  const didInitScroll = useRef(false)
  useEffect(() => {
    if (didInitScroll.current || mode === null || !levels.length || !selectedLevel) return
    const btn = levelsRef.current?.querySelector(`[data-level="${selectedLevel}"]`)
    if (btn) { scrollLevelToStart(btn, 'auto'); didInitScroll.current = true }
  }, [mode, levels, selectedLevel])

  // ── Initial data ──
  useEffect(() => {
    fetch('/api/characters').then(r => r.json()).then(data => {
      setTabs(data.tabs)
      setActiveTab(Object.keys(data.tabs)[0])
    })
    fetch('/api/flags').then(r => r.json()).then(data => {
      setGameEnabled(data.game_enabled)
      setTurnstileEnabled(data.turnstile_enabled)
    })
    fetch('/api/levels').then(r => r.json()).then(data => {
      setLevels(data.levels)
      const ids = data.levels.filter(l => !l.locked).map(l => l.id)
      if (selectedLevel && !ids.includes(selectedLevel)) setSelectedLevel(null)
    }).catch(err => console.error('Error fetching levels:', err))
  }, [])

  const levelObj = levels.find(l => l.id === selectedLevel)
  const maxPlayers = levelObj?.max_players || 12
  const minPlayers = levelObj?.min_players || 2

  const aiCap = maxPlayers - (playing ? 1 : 0)
  const selectCap = Math.max(aiCap, HARD_CAP - (playing ? 1 : 0))
  const activeSelected = selected.slice(0, aiCap)
  const inactiveCount = selected.length - activeSelected.length
  const count = activeSelected.length + (playing ? 1 : 0)
  const need = Math.max(0, minPlayers - count)

  const toggle = (name) => setSelected(s =>
    s.includes(name) ? s.filter(n => n !== name) : (s.length >= selectCap ? s : [...s, name]))
  const remove = (name) => setSelected(s => s.filter(n => n !== name))

  // ── Watch / Play fork ──
  const goWatch = () => {
    setMode('watch'); setPlaying(false)
    if (playOpen) {
      setPlayOpen(false); setPlayClosing(true)
      setTimeout(() => setPlayClosing(false), 240)
    }
  }
  const goPlay = () => {
    setMode('play'); setPlaying(true); setPlayOpen(true); setPlayClosing(false)
    if (!humanName.trim()) requestAnimationFrame(() => nameInputRef.current?.focus())
  }

  // ── Custom names ──
  const addCustom = () => {
    const name = customInput.trim()
    if (!name) return
    const lower = name.toLowerCase()
    const existing = [...customNames, ...Object.values(tabs).flat()].find(n => n.toLowerCase() === lower)
    if (existing) { toggle(existing); setCustomInput(''); return }
    setCustomNames([...customNames, name])
    if (selected.length < selectCap) setSelected([...selected, name])
    setCustomInput('')
  }
  const removeCustom = (name) => { setCustomNames(customNames.filter(n => n !== name)); remove(name) }
  const addFromSearch = () => {
    const name = query.trim()
    if (!name || selected.length >= selectCap) return
    setCustomNames([...customNames, name])
    setSelected([...selected, name])
    setQuery('')
  }

  const humanNameMissing = playing && !humanName.trim()
  const bodyVisible = mode === 'watch' || (mode === 'play' && !!humanName.trim())
  const canStart = gameEnabled && count >= minPlayers && count <= maxPlayers
    && selectedLevel && !humanNameMissing && (!turnstileEnabled || turnstileToken)

  const q = query.trim().toLowerCase()
  const allNames = [...new Set([...Object.values(tabs).flat(), ...customNames])]
  const names = [...new Set(activeTab === 'Custom' ? customNames : (tabs[activeTab] || []))]
  const filtered = q ? allNames.filter(n => n.toLowerCase().includes(q)) : names

  const handleStart = () => onStart({
    names: activeSelected,
    humanName: playing ? humanName.trim() : null,
    levelId: selectedLevel,
    turnstileToken,
  })

  return (
    <div className="ml-lobby">
      <div className="ml-body">
        <MobileNav />

        {/* Watch / Play chooser — gates the rest of the lobby */}
        <div className={`ml-choose ${mode === null ? 'pulse' : ''}`}>
          <button className={mode === 'watch' && !playOpen ? 'active' : ''} onClick={goWatch}>WATCH</button>
          <button className={mode === 'play' || playOpen ? 'active' : ''} onClick={goPlay}>PLAY</button>
        </div>
        {(playOpen || playClosing) && (
          <div className={`ml-play-row ${playClosing ? 'closing' : ''}`}>
            <input ref={nameInputRef} value={humanName} maxLength={40} placeholder="Your name"
              onChange={e => setHumanName(e.target.value)} />
          </div>
        )}
        {mode === null && !playOpen && (
          <div className="ml-choose-hint">Choose WATCH or PLAY to set up your game.</div>
        )}

        {bodyVisible && <>
        {/* levels */}
        <div style={{ padding: '18px 0' }}>
          <div className="ml-label" style={{ padding: '0 16px 9px' }}>Level</div>
          <div className="ml-levels ml-hscroll" ref={levelsRef}>
            {/* {levels.filter(level => !level.locked).map(level => ( */}
            {levels.map(level => (
              <button key={level.id} data-level={level.id}
                className={`ml-level ${selectedLevel === level.id ? 'selected' : ''} ${level.locked ? 'locked' : ''}`}
                onClick={(e) => { if (level.locked) return; setSelectedLevel(level.id); scrollLevelToStart(e.currentTarget) }} disabled={level.locked}>
                <div className="ml-level-head">
                  <span className="ml-level-name">{level.name}</span>
                  {level.locked && <span style={{ opacity: .6 }}>🔒</span>}
                </div>
                <div className="ml-level-desc">{level.description}</div>
                <div className="ml-level-info">{level.min_players === level.max_players ? level.max_players : `${level.min_players}-${level.max_players}`} players</div>
              </button>
            ))}
          </div>
        </div>

        {/* player tray */}
        {selectedLevel && <div className="ml-tray">
          <div className="ml-label">
            Players ({count}/{maxPlayers}){inactiveCount > 0 && ` +${inactiveCount} inactive`}
          </div>
          <div className="ml-chips">
            {playing && (
              <span className="ml-chip">{humanName || 'You'}<span className="you"> (you)</span>
                <button className="ml-chip-x" onClick={goWatch}>×</button></span>
            )}
            {selected.map((n, i) => (
              <span key={n} className={`ml-chip ${i >= aiCap ? 'inactive' : ''}`}>{n}
                <button className="ml-chip-x" onClick={() => remove(n)}>×</button></span>
            ))}
            {activeSelected.length === 0 && <span className="ml-hint">{aiCap === 1 ? (playing ? 'Select a partner below' : 'Select a player below') : 'Select players below'}</span>}
          </div>
        </div>}

        {/* cast */}
        {selectedLevel && <div style={{ marginTop: 18 }}>
          <div className="ml-cast-sticky">
            <div className="ml-label" style={{ padding: '0 16px 9px' }}>Cast</div>
            <div style={{ padding: '0 16px 10px' }}>
              <div className="ml-search">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <circle cx="5.5" cy="5.5" r="4" stroke="var(--text-dim)" strokeWidth="1.3" />
                  <path d="M8.7 8.7L12 12" stroke="var(--text-dim)" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
                <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search cast…" />
                {query && <button className="ml-x" onClick={() => setQuery('')}>×</button>}
              </div>
            </div>
            {!q && (
              <div className="ml-tabs ml-hscroll">
                {Object.keys(tabs).map(t => (
                  <button key={t} className={`ml-tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>{t}</button>
                ))}
                <button className={`ml-tab ${activeTab === 'Custom' ? 'active' : ''}`} onClick={() => setActiveTab('Custom')}>Custom</button>
              </div>
            )}
          </div>

          {!q && activeTab === 'Custom' && (
            <div className="ml-custom-row" style={{ paddingTop: 12 }}>
              <input value={customInput} maxLength={40} placeholder="Enter a name…"
                onChange={e => setCustomInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') addCustom() }} />
              <button onClick={addCustom}>ADD</button>
            </div>
          )}

          {q && filtered.length === 0 && (
            <div className="ml-add-row">
              <button className="ml-name ml-name-add" onClick={addFromSearch} disabled={selected.length >= selectCap}>
                + Add “{query.trim()}”
              </button>
            </div>
          )}

          <div className="ml-grid">
            {filtered.map(name => {
              const idx = selected.indexOf(name)
              const sel = idx !== -1
              const inactive = sel && idx >= aiCap
              const dis = !sel && selected.length >= selectCap
              const isCustom = !q && activeTab === 'Custom'
              const cls = `ml-name ${sel ? 'selected' : ''} ${inactive ? 'inactive' : ''}`
              return isCustom ? (
                <span key={name} className="ml-name-wrap">
                  <button className={cls} onClick={() => toggle(name)} disabled={dis}>{name}</button>
                  <button className="ml-name-rm" onClick={() => removeCustom(name)}>×</button>
                </span>
              ) : (
                <button key={name} className={cls} onClick={() => toggle(name)} disabled={dis}>{name}</button>
              )
            })}
            {!q && activeTab === 'Custom' && customNames.length === 0 && <span className="ml-hint">Add names above.</span>}
            {!q && activeTab !== 'Custom' && filtered.length === 0 && <span className="ml-hint">No matches.</span>}
          </div>
        </div>}

        {turnstileEnabled && <div className="ml-turnstile" ref={turnstileRef} />}
        </>}
      </div>

      {/* footer */}
      {bodyVisible && (
        <div className="ml-footer">
          <button className="ml-start" disabled={!canStart} onClick={handleStart}>
            {!gameEnabled ? 'COMING SOON' : count < minPlayers ? `SELECT ${need} MORE` : 'START GAME'}
          </button>
        </div>
      )}
    </div>
  )
}
