import { useState, useRef } from 'react'
import { MAX_INPUT_CHARS } from '../utils/settings'

export default function InputRequest({ request, onSubmit }) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const recorderRef = useRef(null)

  const inactive = !request
  const description = request?.description ?? 'Waiting...'

  const submit = (val) => { onSubmit(val); setValue('') }

  const toggleMic = async () => {
    if (listening) {
      recorderRef.current?.stop()
      return
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    const chunks = []
    recorder.ondataavailable = e => chunks.push(e.data)
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      setListening(false)
      const blob = new Blob(chunks, { type: recorder.mimeType })
      const form = new FormData()
      form.append('audio', blob, 'recording.webm')
      const res = await fetch('/api/transcribe', { method: 'POST', body: form })
      const data = await res.json()
      if (data.text) setValue(data.text)
    }
    recorderRef.current = recorder
    recorder.start()
    setListening(true)
  }

  return (
    <div className={`input-bar ${inactive ? 'inactive' : ''}`}>
      <div className="input-prompt">{request?.field ?? 'your turn'} — {description}</div>
      {request?.choices ? (
        <div className="input-choices">
          {request.choices.map(c => (
            <button key={c} className="choice-btn" onClick={() => submit(c)}>{c}</button>
          ))}
        </div>
      ) : (
        <div className="input-row">
          <input
            className="input-text"
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && value.trim()) submit(value.trim()) }}
            placeholder="Type your response..."
            autoFocus={!inactive}
          />
          {value.length > MAX_INPUT_CHARS && (
            <span className="input-truncate-warn">
              {value.length} / {MAX_INPUT_CHARS} — will be truncated
            </span>
          )}
          <button className={`mic-btn ${listening ? 'active' : ''}`} onClick={toggleMic} title="Voice input">
            {listening ? '◼' : '🎙'}
          </button>
          <button className="input-submit" onClick={() => { if (value.trim()) submit(value.trim()) }}>
            Send
          </button>
        </div>
      )}
    </div>
  )
}
