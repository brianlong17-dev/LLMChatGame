import { useState } from 'react'

const DEMOS = [
  {
    id: 'reunion_3',
    title: 'Reunion Finale — Game 3',
    description: 'Tied 39–39. Avatar Aang vs Morty Smith. The jury decides who wins.',
    cast: ['Avatar Aang', 'Morty Smith', 'HAL 9000', 'Michael Jackson', 'Amy March', 'Benoit Blanc', 'Buffy Summers', 'Gollum', 'Lady Macbeth', 'Jo March', 'Lady Dianna'],
  },
  {
    id: 'reunion_2',
    title: 'Reunion Finale — Game 2',
    description: 'Amy March (41) vs Lady Dianna (48). The jury has the final say.',
    cast: ['Amy March', 'Lady Dianna', 'Morty Smith', 'Lady Macbeth', 'HAL 9000', 'Jo March', 'Michael Jackson', 'Avatar Aang', 'Gollum', 'Buffy Summers', 'Benoit Blanc'],
  },
  {
    id: 'game_phase',
    title: 'Game Phase',
    description: 'A full Knives + Vote round from mid-game state. 11 real players.',
    cast: ['Aang', 'Michael Jackson', 'HAL 9000', 'Jo March', 'Lady Macbeth', 'Lady Diana', 'Morty Smith', 'Amy March', 'Benoit Blanc', 'Gollum', 'Buffy Summers'],
    locked: false,
  },
]

function DemoCard({ demo, onStart }) {
  const [mode, setMode] = useState('watch')
  const [humanName, setHumanName] = useState('')

  const canStart = mode === 'watch' || humanName.trim()

  if (demo.locked) {
    return (
      <div className="demo-card demo-card--locked">
        <span className="demo-locked-badge">Coming Soon</span>
        <h2 className="demo-title">{demo.title}</h2>
        <p className="demo-description">{demo.description}</p>
        <div className="demo-cast">
          {demo.cast.map(name => (
            <span key={name} className="demo-cast-chip">{name}</span>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="demo-card">
      <h2 className="demo-title">{demo.title}</h2>
      <p className="demo-description">{demo.description}</p>
      <div className="demo-cast">
        {demo.cast.map(name => (
          <span
            key={name}
            className={`demo-cast-chip demo-cast-chip--clickable${humanName === name && mode === 'play' ? ' demo-cast-chip--selected' : ''}`}
            onClick={() => { setMode('play'); setHumanName(name) }}
          >{name}</span>
        ))}
      </div>
      <div className="demo-mode">
        <label className="mode-opt">
          <input type="radio" name={`mode-${demo.id}`} value="watch" checked={mode === 'watch'} onChange={() => setMode('watch')} />
          Watch
        </label>
        <label className="mode-opt">
          <input type="radio" name={`mode-${demo.id}`} value="play" checked={mode === 'play'} onChange={() => setMode('play')} />
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
        onClick={() => onStart({ demoId: demo.id, humanName: mode === 'play' ? humanName.trim() : null })}
      >
        Run Demo
      </button>
    </div>
  )
}

export default function DemosPage({ onStart }) {
  return (
    <div className="demos-page">
      <h1 className="lobby-title">Demos</h1>
      <p className="demos-subtitle">Pre-loaded game scenarios from real playthroughs.</p>
      <div className="demos-grid">
        {DEMOS.map(demo => (
          <DemoCard key={demo.id} demo={demo} onStart={onStart} />
        ))}
      </div>
    </div>
  )
}
