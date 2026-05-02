/**
 * RoundWidget — context-aware left-sidebar widget.
 *
 * Driven by `widget_update` events from the server.
 * Server sends: { type: 'widget_update', widget: { kind, ...data } }
 *
 * Supported kinds:
 *   'voting' — live vote tally
 *     data: {
 *       nominees: [{ name, votes }],
 *       voters_done: [{ name, voted_for } | string],
 *       voters_pending: string[],
 *       is_final: boolean,  // true → winner gets gold + sparks
 *     }
 */

import { useEffect, useRef, useState } from 'react'

const GOLD_COLORS = ['#f5d376','#c9a84c','#e8c050','#fbeaa0','#a07820']
const BLOOD_COLORS = ['#8b1a1a','#a02020','#c0392b','#7b1010','#6b0f0f']

const THEME = {
  gold:  { winner: '#c9a84c', sparks: GOLD_COLORS },
  blood: { winner: '#c0392b', sparks: BLOOD_COLORS },
}

function SparkCanvas({ colors = GOLD_COLORS }) {
  const canvasRef = useRef(null)
  const rafRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const particles = []

    const spawn = () => {
      const x = Math.random() * canvas.width
      particles.push({
        x, y: 0,
        vx: (Math.random() - 0.5) * 0.4,
        vy: Math.random() * 0.7 + 0.2,
        life: 1,
        decay: Math.random() * 0.025 + 0.018,
        size: Math.random() * 0.9 + 0.3,
        color: colors[Math.floor(Math.random() * colors.length)],
        trail: [],
      })
    }

    const tick = () => {
      // Size canvas once DOM is ready
      if (!canvas._sized && canvas.offsetWidth > 0) {
        canvas.width = canvas.offsetWidth
        canvas.height = canvas.offsetHeight || 120
        canvas._sized = true
      }

      const spawnCount = Math.floor(Math.random() * 2) + 1
      for (let i = 0; i < spawnCount; i++) spawn()

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i]
        p.trail.push({ x: p.x, y: p.y, life: p.life })
        if (p.trail.length > 6) p.trail.shift()

        p.x += p.vx
        p.vy += 0.02
        p.vx *= 0.995
        p.y += p.vy
        p.life -= p.decay

        if (p.life <= 0 || p.y > canvas.height) { particles.splice(i, 1); continue }

        for (let t = 0; t < p.trail.length; t++) {
          const tp = p.trail[t]
          ctx.beginPath()
          ctx.arc(tp.x, tp.y, p.size * 0.5, 0, Math.PI * 2)
          ctx.fillStyle = p.color
          ctx.globalAlpha = (t / p.trail.length) * p.life * 0.2
          ctx.fill()
        }

        const s = p.size * 1.6
        ctx.fillStyle = p.color
        ctx.globalAlpha = p.life * 0.6
        ctx.fillRect(p.x - s / 2, p.y - s / 2, s, s)

        if (Math.random() < 0.02) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.size * 2, 0, Math.PI * 2)
          ctx.fillStyle = '#fff8d0'
          ctx.globalAlpha = p.life * 0.15
          ctx.fill()
        }
      }

      ctx.globalAlpha = 1
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(rafRef.current)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
    }
  }, [colors])

  return (
    <div style={{ position: 'relative', height: 0, overflow: 'visible', pointerEvents: 'none' }}>
      <canvas
        ref={canvasRef}
        width="196"
        height="120"
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 120, pointerEvents: 'none' }}
      />
    </div>
  )
}

function VoterSection({ voters_done, voters_pending, totalVoters }) {
  const [allOpen, setAllOpen] = useState(false)
  const [openSet, setOpenSet] = useState(new Set())

  const toggleAll = () => {
    if (allOpen) {
      setAllOpen(false)
      setOpenSet(new Set())
    } else {
      setAllOpen(true)
      setOpenSet(new Set(voters_done.map(v => typeof v === 'string' ? v : v.name)))
    }
  }

  const toggleOne = (name) => {
    setOpenSet(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div className="rw-section">
      <h3 className="rw-label rw-label-toggle" onClick={toggleAll}>
        Voted
        <span className="rw-label-count">{voters_done.length}/{totalVoters}</span>
      </h3>
      <div className="rw-voters">
        {voters_done.map(v => {
          const name = typeof v === 'string' ? v : v.name
          const voted_for = typeof v === 'string' ? null : v.voted_for
          const isOpen = openSet.has(name)
          return (
            <div
              key={name}
              className={`rw-voter rw-voter--done ${isOpen ? 'expanded' : ''}`}
              onClick={() => voted_for && toggleOne(name)}
            >
              <div className="rw-voter-row">
                <span className="rw-voter-tick">›</span>
                <span className="rw-voter-name">{name}</span>
              </div>
              {isOpen && voted_for && (
                <div className="rw-voter-voted-for">↳ {voted_for}</div>
              )}
            </div>
          )
        })}
        {voters_pending.map(v => {
          const name = typeof v === 'string' ? v : v.name
          return (
            <div key={name} className="rw-voter rw-voter--pending">
              <div className="rw-voter-row">
                <span className="rw-voter-tick"> </span>
                <span className="rw-voter-name">{name}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function VotingWidget({ nominees = [], voters_done = [], voters_pending = [], is_final = false, theme = 'gold' }) {
  const totalVoters = voters_done.length + voters_pending.length
  const sorted = [...nominees].sort((a, b) => (b.votes || 0) - (a.votes || 0))
  const maxVotes = sorted[0]?.votes || 1
  const t = THEME[theme] || THEME.gold

  return (
    <div className="round-widget">
      <div className="rw-section">
        <h3 className="rw-label">Vote</h3>
        <div className="rw-nominees">
          {sorted.map(({ name, votes = 0 }) => {
            const pct = maxVotes > 0 ? (votes / maxVotes) * 100 : 0
            const isLeading = votes === maxVotes && votes > 0
            const isWinner = is_final && isLeading
            const winnerColor = isWinner ? t.winner : undefined
            return (
              <div key={name} className={`rw-nominee ${isWinner ? 'winner' : (isLeading ? 'leading' : '')}`}
                   style={winnerColor ? { '--winner-color': winnerColor } : {}}>
                <div className="rw-nominee-header">
                  <span className="rw-nominee-name">{name}</span>
                  <span className="rw-nominee-count">{votes}</span>
                </div>
                <div className="rw-bar-track">
                  <div className="rw-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                {isWinner && <SparkCanvas colors={t.sparks} />}
              </div>
            )
          })}
        </div>
      </div>

      {(voters_done.length > 0 || voters_pending.length > 0) && (
        <VoterSection
          voters_done={voters_done}
          voters_pending={voters_pending}
          totalVoters={totalVoters}
        />
      )}
    </div>
  )
}

export default function RoundWidget({ widget }) {
  if (!widget || !widget.kind) return null
  switch (widget.kind) {
    case 'voting': return <VotingWidget {...widget} />
    default: return null
  }
}
