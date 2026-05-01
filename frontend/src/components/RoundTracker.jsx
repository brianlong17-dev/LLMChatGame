export default function RoundTracker({ rounds, currentIndex }) {
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
