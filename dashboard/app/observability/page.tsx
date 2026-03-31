'use client'

import { useState, useEffect } from 'react'
import { 
    Activity, Shield, Zap, Database, 
    Network, AlertTriangle, CheckCircle2, 
    ArrowLeft, ExternalLink, BarChart3,
    Clock, Cpu, Globe, Infinity as InfinityIcon, Braces
} from 'lucide-react'
import Link from 'next/link'
import { clsx } from 'clsx'

// -- Mock Data for Observability --
const SERVICES = [
    { name: 'API Gateway (Go)', status: 'healthy', latency: '12ms', version: 'v2.4.0', type: 'entry' },
    { name: 'Agent Orchestrator (Go)', status: 'healthy', latency: '45ms', version: 'v1.12.2', type: 'core' },
    { name: 'Python Agent Worker', status: 'healthy', latency: '850ms', version: 'v3.1.0', type: 'compute' },
    { name: 'Rust Security Engine', status: 'healthy', latency: '<1ms', version: 'v0.8.5', type: 'security' },
    { name: 'Mixture-of-Experts (Rust)', status: 'healthy', latency: '15ms', version: 'v4.2.1', type: 'routing' },
]

const INFRA = [
    { name: 'Redis (Global Cache)', status: 'healthy', load: '12%', role: 'primary' },
    { name: 'Kafka (Event Bus)', status: 'healthy', throughput: '1.2k msg/s', role: 'backbone' },
    { name: 'Postgres (Primary DB)', status: 'healthy', connections: '42', role: 'storage' },
]

const RECENT_TRACES = [
    { id: 'tr_8f2a1b', service: 'gateway', path: '/v1/projects', duration: '1.2s', status: 200, time: '2m ago' },
    { id: 'tr_4d9e0c', service: 'agent', path: 'call_llm', duration: '2.5s', status: 200, time: '5m ago' },
    { id: 'tr_2a7f5a', service: 'security', path: 'scrub_text', duration: '0.1ms', status: 200, time: '12m ago' },
    { id: 'tr_9d1c3b', service: 'gateway', path: '/v1/auth/refresh', duration: '140ms', status: 401, time: '15m ago' },
]

