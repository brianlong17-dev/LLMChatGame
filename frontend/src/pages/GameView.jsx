import { useRef, useEffect, useState } from 'react'
import { Message } from '../components/Messages'
import Scoreboard from '../components/Scoreboard'
import RoundTracker from '../components/RoundTracker'
import RoundWidget from '../components/RoundWidget'
import InputRequest from '../components/InputRequest'
import SegmentTracker from '../components/SegmentTracker'
import PrivateChatsPanel from '../components/PrivateChatsPanel'

export default function GameView({
  status, events, scores, evicted,
  inputRequest, awaitingNext, phaseRounds, currentRoundIndex,
  submitInput, sendNext, skipAnimation, onAnimationComplete, skipRef,
  isAnimating, settings, updateSetting, feedMarkers, segmentTitles, widget,
  privateConversations,
}) {
  const { showPrivate, autoRun, animateText, showPrivateChats } = settings

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('feed')
  const [seenPrivateCount, setSeenPrivateCount] = useState(0)
  const settingsRef = useRef(null)
  const colorMapRef = useRef({})
  const bottomRef = useRef(null)
  const feedRef = useRef(null)
  const privateBottomRef = useRef(null)
  const lastSeenPrivateCountRef = useRef(0)
  const userScrolledUpRef = useRef(false)
  const lastScrollTopRef = useRef(0)
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
    const distFromBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight
    const movedUp = feed.scrollTop < lastScrollTopRef.current - 1
    lastScrollTopRef.current = feed.scrollTop

    if (distFromBottom < 80) {
      userScrolledUpRef.current = false
    } else if (movedUp) {
      userScrolledUpRef.current = true
    }
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

  useEffect(() => {
    if (activeTab !== 'private') return
    if (privateConversations.length > lastSeenPrivateCountRef.current) {
      lastSeenPrivateCountRef.current = privateConversations.length
      privateBottomRef.current?.scrollIntoView({ behavior: 'instant' })
    }
  }, [privateConversations, activeTab])

  const visibleEvents = showPrivate
    ? events
    : events.filter(e => e.type !== 'private_thought' && e.type !== 'system_private')

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">THE GAME</h1>
          {showPrivateChats && (
            <div className="header-tabs">
              <button className={`header-tab${activeTab === 'feed' ? ' active' : ''}`} onClick={() => setActiveTab('feed')}>
                Main Feed
              </button>
              <button className={`header-tab${activeTab === 'private' ? ' active' : ''}`} onClick={() => { setActiveTab('private'); setSeenPrivateCount(privateConversations.length) }}>
                Private Conversations
                {privateConversations.length > seenPrivateCount && <span className="feed-tab-badge">{privateConversations.length - seenPrivateCount}</span>}
              </button>
            </div>
          )}
        </div>
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
                <label className="toggle-label">
                  <input type="checkbox" checked={showPrivateChats} onChange={e => updateSetting('showPrivateChats', e.target.checked)} />
                  Show private conversations
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
          <main
            className="feed"
            ref={feedRef}
            onScroll={handleFeedScroll}
            style={{ display: showPrivateChats && activeTab === 'private' ? 'none' : undefined }}
          >
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
          {showPrivateChats && (
            <main
              className="feed"
              style={{ display: activeTab === 'private' ? undefined : 'none' }}
            >
              <PrivateChatsPanel conversations={privateConversations} colorMap={colorMapRef.current} />
              <div ref={privateBottomRef} />
            </main>
          )}
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
