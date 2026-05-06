'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface AgentEvent {
    id: string
    type: 'thinking' | 'message' | 'error' | 'system'
    agent: string
    message: string
    data?: Record<string, unknown>
    timestamp: string
    level?: 'info' | 'warning' | 'error' | 'success'
}

interface UseWebSocketOptions {
    onEvent?: (event: AgentEvent) => void
    reconnectMs?: number
    maxEvents?: number
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

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080'

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        const url = `${wsUrl}/ws/chat`
        setStatus('connecting')

        try {
            const ws = new WebSocket(url)
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
                        timestamp: data.timestamp || new Date().toISOString(),
                        level: data.level || 'info',
                    }

                    setEvents(prev => [agentEvent, ...prev].slice(0, maxEvents))
                    onEvent?.(agentEvent)
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
    }, [wsUrl, reconnectMs, maxEvents, onEvent])

    const disconnect = useCallback(() => {
        clearTimeout(reconnectRef.current!)
        clearInterval(pingRef.current!)
        wsRef.current?.close()
        setStatus('disconnected')
    }, [])

    const sendMessage = useCallback((message: string, role: string = 'Research_Intelligence') => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ message, role }))
            return true
        }
        return false
    }, [])

    useEffect(() => {
        connect()
        return () => disconnect()
    }, [connect, disconnect])

    return { status, events, latency, connect, disconnect, sendMessage }
}
