import { useState } from 'react'
import './App.css'
import { loadSettings, saveSettings } from './utils/settings'
import { useGameSocket } from './hooks/useGameSocket'
import Lobby from './pages/Lobby'
import DemosPage from './pages/DemosPage'
import GameView from './pages/GameView'

export default function App() {
  const [view, setView] = useState('lobby')
  const [settings, setSettings] = useState(loadSettings)

  const updateSetting = (key, value) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value }
      saveSettings(next)
      return next
    })
  }

  const socket = useGameSocket(settings.autoRun, settings.animateText)
  const { status, startGame, startDemo } = socket

  if (status !== 'idle') {
    return <GameView {...socket} settings={settings} updateSetting={updateSetting} />
  }

  return (
    <>
      {status === 'idle' && (
        <>
          <nav className="main-nav">
            <button className={`nav-btn ${view === 'lobby' ? 'active' : ''}`} onClick={() => setView('lobby')}>Game</button>
            <button className={`nav-btn ${view === 'demos' ? 'active' : ''}`} onClick={() => setView('demos')}>Demos</button>
          </nav>
          {view === 'lobby' ? <Lobby onStart={startGame} /> : <DemosPage onStart={startDemo} />}
        </>
      )}
    </>
  )
}
