import { useState, useRef } from 'react'
import { MAX_INPUT_CHARS } from '../utils/settings'

export default function InputRequest({ request, onSubmit }) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const recorderRef = useRef(null)

  const textareaRef = useRef(null)
  const inactive = !request
  const description = request?.description ?? 'Waiting...'

  const submit = (val) => { onSubmit(val); setValue(''); resetHeight() }

  const resetHeight = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
  }

  const handleChange = (e) => {
    setValue(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  }

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
          <textarea
            ref={textareaRef}
            className="input-text"
            value={value}
            onChange={handleChange}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && value.trim()) { e.preventDefault(); submit(value.trim()) } }}
            placeholder="Type your response..."
            autoFocus={!inactive}
            rows={1}
          />
          {value.length > MAX_INPUT_CHARS && (
            <span className="input-truncate-warn">
              {value.length} / {MAX_INPUT_CHARS} — will be truncated
            </span>
          )}
          <button className={`mic-btn ${listening ? 'active' : ''}`} onClick={toggleMic} title="Voice input">
            {listening
              ? (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <rect x="2" y="2" width="10" height="10" fill="currentColor" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  {/* capsule */}
                  <rect x="4.5" y="1" width="5" height="7" rx="2.5" stroke="currentColor" strokeWidth="1.2" />
                  {/* stand arc */}
                  <path d="M2.5 7.5C2.5 10.0376 4.46243 12 7 12C9.53757 12 11.5 10.0376 11.5 7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
                  {/* stem */}
                  <line x1="7" y1="12" x2="7" y2="13.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
                  {/* base */}
                  <line x1="4.5" y1="13.5" x2="9.5" y2="13.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="square" />
                </svg>
              )
            }
          </button>
          <button className="input-submit" onClick={() => { if (value.trim()) submit(value.trim()) }}>
            Send
          </button>
        </div>
      )}
    </div>
  )
}
