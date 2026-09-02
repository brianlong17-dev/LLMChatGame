import { useState, useRef, useCallback, useEffect } from 'react'

const WS_GAME_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/game`
const WS_DEMO_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/demo`
const WS_REPLAY_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/replay`

function isAnimatableEvent(evt, animateText) {
  if (!animateText) return false
  if (evt.type === 'round_start') return true
  if (evt.type !== 'public_action' || evt.is_human) return false
  if (evt.tutorial_message) return false
  return evt.animate_as_player === true || evt.speaker === 'HOST'
}

function mergeCommentary(events, evt) {
  const entry = { speaker: evt.speaker, message: evt.message }
  const idx = events.findIndex(e => e.type === 'summary_commentary' && e.phase_id === evt.phase_id)
  if (idx === -1) return [...events, { type: 'summary_commentary', phase_id: evt.phase_id, entries: [entry] }]
  return events.map((e, i) => i === idx ? { ...e, entries: [...e.entries, entry] } : e)
}

export function useGameSocket(autoRun, animateText, mobileOutputs) {
  const [status, setStatus] = useState('idle')
  const [events, setEvents] = useState([])
  const [scores, setScores] = useState(null)
  const [evicted, setEvicted] = useState([])
  const [inputRequest, setInputRequest] = useState(null)
  const [awaitingNext, setAwaitingNext] = useState(false)
  const [awaitingNextRound, setAwaitingNextRound] = useState(false)
  

  const [phaseRounds, setPhaseRounds] = useState([])
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0)
  const [feedMarkers, setFeedMarkers] = useState([])
  const [segmentTitles, setSegmentTitles] = useState([])
  const [widget, setWidget] = useState(null)
  const [privateConversations, setPrivateConversations] = useState([])
  const [playerNames, setPlayerNames] = useState([])
  const [typingMessage, setTypingMessage] = useState(null)

  const wsRef = useRef(null)
  const lastConnectRef = useRef(null)
  const transcribePendingRef = useRef(null)
  const autoRunRef = useRef(autoRun)
  useEffect(() => {
    autoRunRef.current = autoRun
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify({ type: 'set_flag', flag: 'auto_run', value: autoRun }))
  }, [autoRun])

  const animateTextRef = useRef(animateText)
  useEffect(() => { animateTextRef.current = animateText }, [animateText])

  const mobileOutputsRef = useRef(mobileOutputs)
  useEffect(() => {
    mobileOutputsRef.current = mobileOutputs
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify({ type: 'set_flag', flag: 'mobile_outputs', value: mobileOutputs }))
  }, [mobileOutputs])

  const [isAnimatingState, setIsAnimatingState] = useState(false)

  const pendingQueue = useRef([])
  const isAnimating = useRef(false)
  const skipRef = useRef(false)
  const awaitingNextRef = useRef(false)
  const releaseOneRef = useRef(false)
  const firstPlayerMessageSeenRef = useRef(false)
  const awaitingNextRoundRef = useRef(false)
  const statusRef = useRef(status)
  useEffect(() => { statusRef.current = status }, [status])
  const drainDelayRef = useRef(0)
  const pacingRef = useRef(false)

  //are we paused?
  //isAnimating or waitingForUserToPressNextTurn
  //waitingForUserToPressNextRound


  const drainQueue = useCallback(() => {
    while (pendingQueue.current.length > 0) {
      const peek = pendingQueue.current[0]
      if (isAnimating.current) break
      if (awaitingNextRef.current && peek.type !== 'private_thought') break

      if (awaitingNextRoundRef.current) break

      if (pacingRef.current) break

      
      
      if (!autoRunRef.current && peek.type === 'public_action' && peek.should_hold && !peek.is_human) {
        if (!firstPlayerMessageSeenRef.current) {
          firstPlayerMessageSeenRef.current = true
        } else if (releaseOneRef.current) {
          releaseOneRef.current = false
        } else {
          awaitingNextRef.current = true
          setAwaitingNext(true)
          break
        }
      }

      // Yay! we're through the breaks ! Lets get something out the queue! 

      const evt = pendingQueue.current.shift()
      if (evt.type === 'public_action' && evt.widget) setWidget(evt.widget)
      if (evt.type === 'input_form_request') { setInputRequest(evt); return }

      if (evt.type === 'delay') {
        if (evt.ms > 0) {
          pacingRef.current = true
          setTimeout(() => { pacingRef.current = false; drainQueue() }, evt.ms)
          break
        }
        continue
      }

      if (evt.type === 'points_update') { setScores(evt.scores); continue }
      
      if (evt.type === 'evicted_update') { setEvicted(evt.evicted_names); continue }
      if (evt.type === 'widget_update') { setWidget(evt.widget ?? null); continue }
      if (evt.type === 'phase_rounds') { setPhaseRounds(evt.rounds); setCurrentRoundIndex(0); continue }
      if (evt.type === 'phase_round_index') { setCurrentRoundIndex(evt.index); setFeedMarkers([]); setSegmentTitles([]); setWidget(null); continue }
      if (evt.type === 'set_segments') { setSegmentTitles(evt.titles); continue }
      if (evt.type === 'summary_commentary') { setEvents(prev => mergeCommentary(prev, evt)); continue }
      if (evt.type === 'feed_marker') {
        setFeedMarkers(prev => [...prev, evt.label])
        setEvents(prev => [...prev, evt])
        continue
      }

      if (evt.tutorial_message && evt.tutorial_hold) {
        awaitingNextRef.current = true
        setAwaitingNext(true)
      }

      if (evt.type === 'next_round_request') {
        awaitingNextRoundRef.current = true
        setAwaitingNextRound(true)
        setEvents(prev => [...prev, evt])
        break
      }

      if (isAnimatableEvent(evt, animateTextRef.current)) {
        isAnimating.current = true
        setIsAnimatingState(true)
        setEvents(prev => [...prev, evt])
        break
      }
      
      setEvents(prev => [...prev, evt])

      if (drainDelayRef.current > 0 && evt.type === 'public_action') {
        pacingRef.current = true
        setTimeout(() => { pacingRef.current = false; drainQueue() }, drainDelayRef.current)
        break
      }
    }
  },  [setScores, setEvicted])

  const onAnimationComplete = useCallback(() => {
    isAnimating.current = false
    setIsAnimatingState(false)
    skipRef.current = false
    drainQueue()
  }, [drainQueue])

  useEffect(() => {
    if (!animateText && isAnimating.current) {
      skipRef.current = true
    }
  }, [animateText])

  
  useEffect(() => {
    if (autoRun) {
      awaitingNextRef.current = false
      setAwaitingNext(false)
      drainDelayRef.current = statusRef.current === 'done' ? 5 : 0
      drainQueue()
    }
  }, [autoRun])

  const handleMessage = useCallback((e) => {
    const evt = JSON.parse(e.data)

    if (evt.type === 'private_conversation') {
      setPrivateConversations(prev => [...prev, { participants: evt.participants ?? [], messages: evt.messages }])
      return
    }
    if (evt.type === 'transcription') {
      const resolve = transcribePendingRef.current
      transcribePendingRef.current = null
      resolve?.(evt.text || '')
      return
    }
    if (evt.type === 'cast') { setPlayerNames(evt.names ?? []); return }
    if (evt.type === 'is_typing') { setTypingMessage(evt.message || null); return }
    if (evt.type === 'loading') { setEvents(prev => [...prev, evt]); return }
    if (evt.type === 'loading_done') {
      setEvents(prev => {
        const idx = prev.map(e => e.type === 'loading' && !e.done).lastIndexOf(true)
        if (idx === -1) return prev
        return prev.map((e, i) => i === idx ? { ...e, done: true, completed_message: evt.message ?? null } : e)
      })
      return
    }
        
    if (evt.type === 'game_over') setStatus('done')
    if (evt.type === 'error') setStatus('error')
    pendingQueue.current.push(evt)
    drainQueue()
  }, [drainQueue])

  const connect = useCallback((wsUrl, initMsg) => {
    if (wsRef.current) return
    lastConnectRef.current = { wsUrl, initMsg }
    setStatus('connecting')
    setEvents([])
    setScores(null)
    setEvicted([])
    setFeedMarkers([])
    setSegmentTitles([])
    setWidget(null)
    setPrivateConversations([])
    setPlayerNames([])
    setTypingMessage(null)
    pendingQueue.current = []
    isAnimating.current = false
    setIsAnimatingState(false)
    skipRef.current = false
    awaitingNextRef.current = false
    awaitingNextRoundRef.current = false
    firstPlayerMessageSeenRef.current = false
    setAwaitingNextRound(false)
    setAwaitingNext(false)
    drainDelayRef.current = 0
    pacingRef.current = false

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify(initMsg))
      ws.send(JSON.stringify({ type: 'set_flag', flag: 'mobile_outputs', value: mobileOutputsRef.current }))
      ws.send(JSON.stringify({ type: 'set_flag', flag: 'auto_run', value: autoRunRef.current }))
      setStatus('running')
    }
    ws.onmessage = handleMessage
    ws.onclose = () => { wsRef.current = null; setStatus(s => s === 'running' ? 'done' : s) }
    ws.onerror = () => {
      setStatus('error')
      setEvents(prev => [...prev, { type: 'error', message: 'WebSocket connection failed. Is the server running?' }])
      wsRef.current = null
    }
  }, [handleMessage])

  const startGame = useCallback(({ names = [], humanName = null, levelId = null, turnstileToken = null, models = {} } = {}) => {
    connect(WS_GAME_URL, { type: 'start', names, human_name: humanName, levelId, turnstile_token: turnstileToken, models })
  }, [connect])

  const startDemo = useCallback(({ demoId, humanName = null, fixtureChoice = null, turnstileToken = null } = {}) => {
    connect(WS_DEMO_URL, { type: 'start_demo', demo_id: demoId, human_name: humanName, fixture_choice: fixtureChoice, turnstile_token: turnstileToken })
  }, [connect])

  const startReplay = useCallback(({ replayFile }) => {
    connect(WS_REPLAY_URL, { type: 'start_replay', replay_file: replayFile })
  }, [connect])

  const submitInputForm = useCallback((values) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'input_form_response', values }))
      setInputRequest(null)
    }
  }, [])

  const skipAnimation = useCallback(() => {
    skipRef.current = true
  }, [])

  const exitGame = useCallback(() => {
    if (wsRef.current) {
      try { wsRef.current.close() } catch (e) {}
      wsRef.current = null
    }
    setStatus('idle')
    setEvents([])
    setScores(null)
    setEvicted([])
    setFeedMarkers([])
    setSegmentTitles([])
    setWidget(null)
    setPrivateConversations([])
    setPlayerNames([])
    setTypingMessage(null)
    setInputRequest(null)
    setAwaitingNext(false)

    awaitingNextRoundRef.current = false 
    setAwaitingNextRound(false)   

    setPhaseRounds([])
    setCurrentRoundIndex(0)
    pendingQueue.current = []
    isAnimating.current = false
    setIsAnimatingState(false)
    skipRef.current = false
    awaitingNextRef.current = false
  }, [])

  const restartGame = useCallback(() => {
    const last = lastConnectRef.current
    if (!last) return
    if (wsRef.current) {
      try { wsRef.current.onclose = null; wsRef.current.close() } catch (e) {}
      wsRef.current = null
    }
    connect(last.wsUrl, last.initMsg)
  }, [connect])

  const transcribe = useCallback((blob, hints = []) => {
    return new Promise((resolve) => {
      if (!wsRef.current) { resolve(''); return }
      const reader = new FileReader()
      reader.onload = () => {
        const dataUrl = reader.result
        const base64 = typeof dataUrl === 'string' ? dataUrl.split(',')[1] : ''
        const mimeType = blob.type || 'audio/webm'
        transcribePendingRef.current = resolve
        wsRef.current.send(JSON.stringify({ type: 'transcribe', audio: base64, mimeType, hints }))
      }
      reader.onerror = () => resolve('')
      reader.readAsDataURL(blob)
    })
  }, [])

  
  const sendNextRound = useCallback(() => {
    awaitingNextRoundRef.current = false
    setAwaitingNextRound(false)
    if (wsRef.current)
      wsRef.current.send(JSON.stringify({ type: 'next_round' }))
    drainQueue()
  }, [drainQueue])

  const sendNext = useCallback(() => {
    awaitingNextRef.current = false
    setAwaitingNext(false)
    releaseOneRef.current = true
    drainQueue()
  }, [drainQueue])

  return {
    status, events, scores, evicted,
    inputRequest, awaitingNext,  awaitingNextRound, phaseRounds, currentRoundIndex, feedMarkers, segmentTitles,
    widget, privateConversations, playerNames, typingMessage,
    startGame, startDemo, startReplay, submitInputForm, sendNext, sendNextRound, skipAnimation, exitGame, restartGame, transcribe,
    onAnimationComplete, skipRef, isAnimating: isAnimatingState,
  }
}
