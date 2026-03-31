'use client'

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { formatCost } from '@/lib/api'
import { DollarSign, TrendingUp, AlertTriangle } from 'lucide-react'
import { clsx } from 'clsx'

interface CostEntry {
    time: string
    spent: number
    budget: number
}

interface CostMeterProps {
    budgetUsd: number
    spentUsd: number
    history?: CostEntry[]
    projectId?: string
}

export default function CostMeter({ budgetUsd, spentUsd, history = [], projectId }: CostMeterProps) {
    const pct = budgetUsd > 0 ? Math.min((spentUsd / budgetUsd) * 100, 100) : 0
    const remaining = Math.max(budgetUsd - spentUsd, 0)
    const isWarning = pct > 70
    const isDanger = pct > 90

    const barColor = isDanger ? '#ef4444' : isWarning ? '#f59e0b' : '#10b981'

    // Build chart data — use history or synthetic
    const chartData: CostEntry[] = history.length > 0
        ? history
        : Array.from({ length: 12 }, (_, i) => ({
            time: `${i * 5}m`,
            spent: spentUsd * (i / 11),
            budget: budgetUsd,
        }))

    return (
        <div className="card flex flex-col gap-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <DollarSign size={14} className="text-amber-400" />
                    <h2 className="text-sm font-semibold">Cost Tracker</h2>
                </div>
                {isWarning && (
                    <span className={clsx(
                        'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
                        isDanger
                            ? 'text-red-400 bg-red-500/10 border border-red-500/20'
                            : 'text-amber-400 bg-amber-500/10 border border-amber-500/20'
                    )}>
                        <AlertTriangle size={10} />
                        {isDanger ? 'Budget Critical' : 'Budget Warning'}
                    </span>
                )}
            </div>

            {/* Main figures */}
            <div className="flex items-end justify-between">
                <div>
                    <div className="text-3xl font-bold font-mono" style={{ color: barColor }}>
                        {formatCost(spentUsd)}
                    </div>
                    <div className="text-xs text-text-muted mt-0.5">
                        of {formatCost(budgetUsd)} budget
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-lg font-semibold text-text-primary font-mono">
                        {formatCost(remaining)}
                    </div>
                    <div className="text-xs text-text-muted">remaining</div>
                </div>
            </div>

            {/* Progress bar */}
            <div>
                <div className="flex justify-between text-xs text-text-muted mb-1.5">
                    <span>{pct.toFixed(1)}% used</span>
                    <span className="flex items-center gap-1">
                        <TrendingUp size={10} />
                        {(spentUsd / Math.max(spentUsd, 0.001) * 100).toFixed(0)}% efficiency
                    </span>
                </div>
                <div className="h-2 bg-[#1c1c28] rounded-full overflow-hidden">
                    <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                            width: `${pct}%`,
                            background: `linear-gradient(90deg, ${barColor}80, ${barColor})`,
                            boxShadow: `0 0 8px ${barColor}60`,
                        }}
                    />
                </div>
            </div>

            {/* Mini cost breakdown */}
            <div className="grid grid-cols-3 gap-2">
                {[
                    { label: 'LLM', value: spentUsd * 0.75, color: '#4f8ef7' },
                    { label: 'AWS', value: spentUsd * 0.20, color: '#8b5cf6' },
                    { label: 'Tools', value: spentUsd * 0.05, color: '#22d3ee' },
                ].map(item => (
                    <div key={item.label} className="bg-[#1c1c28] rounded-lg p-2 text-center">
                        <div className="text-xs font-mono font-medium" style={{ color: item.color }}>
                            {formatCost(item.value)}
                        </div>
                        <div className="text-[10px] text-text-muted mt-0.5">{item.label}</div>
                    </div>
                ))}
            </div>

            {/* Area chart */}
            {chartData.length > 1 && (
                <div className="h-[80px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                            <defs>
                                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={barColor} stopOpacity={0.3} />
                                    <stop offset="95%" stopColor={barColor} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#252535" vertical={false} />
                            <XAxis dataKey="time" hide />
                            <YAxis hide domain={[0, budgetUsd || 100]} />
                            <Tooltip
                                contentStyle={{ background: '#16161f', border: '1px solid #252535', borderRadius: 8, fontSize: 11 }}
                                labelStyle={{ color: '#94a3b8' }}
                                formatter={(v: any) => [formatCost(v), 'Spent']}
                            />
                            <Area
                                type="monotone"
                                dataKey="spent"
                                stroke={barColor}
                                strokeWidth={2}
                                fill="url(#costGrad)"
                                dot={false}
                                animationDuration={800}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    )
}
