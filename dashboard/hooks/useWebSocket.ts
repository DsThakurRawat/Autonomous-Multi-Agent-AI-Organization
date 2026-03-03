'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface AgentEvent {
    id: string
    type: 'thinking' | 'task_start' | 'task_complete' | 'task_failed' | 'phase_change' | 'cost_update' | 'system'
    agent: string
    message: string
    data?: Record<string, unknown>
    timestamp: string
    project_id: string
    trace_id?: string
    level?: 'info' | 'warning' | 'error' | 'success'
}

interface UseWebSocketOptions {
    projectId?: string
    onEvent?: (event: AgentEvent) => void
    reconnectMs?: number
    maxEvents?: number
}

export function useWebSocket({
    projectId,
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

        const url = projectId
            ? `${wsUrl}/ws/projects/${projectId}/events`
            : `${wsUrl}/ws/events`

        setStatus('connecting')

        try {
            const ws = new WebSocket(url)
            wsRef.current = ws

            ws.onopen = () => {
                setStatus('connected')
                // Start ping interval for latency measurement
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

                    // Handle ping/pong
                    if (data.type === 'pong') {
                        setLatency(Date.now() - pingStartRef.current)
                        return
                    }

                    const agentEvent: AgentEvent = {
                        id: data.id || `evt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                        type: data.type || 'system',
                        agent: data.agent || data.agent_role || 'system',
                        message: data.message || data.content || '',
                        data: data.data || data.payload,
                        timestamp: data.timestamp || new Date().toISOString(),
                        project_id: data.project_id || projectId || '',
                        trace_id: data.trace_id,
                        level: data.level || 'info',
                    }

                    setEvents(prev => {
                        const next = [agentEvent, ...prev]
                        return next.slice(0, maxEvents)
                    })

                    onEvent?.(agentEvent)
                } catch (e) {
                    console.warn('WS parse error:', e)
                }
            }

            ws.onclose = () => {
                setStatus('disconnected')
                clearInterval(pingRef.current!)
                // Auto-reconnect
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
    }, [wsUrl, projectId, reconnectMs, maxEvents, onEvent])

    const disconnect = useCallback(() => {
        clearTimeout(reconnectRef.current!)
        clearInterval(pingRef.current!)
        wsRef.current?.close()
        setStatus('disconnected')
    }, [])

    const clearEvents = useCallback(() => setEvents([]), [])

    // Inject a mock event — useful when API is offline (dev mode)
    const injectMockEvent = useCallback((msg: Partial<AgentEvent>) => {
        const event: AgentEvent = {
            id: `mock-${Date.now()}`,
            type: msg.type || 'thinking',
            agent: msg.agent || 'CEO',
            message: msg.message || 'Analyzing business requirements...',
            timestamp: new Date().toISOString(),
            project_id: msg.project_id || 'demo',
            level: msg.level || 'info',
            ...msg,
        }
        setEvents(prev => [event, ...prev].slice(0, maxEvents))
    }, [maxEvents])

    useEffect(() => {
        connect()
        return () => disconnect()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId])

    return { status, events, latency, connect, disconnect, clearEvents, injectMockEvent }
}