export default function ObservabilityPage() {
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) return null

    return (
        <div className="min-h-screen bg-[#09090b] text-white selection:bg-emerald-500/30 font-sans">
            {/* Header */}
            <header className="bg-[#09090b]/80 backdrop-blur-md border-b border-white/5 px-6 py-4 flex items-center justify-between sticky top-0 z-40">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard" className="p-2 hover:bg-white/5 rounded-lg transition-colors text-zinc-400 hover:text-white">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
                            <Activity size={18} className="text-emerald-500" /> System Health
                        </h1>
                        <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest">Observability & Tracing Hub</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-[11px] px-3 py-1 rounded-full font-mono uppercase tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        OTel Collector: Active
                    </div>
                    <button className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 text-white text-sm font-medium transition-colors">
                        <BarChart3 size={16} />
                        Export Metrics
                    </button>
                </div>
            </header>

            <main className="max-w-7xl mx-auto p-6 space-y-8 animate-fade-in">
                
                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                        { label: 'Avg Latency', value: '42ms', change: '-4%', icon: <Clock className="text-blue-400" /> },
                        { label: 'CPU Usage', value: '28%', change: '+2%', icon: <Cpu className="text-purple-400" /> },
                        { label: 'Success Rate', value: '99.9%', change: '+0.1%', icon: <CheckCircle2 className="text-emerald-400" /> },
                        { label: 'Active Spans', value: '1,452', change: '+124', icon: <Network className="text-amber-400" /> },
                    ].map((stat, i) => (
                        <div key={i} className="bg-[#121214] border border-white/5 rounded-2xl p-5 hover:border-white/10 transition-all">
                            <div className="flex items-center justify-between mb-3">
                                <div className="p-2 bg-white/5 rounded-lg">{stat.icon}</div>
                                <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded-md", 
                                    stat.change.startsWith('+') ? 'text-emerald-400 bg-emerald-400/10' : 'text-blue-400 bg-blue-400/10'
                                )}>
                                    {stat.change}
                                </span>
                            </div>
                            <p className="text-xs text-zinc-500 font-medium">{stat.label}</p>
                            <h3 className="text-2xl font-bold text-white mt-1">{stat.value}</h3>
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    
                    {/* Services Column */}
                    <div className="lg:col-span-2 space-y-6">
                        <section>
                            <h2 className="text-sm font-semibold text-zinc-400 mb-4 flex items-center gap-2 uppercase tracking-widest">
                                <Zap size={14} className="text-emerald-400" /> Distributed Services
                            </h2>
                            <div className="bg-[#121214] border border-white/5 rounded-2xl overflow-hidden">
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-white/5 text-zinc-500 text-[11px] uppercase tracking-wider font-semibold">
                                            <th className="px-6 py-4">Service</th>
                                            <th className="px-6 py-4">Status</th>
                                            <th className="px-6 py-4">Latency</th>
                                            <th className="px-6 py-4">Version</th>
                                            <th className="px-6 py-4"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {SERVICES.map((svc, i) => (
                                            <tr key={i} className="group hover:bg-white/[0.02] transition-colors">
                                                <td className="px-6 py-4 flex items-center gap-3">
                                                    <div className={clsx("w-2 h-2 rounded-full",
                                                        svc.type === 'entry' ? 'bg-blue-400' :
                                                        svc.type === 'security' ? 'bg-red-400' :
                                                        svc.type === 'compute' ? 'bg-purple-400' : 'bg-emerald-400'
                                                    )} />
                                                    <span className="font-medium">{svc.name}</span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="text-emerald-400 bg-emerald-400/10 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Healthy</span>
                                                </td>
                                                <td className="px-6 py-4 font-mono text-zinc-400">{svc.latency}</td>
                                                <td className="px-6 py-4 font-mono text-xs text-zinc-500">{svc.version}</td>
                                                <td className="px-6 py-4 text-right">
                                                    <button className="text-zinc-600 hover:text-white transition-colors">
                                                        <ExternalLink size={14} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section>
                            <h2 className="text-sm font-semibold text-zinc-400 mb-4 flex items-center gap-2 uppercase tracking-widest">
                                <Network size={14} className="text-blue-400" /> Recent Distributed Traces
                            </h2>
                            <div className="grid grid-cols-1 gap-3">
                                {RECENT_TRACES.map((trace, i) => (
                                    <div key={i} className="bg-[#121214] border border-white/5 rounded-xl p-4 flex items-center justify-between hover:border-emerald-500/20 transition-all cursor-pointer group">
                                        <div className="flex items-center gap-4">
                                            <div className={clsx("p-2 rounded-lg", 
                                                trace.status === 200 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                                            )}>
                                                <Braces size={16} />
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-semibold font-mono">{trace.id}</span>
                                                    <span className="text-[10px] text-zinc-500 uppercase font-bold px-1.5 py-0.5 bg-white/5 rounded">{trace.service}</span>
                                                </div>
                                                <p className="text-xs text-zinc-400 mt-0.5">{trace.path}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="flex items-center gap-2 justify-end mb-1">
                                                <span className="text-xs font-mono font-medium text-white">{trace.duration}</span>
                                                <CheckCircle2 size={12} className={trace.status === 200 ? 'text-emerald-500' : 'text-red-500'} />
                                            </div>
                                            <span className="text-[10px] text-zinc-500">{trace.time}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    {/* Sidebar Column */}
                    <div className="space-y-6">
                        <section>
                            <h2 className="text-sm font-semibold text-zinc-400 mb-4 flex items-center gap-2 uppercase tracking-widest">
                                <Database size={14} className="text-purple-400" /> Infrastructure
                            </h2>
                            <div className="bg-[#121214] border border-white/5 rounded-2xl p-4 space-y-4">
                                {INFRA.map((item, i) => (
                                    <div key={i} className="flex items-center justify-between">
                                        <div>
                                            <p className="text-xs font-semibold text-white">{item.name}</p>
                                            <p className="text-[10px] text-zinc-500">{item.role}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[10px] font-bold text-emerald-400 uppercase">Online</p>
                                            <p className="text-[10px] text-zinc-500 font-mono">{item.load || item.throughput || item.connections}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section>
                            <h2 className="text-sm font-semibold text-zinc-400 mb-4 flex items-center gap-2 uppercase tracking-widest">
                                <Shield size={14} className="text-emerald-400" /> Security Privacy
                            </h2>
                            <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-2xl p-5 space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-zinc-400 font-medium">PII Redacted</span>
                                    <span className="text-emerald-400 font-bold">14,251</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-zinc-400 font-medium">Safe AST Scans</span>
                                    <span className="text-emerald-400 font-bold">892</span>
                                </div>
                                <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 w-[85%] rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                                </div>
                                <p className="text-[10px] text-zinc-500 leading-relaxed italic">
                                    &quot;Organizational safety layers are active. Performance overhead: &lt;0.5ms&quot;
                                </p>
                            </div>
                        </section>

                        <section className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                           <div className="absolute -right-4 -bottom-4 text-white/[0.03] transform group-hover:scale-110 transition-transform duration-500">
                               <Network size={120} />
                           </div>
                           <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                               <Globe size={16} className="text-blue-400" /> OpenTelemetry
                           </h3>
                           <p className="text-[11px] text-zinc-400 mb-4 leading-relaxed">
                               Full-stack context propagation is active. All services are reporting to the central OTLP collector.
                           </p>
                           <button className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-blue-500/10">
                               Open Jaeger UI <ExternalLink size={12} />
                           </button>
                        </section>
                    </div>
                </div>
            </main>
        </div>
    )
}
