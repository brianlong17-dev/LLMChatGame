function slugify(label) {
  return `feed-${label.toLowerCase().replace(/\s+/g, '-')}`
}

export default function SegmentTracker({ titles, markers }) {
  if (!titles || titles.length === 0) return null

  const lastArrivedIndex = titles.reduce((acc, title, i) =>
    markers.includes(title) ? i : acc, -1)

  const scrollTo = (label) => {
    document.getElementById(slugify(label))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="segment-tracker">
      <ul className="segment-list">
        {titles.map((label, i) => {
          const done = i < lastArrivedIndex
          const active = i === lastArrivedIndex
          const clickable = markers.includes(label)
          return (
            <li
              key={i}
              className={`segment-item ${done ? 'done' : ''} ${active ? 'active' : ''} ${clickable ? 'clickable' : ''}`}
              onClick={clickable ? () => scrollTo(label) : undefined}
            >
              <span className="segment-arrow">{active ? '›' : ''}</span>
              <span className="segment-name">{label}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
