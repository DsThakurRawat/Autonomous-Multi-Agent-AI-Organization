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
        <div className="card flex flex-col h-[480px] bg-[#09090b] border border-[#27272a] shadow-2xl relative overflow-hidden rounded-xl">
            {/* Header (Terminal Window Style) */}
            <div className="flex items-center justify-between mb-0 flex-shrink-0 bg-[#18181b] border-b border-[#27272a] px-3 py-2 rounded-t-xl z-10">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-500/80 border border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 border border-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 border border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    </div>
                    <div className="flex items-center gap-2 border-l border-[#27272a] pl-4">
                        <Radio size={12} className="text-blue-400" />
                        <h2 className="text-xs font-mono text-zinc-400">bash — agent-feed</h2>
                    </div>
                    <span className="ml-3 text-[10px] text-zinc-600 font-mono bg-black/50 px-2 py-0.5 rounded-full border border-[#27272a]">
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
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1 font-mono text-[11px] leading-relaxed custom-scrollbar">
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
                                className="flex items-start gap-4 hover:bg-[#18181b] px-2 py-1 -mx-2 rounded transition-colors"
                            >
                                {/* Timestamp */}
                                <span className="text-[10px] text-text-muted w-16 flex-shrink-0 pt-0.5">
                                    {new Date(event.timestamp).toLocaleTimeString('en', { hour12: false })}
                                </span>

                                {/* Agent text box */}
                                <div className="flex items-start gap-2 w-full">
                                    <span className="text-zinc-500 font-bold whitespace-nowrap pt-0.5">
                                        {`[${event.agent.replace('Engineer_', 'Eng_').toUpperCase()}]`}
                                    </span>

                                    {/* Type icon */}
                                    <span className={clsx('w-4 flex-shrink-0 text-center pt-0.5', cls)}>
                                        {icon}
                                    </span>

                                    {/* Message content */}
                                    <span className={clsx("flex-1 whitespace-pre-wrap break-words", cls)}>
                                        {event.message}
                                    </span>
                                </div>

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
