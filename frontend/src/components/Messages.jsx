import { useState, useEffect, useRef } from 'react'

const SPEAKER_COLORS = [
  '#e07b54', '#5b8dd9', '#67b37d', '#c97bc4',
  '#d4a84b', '#5bbccc', '#d9706a', '#8d7fd9',
]

export function getSpeakerColor(name, colorMap) {
  if (!colorMap[name]) {
    const idx = Object.keys(colorMap).length % SPEAKER_COLORS.length
    colorMap[name] = SPEAKER_COLORS[idx]
  }
  return colorMap[name]
}

function WordByWord({ text, onComplete, skipRef, animateText }) {
  const [typed, setTyped] = useState('')
  const [snapped, setSnapped] = useState('')
  const [dots, setDots] = useState('')
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])
  useEffect(() => {
    setTyped('')
    setSnapped('')
    setDots('')
    let timeoutId = null

    if (!animateText) {
      setTyped(text)
      onCompleteRef.current?.()
      return
    }

    const snap = () => {
      clearTimeout(timeoutId)
      setTyped(text)
      setSnapped('')
      setDots('')
      onCompleteRef.current?.()
    }

    const checkSkip = () => {
      if (skipRef?.current) { snap(); return true }
      return false
    }

    const paragraphs = text.split('\n\n')

    const showDots = (onDone) => {
      const steps = ['.', '..', '...']
      let i = 0
      const tick = () => {
        if (checkSkip()) return
        setDots(steps[i]); i++
        if (i < steps.length) timeoutId = setTimeout(tick, 400)
        else timeoutId = setTimeout(() => { setDots(''); onDone() }, 600)
      }
      timeoutId = setTimeout(tick, 300)
    }

    const splitSentences = (para) =>
      para.match(/[^.!?]+[.!?]+[\s]*/g) || [para]

    const runParagraph = (paraIdx, onDone) => {
      if (paraIdx >= paragraphs.length) return
      if (checkSkip()) return
      const para = paragraphs[paraIdx]
      const prefix = paragraphs.slice(0, paraIdx).join('\n\n') + (paraIdx > 0 ? '\n\n' : '')
      const sentences = splitSentences(para)
      const isLast = paraIdx === paragraphs.length - 1

      const runSentence = (sentIdx, soFar) => {
        if (checkSkip()) return
        if (sentIdx >= sentences.length) {
          if (isLast) { onDone(); return }
          showDots(onDone)
          return
        }
        if (sentIdx >= 3) {
          const rest = sentences.slice(sentIdx).join('')
          setSnapped(rest)
          timeoutId = setTimeout(() => {
            if (checkSkip()) return
            setTyped(prefix + para)
            setSnapped('')
            if (isLast) { onDone(); return }
            showDots(onDone)
          }, 400)
          return
        }
        const sentence = sentences[sentIdx]
        const words = sentence.split(/(\s+)/)
        const wordCount = words.filter(w => w.trim()).length || 1
        const wordDelay = Math.round(500 / wordCount)
        let wordIdx = 0
        const tickWord = () => {
          if (checkSkip()) return
          wordIdx++
          const current = soFar + words.slice(0, wordIdx).join('')
          setTyped(prefix + current)
          if (wordIdx < words.length) timeoutId = setTimeout(tickWord, wordDelay)
          else timeoutId = setTimeout(() => runSentence(sentIdx + 1, current), 300)
        }
        tickWord()
      }

      runSentence(0, '')
    }

    const runAll = (paraIdx) => {
      if (paraIdx >= paragraphs.length) {
        onCompleteRef.current?.()
        return
      }
      runParagraph(paraIdx, () => runAll(paraIdx + 1))
    }

    timeoutId = setTimeout(() => runAll(0), 80)
    return () => clearTimeout(timeoutId)
  }, [text])

  return (
    <span style={{ whiteSpace: 'pre-wrap' }}>
      {typed}
      {snapped && <span style={{ animation: 'fadeIn 0.4s ease forwards' }}>{snapped}</span>}
      {dots && <span style={{ color: 'var(--text-dim)', marginLeft: 2 }}>{dots}</span>}
    </span>
  )
}

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

function PublicAction({ speaker, message, color, animate, onComplete, skipRef, animateText}) {
  //so -- i believe that animate should come from the backend 
  const isSystem = speaker === 'SYSTEM' || speaker === 'HOST'
  return (
    <div className={`msg public-action ${isSystem ? 'system' : ''}`}>
      {!isSystem && <span className="speaker" style={{ color }}>{speaker}</span>}
      {isSystem && <span className="speaker system-speaker">{speaker}</span>}
      {animate
        ? <WordByWord text={message} onComplete={onComplete} skipRef={skipRef} animateText={animateText} />
        : <span className="message-text">{message}</span>
      }
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

function LoadingMessage({ message }) {
  return (
    <div className="msg loading-message">
      <span className="loading-text">{message}</span>
      <span className="loading-dot" style={{ animationDelay: '0s' }}>.</span>
      <span className="loading-dot" style={{ animationDelay: '0.2s' }}>.</span>
      <span className="loading-dot" style={{ animationDelay: '0.4s' }}>.</span>
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

function FeedMarker({ label }) {
  const id = `feed-${label.toLowerCase().replace(/\s+/g, '-')}`
  return <div id={id} style={{ height: 0 }} />
}

export function Message({ event, colorMap, onComplete, skipRef, animateText}) {
  switch (event.type) {
    case 'phase_header':
      return <PhaseHeader {...event} />
    case 'round_start':
      return <RoundHeader {...event} />
    case 'public_action':
      return <PublicAction {...event} color={getSpeakerColor(event.speaker, colorMap)} onComplete={onComplete} skipRef={skipRef} 
      animateText={animateText}/>
    case 'round_summary':
      return <RoundSummary {...event} />
    case 'private_thought':
      return <PrivateThought {...event} color={getSpeakerColor(event.speaker, colorMap)} />
    case 'system_private':
      return <SystemPrivate {...event} />
    case 'game_intro':
      return <PublicAction speaker="HOST" message={event.message} color="#aaa" />
    case 'game_over':
      return <GameOver winner={event.winner} />
    case 'error':
      return <ErrorMsg message={event.message} />
    case 'loading':
      return <LoadingMessage message={event.message} />
    case 'feed_marker':
      return <FeedMarker label={event.label} />
    case 'points_update':
    case 'turn_header':
    case 'phase_intro':
    case 'evicted_update':
    case 'loading_done':
    default:
      return null
  }
}
