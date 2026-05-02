import { useRef, useEffect, useState } from 'react'
import { Message } from '../components/Messages'
import Scoreboard from '../components/Scoreboard'
import RoundTracker from '../components/RoundTracker'
import RoundWidget from '../components/RoundWidget'
import InputRequest from '../components/InputRequest'
import SegmentTracker from '../components/SegmentTracker'

export default function GameView({
  status, events, scores, evicted,
  inputRequest, awaitingNext, phaseRounds, currentRoundIndex,
  submitInput, sendNext, skipAnimation, onAnimationComplete, skipRef,
  isAnimating, settings, updateSetting, feedMarkers, segmentTitles, widget
}) {
  const { showPrivate, autoRun, animateText } = settings

  const [settingsOpen, setSettingsOpen] = useState(false)
  const settingsRef = useRef(null)
  const colorMapRef = useRef({})
  const bottomRef = useRef(null)
  const feedRef = useRef(null)
  const userScrolledUpRef = useRef(false)
  const leftDragRef = useRef({ startX: 0, startWidth: 0, moved: false })

  const onLeftResizeStart = (e) => {
    const startWidth = settings.leftSidebarWidth ?? 220
    leftDragRef.current = { startX: e.clientX, startWidth, moved: false }

    const onMove = (mv) => {
      const dx = mv.clientX - leftDragRef.current.startX
      if (Math.abs(dx) > 4) leftDragRef.current.moved = true
      const newWidth = Math.max(120, Math.min(500, leftDragRef.current.startWidth + dx))
      updateSetting('leftSidebarWidth', newWidth)
    }

    const onUp = () => {
      if (!leftDragRef.current.moved) {
        updateSetting('leftSidebarOpen', settings.leftSidebarOpen === false ? true : false)
      }
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  const handleFeedScroll = () => {
    const feed = feedRef.current
    if (!feed) return
    // Only re-enable auto-scroll when user scrolls back near the bottom
    if (feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80) {
      userScrolledUpRef.current = false
    }
  }

  const handleFeedWheel = (e) => {
    // Any upward wheel gesture immediately releases auto-scroll
    if (e.deltaY < 0) userScrolledUpRef.current = true
  }

  useEffect(() => {
    if (!settingsOpen) return
    const handler = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) {
        setSettingsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [settingsOpen])

  useEffect(() => {
    if (status !== 'running') return
    const id = setInterval(() => {
      if (!userScrolledUpRef.current) bottomRef.current?.scrollIntoView({ behavior: 'instant' })
    }, 100)
    return () => clearInterval(id)
  }, [status])

  const visibleEvents = showPrivate
    ? events
    : events.filter(e => e.type !== 'private_thought' && e.type !== 'system_private')

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">THE GAME</h1>
        <div className="header-controls">
          <div className="settings-menu" ref={settingsRef}>
            <button className="gear-btn" onClick={() => setSettingsOpen(o => !o)}>⚙</button>
            {settingsOpen && (
              <div className="settings-dropdown">
                <label className="toggle-label">
                  <input type="checkbox" checked={showPrivate} onChange={e => updateSetting('showPrivate', e.target.checked)} />
                  Show private thoughts
                </label>
                <label className="toggle-label">
                  <input type="checkbox" checked={autoRun} onChange={e => updateSetting('autoRun', e.target.checked)} />
                  Auto-run
                </label>
                <label className="toggle-label">
                  <input type="checkbox" checked={animateText} onChange={e => updateSetting('animateText', e.target.checked)} />
                  Animate text
                </label>
              </div>
            )}
          </div>
          {(() => {
            const skipOrNext = isAnimating
              ? { label: 'Skip ›', action: skipAnimation, active: true }
              : { label: 'Next Turn ›', action: sendNext, active: awaitingNext && !autoRun }
            return (
              <button className="next-turn-btn" onClick={skipOrNext.action} disabled={!skipOrNext.active}>
                {skipOrNext.label}
              </button>
            )
          })()}
          <span className={`start-btn status-${status}`} style={{ cursor: 'default' }}>
            {status === 'connecting' && 'Connecting…'}
            {status === 'running' && (awaitingNext && !autoRun && !isAnimating ? 'Waiting…' : 'Running…')}
            {status === 'done' && '✓ Done'}
            {status === 'error' && '⚠ Error'}
          </span>
        </div>
      </header>

      <div className="app-body">
        <aside
          className={`sidebar-left ${settings.leftSidebarOpen === false ? 'collapsed' : ''}`}
          style={{ width: settings.leftSidebarOpen === false ? 0 : (settings.leftSidebarWidth ?? 220) }}
        >
          <div className="round-info">
            {phaseRounds.length > 0
              ? <p className="round-info-name">{phaseRounds[currentRoundIndex]}</p>
              : <p className="round-info-empty">—</p>
            }
          </div>
          <RoundWidget widget={widget} />
          <SegmentTracker titles={segmentTitles} markers={feedMarkers} />

        </aside>
        <button
          className="sidebar-toggle sidebar-toggle-left"
          onMouseDown={onLeftResizeStart}
          style={{ cursor: 'col-resize' }}
        >
          {settings.leftSidebarOpen === false ? '›' : '‹'}
        </button>

        <div className="feed-col">
          <main className="feed" ref={feedRef} onScroll={handleFeedScroll} onWheel={handleFeedWheel}>
            {visibleEvents.map((evt, i) => (
              <Message
                key={i}
                event={evt}
                colorMap={colorMapRef.current}
                onComplete={i === visibleEvents.length - 1 ? onAnimationComplete : undefined}
                skipRef={i === visibleEvents.length - 1 ? skipRef : undefined}
                animateText={animateText}
              />
            ))}
            <div ref={bottomRef} />
          </main>
          <InputRequest request={inputRequest} onSubmit={submitInput} />
        </div>

        <button
          className="sidebar-toggle"
          onClick={() => updateSetting('sidebarOpen', settings.sidebarOpen === false ? true : false)}
        >
          {settings.sidebarOpen === false ? '‹' : '›'}
        </button>
        <aside className={`sidebar ${settings.sidebarOpen === false ? 'collapsed' : ''}`}>
          <Scoreboard scores={scores} evicted={evicted} />
          <RoundTracker rounds={phaseRounds} currentIndex={currentRoundIndex} />
        </aside>
      </div>
    </div>
  )
}
