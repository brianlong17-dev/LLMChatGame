import { useState, useRef, useCallback, useEffect } from 'react'

const WS_URL = `ws://${window.location.host}/ws/game`
const WS_DEMO_URL = `ws://${window.location.host}/ws/demo`

function isAnimatableEvent(evt, animateText) {
  if (evt.type !== 'public_action') return false
  if (!animateText) return false
  return evt.animate === true
}

export function useGameSocket(autoRun, animateText) {
  const [status, setStatus] = useState('idle')
  const [events, setEvents] = useState([])
  const [scores, setScores] = useState({})
  const [evicted, setEvicted] = useState([])
  const [inputRequest, setInputRequest] = useState(null)
  const [awaitingNext, setAwaitingNext] = useState(false)
  const [phaseRounds, setPhaseRounds] = useState([])
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0)
  const [feedMarkers, setFeedMarkers] = useState([])
  const [segmentTitles, setSegmentTitles] = useState([])
  const [widget, setWidget] = useState(null)
  const [privateConversations, setPrivateConversations] = useState([])
  const [playerNames, setPlayerNames] = useState([])

  const wsRef = useRef(null)
  const autoRunRef = useRef(autoRun)
  useEffect(() => { autoRunRef.current = autoRun }, [autoRun])

  const animateTextRef = useRef(animateText)
  useEffect(() => { animateTextRef.current = animateText }, [animateText])

  const [isAnimatingState, setIsAnimatingState] = useState(false)

  const pendingQueue = useRef([])
  const isAnimating = useRef(false)
  const skipRef = useRef(false)

  const drainQueue = useCallback(() => {
    while (pendingQueue.current.length > 0) {
      if (isAnimating.current) break
      const evt = pendingQueue.current.shift()
      if (evt.type === 'points_update') { setScores(evt.scores); continue }
      if (evt.type === 'evicted_update') { setEvicted(evt.evicted_names); continue }
      if (evt.type === 'widget_update') { setWidget(evt.widget ?? null); continue }
      if (evt.type === 'feed_marker') {
        setFeedMarkers(prev => [...prev, evt.label])
        setEvents(prev => [...prev, evt])
        continue
      }
      if (evt.type === 'awaiting_next') {                                       // ← new
        if (autoRunRef.current) {
          wsRef.current?.send(JSON.stringify({ type: 'next_turn' }))
        } else {
          setAwaitingNext(true)
        }
        continue
      }


      if (isAnimatableEvent(evt, animateTextRef.current)) {
        isAnimating.current = true
        setIsAnimatingState(true)
        setEvents(prev => [...prev, evt])
        break
      }
      setEvents(prev => [...prev, evt])
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

  // resume immediately if autoRun is turned on while paused
  useEffect(() => {
    if (autoRun && awaitingNext && wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'next_turn' }))
      setAwaitingNext(false)
    }
  }, [autoRun, awaitingNext])

  const handleMessage = useCallback((e) => {
    const evt = JSON.parse(e.data)
    //if (evt.type === 'points_update') { setScores(evt.scores); return }
    //if (evt.type === 'evicted_update') { setEvicted(evt.evicted_names); return }
    // We move these too the queue

    if (evt.type === 'private_conversation') {
      setPrivateConversations(prev => [...prev, { participants: evt.participants ?? [], messages: evt.messages }])
      return
    }
    if (evt.type === 'cast') { setPlayerNames(evt.names ?? []); return }
    if (evt.type === 'input_request') { setInputRequest(evt); return }
    if (evt.type === 'loading_done') {
      setEvents(prev => prev.filter(e => e.type !== 'loading'))
      return
    }
        
    if (evt.type === 'phase_rounds') { setPhaseRounds(evt.rounds); setCurrentRoundIndex(0); return }
    if (evt.type === 'phase_round_index') { setCurrentRoundIndex(evt.index); setFeedMarkers([]); setSegmentTitles([]); setWidget(null); return }
    if (evt.type === 'set_segments') { setSegmentTitles(evt.titles); return }
    if (evt.type === 'widget_update') { setWidget(evt.widget ?? null); return }

    if (evt.type === 'game_over') setStatus('done')
    if (evt.type === 'error') setStatus('error')
    pendingQueue.current.push(evt)
    drainQueue()
  }, [drainQueue])

  const connect = useCallback((wsUrl, initMsg) => {
    if (wsRef.current) return
    setStatus('connecting')
    setEvents([])
    setScores({})
    setEvicted([])
    setFeedMarkers([])
    setSegmentTitles([])
    setWidget(null)
    setPrivateConversations([])
    setPlayerNames([])
    pendingQueue.current = []
    isAnimating.current = false
    setIsAnimatingState(false)
    skipRef.current = false

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => { ws.send(JSON.stringify(initMsg)); setStatus('running') }
    ws.onmessage = handleMessage
    ws.onclose = () => { wsRef.current = null; setStatus(s => s === 'running' ? 'done' : s) }
    ws.onerror = () => {
      setStatus('error')
      setEvents(prev => [...prev, { type: 'error', message: 'WebSocket connection failed. Is the server running?' }])
      wsRef.current = null
    }
  }, [handleMessage])

  const startGame = useCallback(({ names = [], humanName = null } = {}) => {
    connect(WS_URL, { type: 'start', names, human_name: humanName })
  }, [connect])

  const startDemo = useCallback(({ demoId, humanName = null } = {}) => {
    connect(WS_DEMO_URL, { type: 'start_demo', demo_id: demoId, human_name: humanName })
  }, [connect])

  const submitInput = useCallback((value) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'input_response', value }))
      setInputRequest(null)
    }
  }, [])

  const skipAnimation = useCallback(() => {
    skipRef.current = true
  }, [])

  const sendNext = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'next_turn' }))
      setAwaitingNext(false)
    }
  }, [])

  return {
    status, events, scores, evicted,
    inputRequest, awaitingNext, phaseRounds, currentRoundIndex, feedMarkers, segmentTitles,
    widget, privateConversations, playerNames,
    startGame, startDemo, submitInput, sendNext, skipAnimation,
    onAnimationComplete, skipRef, isAnimating: isAnimatingState,
  }
}
