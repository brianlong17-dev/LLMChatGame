import { getSpeakerColor } from './Messages'

export default function PrivateChatsPanel({ conversations, colorMap }) {
  if (conversations.length === 0)
    return <div className="private-empty">No private conversations yet.</div>

  return (
    <div className="private-chats">
      {conversations.map((conv, i) => (
        <div key={i} className="private-conv">
          <div className="private-conv-header">
            {conv.participants.join(' & ')}
          </div>
          {conv.messages.map((m, j) => (
            <div key={j} className="private-conv-msg">
              <span className="private-speaker" style={{ color: getSpeakerColor(m.speaker, colorMap) }}>
                {m.speaker}
              </span>
              <span className="private-msg-text">{m.message}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
