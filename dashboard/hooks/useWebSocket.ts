'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface AgentEvent {
    id: string
    type: string
    agent: string
    message: string
    session_id?: string
    data?: Record<string, unknown>
    timestamp: string
    level?: 'info' | 'warning' | 'error' | 'success' | string
}

interface UseWebSocketOptions {
    onEvent?: (event: AgentEvent) => void
    reconnectMs?: number
    maxEvents?: number
    projectId?: string
}

export function useWebSocket({
    onEvent,
    reconnectMs = 3000,
    maxEvents = 200,
}: UseWebSocketOptions = {}) {
    const [status, setStatus] = useState<WsStatus>('disconnected')
    const [events, setEvents] = useState<AgentEvent[]>([])
    const [latency, setLatency] = useState<number | null>(null)

    const wsRef = useRef<WebSocket | null>(null)
    const reconnectRef = useRef<NodeJS.Timeout | null>(null)
    const pingRef = useRef<NodeJS.Timeout | null>(null)
    const pingStartRef = useRef<number>(0)
    const onEventRef = useRef(onEvent)

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/chat'

    // Keep ref always up-to-date so ws.onmessage never has a stale closure
    useEffect(() => { onEventRef.current = onEvent }, [onEvent])

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        setStatus('connecting')

        try {
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                setStatus('connected')
                pingRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        pingStartRef.current = Date.now()
                        ws.send(JSON.stringify({ type: 'ping' }))
                    }
                }, 5000)
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    if (data.type === 'pong') {
                        setLatency(Date.now() - pingStartRef.current)
                        return
                    }

                    const agentEvent: AgentEvent = {
                        id: `evt-${Date.now()}`,
                        type: data.type || 'message',
                        agent: data.agent || 'system',
                        message: data.message || '',
                        session_id: data.session_id,
                        timestamp: data.timestamp || new Date().toISOString(),
                        level: data.level || 'info',
                    }

                    setEvents(prev => [agentEvent, ...prev].slice(0, maxEvents))
                    onEventRef.current?.(agentEvent)
                } catch (e) {}
            }

            ws.onclose = () => {
                setStatus('disconnected')
                clearInterval(pingRef.current!)
                reconnectRef.current = setTimeout(connect, reconnectMs)
            }

            ws.onerror = () => {
                setStatus('error')
                ws.close()
            }
        } catch (e) {
            setStatus('error')
            reconnectRef.current = setTimeout(connect, reconnectMs)
        }
    }, [wsUrl, reconnectMs, maxEvents])

    const disconnect = useCallback(() => {
        clearTimeout(reconnectRef.current!)
        clearInterval(pingRef.current!)
        wsRef.current?.close()
        setStatus('disconnected')
    }, [])

    const sendMessage = useCallback((message: string, role: string = 'Research_Intelligence', sessionId?: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ 
                message, 
                role,
                session_id: sessionId 
            }))
            return true
        }
        return false
    }, [])

    const clearEvents = useCallback(() => {
        setEvents([])
    }, [])

    const injectMockEvent = useCallback((event: Omit<AgentEvent, 'id' | 'timestamp'>) => {
        const fullEvent: AgentEvent = {
            id: `mock-${Date.now()}`,
            timestamp: new Date().toISOString(),
            ...event
        }
        setEvents(prev => [fullEvent, ...prev].slice(0, maxEvents))
        onEventRef.current?.(fullEvent)
    }, [maxEvents])

    useEffect(() => {
        connect()
        return () => disconnect()
    }, [connect, disconnect])

    return { status, events, latency, connect, disconnect, sendMessage, clearEvents, injectMockEvent }
}
