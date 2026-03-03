'use client'

import { useRef, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { AgentEvent, WsStatus } from '@/hooks/useWebSocket'
import { AGENT_COLORS, AGENT_EMOJI } from '@/lib/api'
import { Wifi, WifiOff, Loader2, Trash2, Radio } from 'lucide-react'
import { clsx } from 'clsx'

interface AgentFeedProps {
    events: AgentEvent[]
    status: WsStatus
    latency?: number | null
    onClear?: () => void
    maxVisible?: number
}

const TYPE_STYLES: Record<string, string> = {
    thinking: 'text-blue-400',
    task_start: 'text-cyan-400',
    task_complete: 'text-emerald-400',
    task_failed: 'text-red-400',
    phase_change: 'text-purple-400',
    cost_update: 'text-amber-400',
    system: 'text-slate-400',
}

const TYPE_ICON: Record<string, string> = {
    thinking: '🧠',
    task_start: '▶',
    task_complete: '✓',
    task_failed: '✗',
    phase_change: '↗',
    cost_update: '$',
    system: '·',
}

function StatusIndicator({ status, latency }: { status: WsStatus; latency?: number | null }) {
    return (
        <div className="flex items-center gap-2 text-xs">
            {status === 'connected' && (
                <>
                    <span className="flex items-center gap-1 text-emerald-400">
                        <Wifi size={12} />
                        Live
                    </span>
                    {latency != null && (
                        <span className="text-text-muted">{latency}ms</span>
                    )}
                </>
            )}
            {status === 'connecting' && (
                <span className="flex items-center gap-1 text-amber-400">
                    <Loader2 size={12} className="animate-spin" />
                    Connecting...
                </span>
            )}
            {(status === 'disconnected' || status === 'error') && (
                <span className="flex items-center gap-1 text-red-400">
                    <WifiOff size={12} />
                    Offline
                </span>
            )}
        </div>
    )
}

export default function AgentFeed({ events, status, latency, onClear, maxVisible = 100 }: AgentFeedProps) {
    const bottomRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom when new events arrive
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [events.length])

    const visible = events.slice(0, maxVisible)

    return (
        <div className="card flex flex-col h-[480px]">
            {/* Header */}
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <Radio size={14} className="text-blue-400" />
                    <h2 className="text-sm font-semibold text-text-primary">Agent Feed</h2>
                    <span className="text-xs text-text-muted bg-[#1c1c28] px-2 py-0.5 rounded-full">
                        {events.length} events
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <StatusIndicator status={status} latency={latency} />
                    {onClear && events.length > 0 && (
                        <button onClick={onClear} className="btn-ghost p-1" title="Clear feed">
                            <Trash2 size={13} />
                        </button>
                    )}
                </div>
            </div>

            {/* Feed */}
            <div className="flex-1 overflow-y-auto space-y-0 font-mono text-xs">
                {visible.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted">
                        <div className="w-12 h-12 rounded-full bg-[#1c1c28] flex items-center justify-center text-2xl">
                            🤖
                        </div>
                        <p>Waiting for agent activity...</p>
                        <p className="text-xs opacity-60">Start a new project to see agents think</p>
                    </div>
                ) : (
                    visible.map((event) => {
                        const color = AGENT_COLORS[event.agent] || '#94a3b8'
                        const emoji = AGENT_EMOJI[event.agent] || '🤖'
                        const icon = TYPE_ICON[event.type] || '·'
                        const cls = TYPE_STYLES[event.type] || 'text-slate-400'

                        return (
                            <div
                                key={event.id}
                                className="log-line group hover:bg-[#1a1a25] px-1 rounded"
                            >
                                {/* Timestamp */}
                                <span className="text-[10px] text-text-muted w-16 flex-shrink-0 pt-0.5">
                                    {new Date(event.timestamp).toLocaleTimeString('en', { hour12: false })}
                                </span>

                                {/* Agent avatar */}
                                <span
                                    className="w-5 h-5 rounded flex-shrink-0 flex items-center justify-center text-[11px]"
                                    style={{ backgroundColor: `${color}25`, border: `1px solid ${color}40` }}
                                    title={event.agent}
                                >
                                    {emoji}
                                </span>

                                {/* Agent name */}
                                <span className="w-20 flex-shrink-0 truncate" style={{ color }}>
                                    {event.agent.replace('Engineer_', 'Eng_')}
                                </span>

                                {/* Type icon */}
                                <span className={clsx('w-4 flex-shrink-0 text-center', cls)}>
                                    {icon}
                                </span>

                                {/* Message */}
                                <span className="text-text-secondary flex-1 truncate group-hover:text-text-primary transition-colors">
                                    {event.message}
                                </span>

                                {/* Trace ID (hover only) */}
                                {event.trace_id && (
                                    <span className="text-[10px] text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                        {event.trace_id.slice(0, 8)}
                                    </span>
                                )}
                            </div>
                        )
                    })
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    )
}
