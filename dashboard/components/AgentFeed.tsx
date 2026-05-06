'use client'

import { useRef, useEffect, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { AgentEvent, WsStatus } from '@/hooks/useWebSocket'
import { AGENT_COLORS, AGENT_EMOJI } from '@/lib/api'
import { Wifi, WifiOff, Loader2, Trash2, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'

interface AgentFeedProps {
    events: AgentEvent[]
    status: WsStatus
    latency?: number | null
    onClear?: () => void
    maxVisible?: number
}

const TYPE_STYLES: Record<string, string> = {
    thinking: 'text-zinc-400',
    task_start: 'text-emerald-400',
    task_complete: 'text-cyan-400',
    task_failed: 'text-red-400',
    phase_change: 'text-purple-400',
    cost_update: 'text-amber-400',
    system: 'text-zinc-500',
}

const TYPE_ICON: Record<string, string> = {
    thinking: '💭',
    task_start: '▶️',
    task_complete: '✅',
    task_failed: '❌',
    phase_change: '🔄',
    cost_update: '💵',
    system: '⚙️',
}

function StatusIndicator({ status, latency }: { status: WsStatus; latency?: number | null }) {
    return (
        <div className="flex items-center gap-2 text-xs font-mono">
            {status === 'connected' && (
                <>
                    <span className="flex items-center gap-1.5 text-emerald-500">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        Live
                    </span>
                    {latency != null && (
                        <span className="text-zinc-600">{latency}ms</span>
                    )}
                </>
            )}
            {status === 'connecting' && (
                <span className="flex items-center gap-1.5 text-amber-500">
                    <Loader2 size={12} className="animate-spin" />
                    Connecting...
                </span>
            )}
            {(status === 'disconnected' || status === 'error') && (
                <span className="flex items-center gap-1.5 text-red-500">
                    <WifiOff size={12} />
                    Offline
                </span>
            )}
        </div>
    )
}

export default function AgentFeed({ events, status, latency, onClear, maxVisible = 100 }: AgentFeedProps) {
    const bottomRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom inside the feed
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [events.length])

    const groupedThreads = useMemo(() => {
        // events is reverse-chronological (newest first). Let's make it chronological.
        const chronEvents = [...events].slice(0, maxVisible).reverse();
        
        type ThreadedEvent = AgentEvent & { subEvents: AgentEvent[] };
        const threads: ThreadedEvent[] = [];
        const activeTaskByAgent: Record<string, ThreadedEvent> = {};
        
        for (const event of chronEvents) {
            if (event.type === 'task_start' || event.type === 'phase_change') {
                const thread = { ...event, subEvents: [] };
                threads.push(thread);
                activeTaskByAgent[event.agent] = thread;
            } else if (event.type === 'task_complete' || event.type === 'task_failed') {
                // Top level, but clears the active task so future loose thoughts don't incorrectly attach
                threads.push({ ...event, subEvents: [] });
                delete activeTaskByAgent[event.agent];
            } else {
                if (activeTaskByAgent[event.agent] && event.type !== 'system') {
                    activeTaskByAgent[event.agent].subEvents.push(event);
                } else {
                    threads.push({ ...event, subEvents: [] });
                }
            }
        }
        return threads;
    }, [events, maxVisible]);

    return (
        <div className="flex flex-col h-[600px] bg-[#09090b] border border-white/5 shadow-2xl relative overflow-hidden rounded-2xl">
            {/* Header */}
            <div className="flex items-center justify-between flex-shrink-0 bg-[#09090b]/80 backdrop-blur-md border-b border-white/5 px-4 py-3 z-10 w-full absolute top-0">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
                        <Sparkles size={16} />
                    </div>
                    <div>
                        <h2 className="text-sm font-semibold text-white tracking-tight">Agent Terminal</h2>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                                {events.length} Events Processed
                            </span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <StatusIndicator status={status} latency={latency} />
                    {onClear && events.length > 0 && (
                        <button onClick={onClear} className="w-8 h-8 rounded-full flex items-center justify-center bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-all border border-white/5" title="Clear feed">
                            <Trash2 size={14} />
                        </button>
                    )}
                </div>
            </div>

            {/* Feed Content */}
            <div className="flex-1 overflow-y-auto px-6 pt-20 pb-6 space-y-4 font-sans text-sm custom-scrollbar bg-gradient-to-b from-[#09090b] to-[#121214]">
                {groupedThreads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4 text-zinc-500 animate-fade-in">
                        <div className="w-16 h-16 rounded-full bg-emerald-500/5 flex items-center justify-center text-3xl border border-white/5">
                            <Sparkles className="text-emerald-500" size={24} />
                        </div>
                        <p className="text-zinc-400">Awaiting Agent Activity...</p>
                    </div>
                ) : (
                    groupedThreads.map((thread) => {
                        const emoji = AGENT_EMOJI[thread.agent] || ''
                        const icon = TYPE_ICON[thread.type] || '·'
                        const cls = TYPE_STYLES[thread.type] || 'text-zinc-500'

                        // If it's a project complete link, make it clickable
                        const isLink = thread.message.includes('http://');
                        const msgHtml = isLink ? (
                            <span dangerouslySetInnerHTML={{__html: thread.message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-emerald-400 underline hover:text-emerald-300 transition-colors">$1</a>')}} />
                        ) : thread.message;

                        return (
                            <div
                                key={thread.id}
                                className="group flex flex-col gap-1 w-full animate-slide-up bg-white/[0.02] border border-white/5 rounded-xl p-3"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 px-2 py-0.5 rounded text-[10px] font-mono text-zinc-300">
                                            <span>{emoji}</span>
                                            <span className="font-semibold">{thread.agent.replace(/_/g, ' ')}</span>
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-zinc-500 font-mono">
                                        {new Date(thread.timestamp).toLocaleTimeString('en', { hour12: false })}
                                    </span>
                                </div>
                                
                                <div className="flex items-start gap-3 mt-2">
                                    <div className={clsx("flex-1 text-[14px] leading-relaxed font-medium flex gap-2 items-start", cls)}>
                                        <span className="mt-0.5 opacity-80">{icon}</span> 
                                        <span>{msgHtml}</span>
                                    </div>
                                </div>

                                {thread.subEvents.length > 0 && (
                                    <div className="flex flex-col gap-3 mt-3 pl-4 border-l-2 border-white/10 ml-2 py-1">
                                        {thread.subEvents.map(sub => (
                                            <div key={sub.id} className={clsx("text-[13px] leading-relaxed font-mono tracking-tight", TYPE_STYLES[sub.type] || 'text-zinc-400')}>
                                                {sub.message.split('\\n').map((line, i) => (
                                                    <div key={i} className="mb-1 opacity-80 hover:opacity-100 transition-opacity">{line}</div>
                                                ))}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )
                    })
                )}
                <div ref={bottomRef} className="h-4" />
            </div>
        </div>
    )
}
