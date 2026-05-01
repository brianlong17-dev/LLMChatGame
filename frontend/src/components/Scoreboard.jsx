export default function Scoreboard({ scores, evicted }) {
  if (!scores || Object.keys(scores).length === 0) return null
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1])
  return (
    <div className="scoreboard">
      <h2 className="scoreboard-title">Scores</h2>
      <ol className="score-list">
        {sorted.map(([name, score], i) => (
          <li key={name} className="score-row">
            <span className="score-rank">{i + 1}</span>
            <span className="score-name">{name}</span>
            <span className="score-pts">{score}</span>
          </li>
        ))}
      </ol>
      <div className="graveyard">
        <h2 className="scoreboard-title">Graveyard</h2>
        {evicted.map(name => (
          <div key={name} className="evicted-row"> ☠ {name}</div>
        ))}
      </div>
    </div>
  )
}
