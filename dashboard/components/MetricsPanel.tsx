'use client'

import { SystemMetrics, AgentStatus, AGENT_COLORS, AGENT_EMOJI, formatDuration } from '@/lib/api'
import { Activity, Zap, Clock, CheckCircle2, XCircle, Cpu } from 'lucide-react'
import { clsx } from 'clsx'

interface MetricsPanelProps {
    metrics?: SystemMetrics | null
    agents?: AgentStatus[]
    isLoading?: boolean
}

function MetricTile({
    label, value, icon, color = '#4f8ef7', delta
}: {
    label: string; value: string; icon: React.ReactNode; color?: string; delta?: string
}) {
    return (
        <div className="metric-card">
            <div className="flex items-center justify-between">
                <span className="metric-label">{label}</span>
                <span style={{ color }}>{icon}</span>
            </div>
            <span className="metric-value">{value}</span>
            {delta && (
                <span className={clsx('metric-delta', delta.startsWith('+') ? 'text-emerald-400' : 'text-red-400')}>
                    {delta}
                </span>
            )}
        </div>
    )
}

export default function MetricsPanel({ metrics, agents = [], isLoading }: MetricsPanelProps) {
    const uptimeStr = metrics
        ? formatDuration(metrics.uptime_seconds * 1000)
        : '—'

    return (
        <div className="flex flex-col gap-4">
            {/* System Metrics grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MetricTile
                    label="Active Projects"
                    value={isLoading ? '…' : String(metrics?.active_projects ?? 0)}
                    icon={<Activity size={14} />}
                    color="#4f8ef7"
                />
                <MetricTile
                    label="Total Tasks Run"
                    value={isLoading ? '…' : String(metrics?.total_tasks_run ?? 0)}
                    icon={<Zap size={14} />}
                    color="#22d3ee"
                />
                <MetricTile
                    label="System Uptime"
                    value={isLoading ? '…' : uptimeStr}
                    icon={<Clock size={14} />}
                    color="#8b5cf6"
                />
                <MetricTile
                    label="Total Projects"
                    value={isLoading ? '…' : String(metrics?.total_projects ?? 0)}
                    icon={<Cpu size={14} />}
                    color="#10b981"
                />
            </div>

            {/* Agent Status Grid */}
            <div className="card">
                <div className="flex items-center gap-2 mb-3">
                    <Activity size={13} className="text-blue-400" />
                    <h3 className="text-sm font-semibold">Agent Status</h3>
                    <span className="text-xs text-text-muted ml-auto">
                        {agents.filter(a => a.status === 'processing').length} active
                    </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
                    {agents.length === 0
                        ? /* Skeleton placeholders */
                        ['CEO', 'CTO', 'Engineer_Backend', 'Engineer_Frontend', 'QA', 'DevOps', 'Finance'].map(role => (
                            <AgentCard key={role} agent={{ role, status: 'idle', tasks_done: 0, success_rate: 1, avg_latency_ms: 0 }} />
                        ))
                        : agents.map(agent => <AgentCard key={agent.role} agent={agent} />)
                    }
                </div>
            </div>
        </div>
    )
}

function AgentCard({ agent }: { agent: AgentStatus }) {
    const color = AGENT_COLORS[agent.role] || '#94a3b8'
    const emoji = AGENT_EMOJI[agent.role] || '🤖'

    const statusColor = {
        idle: '#4b5563',
        processing: '#4f8ef7',
        error: '#ef4444',
    }[agent.status]

    return (
        <div
            className="flex items-center gap-3 p-3 rounded-lg border transition-all duration-200"
            style={{
                background: `${color}08`,
                borderColor: agent.status === 'processing' ? `${color}60` : '#252535',
                boxShadow: agent.status === 'processing' ? `0 0 10px ${color}20` : 'none',
            }}
        >
            {/* Avatar */}
            <div
                className="w-9 h-9 rounded-lg flex items-center justify-center text-base flex-shrink-0"
                style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}
            >
                {emoji}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-medium text-text-primary truncate" style={{ color }}>
                        {agent.role.replace('Engineer_', 'Eng·')}
                    </span>
                    <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{
                            backgroundColor: statusColor,
                            boxShadow: agent.status === 'processing' ? `0 0 6px ${statusColor}` : 'none',
                            animation: agent.status === 'processing' ? 'pulse 1.5s infinite' : 'none',
                        }}
                    />
                </div>

                {/* Current task */}
                {agent.current_task ? (
                    <p className="text-[10px] text-text-muted truncate mt-0.5">{agent.current_task}</p>
                ) : (
                    <p className="text-[10px] text-text-muted mt-0.5 capitalize">{agent.status}</p>
                )}

                {/* Stats row */}
                <div className="flex items-center gap-2 mt-1.5">
                    <span className="flex items-center gap-0.5 text-[10px] text-emerald-400">
                        <CheckCircle2 size={9} />
                        {agent.tasks_done}
                    </span>
                    <span className="flex items-center gap-0.5 text-[10px] text-emerald-400">
                        {(agent.success_rate * 100).toFixed(0)}%
                    </span>
                    <span className="text-[10px] text-text-muted ml-auto">
                        {agent.avg_latency_ms.toFixed(0)}ms
                    </span>
                </div>
            </div>
        </div>
    )
}
