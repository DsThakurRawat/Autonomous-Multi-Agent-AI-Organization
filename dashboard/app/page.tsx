'use client'

import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { api, Project, AgentStatus, SystemMetrics, TaskNode, AGENT_EMOJI } from '@/lib/api'
import AgentFeed from '@/components/AgentFeed'
import DagViewer from '@/components/DagViewer'
import CostMeter from '@/components/CostMeter'
import MetricsPanel from '@/components/MetricsPanel'
import {
    Plus, RefreshCw, Cpu, ChevronRight,
    CheckCircle2, Clock, AlertCircle, Loader2,
    Braces, Github
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'

// ── New Project Modal ─────────────────────────────────────────────
function NewProjectModal({ onClose, onCreate }: {
    onClose: () => void
    onCreate: (idea: string, budget: number) => Promise<void>
}) {
    const [idea, setIdea] = useState('')
    const [budget, setBudget] = useState(100)
    const [busy, setBusy] = useState(false)

    const EXAMPLES = [
        'A SaaS platform for restaurant order tracking with real-time updates',
        'An AI-powered code review tool for GitHub pull requests',
        'A personal finance dashboard with budget alerts and spending analytics',
        'A multi-tenant task management app with Slack integration',
    ]

    const handleSubmit = async () => {
        if (!idea.trim() || busy) return
        setBusy(true)
        try {
            await onCreate(idea.trim(), budget)
            onClose()
        } catch (e) {
            console.error(e)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
            <div className="relative bg-[#16161f] border border-[#252535] rounded-2xl p-6 w-full max-w-lg shadow-2xl z-10 animate-slide-up">
                <h2 className="text-lg font-semibold mb-1">🚀 Start New Project</h2>
                <p className="text-sm text-text-muted mb-5">Describe your idea — the AI organization will do the rest</p>

                {/* Idea input */}
                <div className="mb-4">
                    <label className="block text-xs text-text-muted mb-1.5 uppercase tracking-wider">Business Idea</label>
                    <textarea
                        value={idea}
                        onChange={e => setIdea(e.target.value)}
                        placeholder="Describe what you want to build..."
                        rows={4}
                        className="w-full bg-[#111118] border border-[#252535] rounded-xl p-3 text-sm text-text-primary
                       placeholder-text-muted resize-none focus:outline-none focus:border-blue-500/60
                       focus:ring-1 focus:ring-blue-500/20 transition-all font-sans"
                    />
                </div>

                {/* Example ideas */}
                <div className="mb-4">
                    <p className="text-xs text-text-muted mb-2">Examples:</p>
                    <div className="flex flex-wrap gap-1.5">
                        {EXAMPLES.map((ex, i) => (
                            <button
                                key={i}
                                onClick={() => setIdea(ex)}
                                className="text-xs px-2.5 py-1 bg-[#1c1c28] hover:bg-[#252535] border border-[#252535]
                           hover:border-blue-500/40 text-text-muted hover:text-text-primary
                           rounded-full transition-all duration-150 cursor-pointer text-left"
                            >
                                {ex.slice(0, 45)}…
                            </button>
                        ))}
                    </div>
                </div>

                {/* Budget slider */}
                <div className="mb-5">
                    <label className="flex items-center justify-between text-xs text-text-muted mb-1.5 uppercase tracking-wider">
                        Budget
                        <span className="text-blue-400 font-mono font-medium">${budget}</span>
                    </label>
                    <input
                        type="range"
                        min={10} max={1000} step={10}
                        value={budget}
                        onChange={e => setBudget(Number(e.target.value))}
                        className="w-full accent-blue-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted mt-1">
                        <span>$10 (demo)</span>
                        <span>$1000 (production)</span>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                    <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
                    <button
                        onClick={handleSubmit}
                        disabled={!idea.trim() || busy}
                        className={clsx(
                            'btn-primary flex-1 justify-center',
                            (!idea.trim() || busy) && 'opacity-50 cursor-not-allowed'
                        )}
                    >
                        {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                        {busy ? 'Starting...' : 'Launch Project'}
                    </button>
                </div>
            </div>
        </div>
    )
}

// ── Project List Item ─────────────────────────────────────────────
function ProjectItem({ project, isSelected, onClick }: {
    project: Project
    isSelected: boolean
    onClick: () => void
}) {
    const statusConfig = {
        pending: { icon: <Clock size={11} />, cls: 'badge-pending' },
        running: { icon: <Loader2 size={11} className="animate-spin" />, cls: 'badge-info' },
        completed: { icon: <CheckCircle2 size={11} />, cls: 'badge-success' },
        failed: { icon: <AlertCircle size={11} />, cls: 'badge-error' },
    }[project.status] || { icon: null, cls: 'badge-pending' }

    return (
        <button
            onClick={onClick}
            className={clsx(
                'w-full text-left p-3 rounded-xl border transition-all duration-150',
                isSelected
                    ? 'bg-blue-500/10 border-blue-500/40'
                    : 'bg-[#16161f] border-[#252535] hover:bg-[#1c1c28] hover:border-[#3a3a55]'
            )}
        >
            <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-text-primary truncate">{project.name}</p>
                <span className={statusConfig.cls}>
                    {statusConfig.icon}
                    {project.status}
                </span>
            </div>
            {/* Progress bar */}
            {project.status === 'running' && (
                <div className="mt-2 h-1 bg-[#252535] rounded-full overflow-hidden">
                    <div
                        className="h-full bg-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${project.progress_pct || 0}%` }}
                    />
                </div>
            )}
            <div className="flex items-center gap-3 mt-1.5 text-[11px] text-text-muted">
                <span>{project.tasks_done}/{project.tasks_total} tasks</span>
                <span className="ml-auto">
                    {formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}
                </span>
            </div>
        </button>
    )
}

// ── Main Page ─────────────────────────────────────────────────────
export default function DashboardPage() {
    const [projects, setProjects] = useState<Project[]>([])
    const [agents, setAgents] = useState<AgentStatus[]>([])
    const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
    const [tasks, setTasks] = useState<TaskNode[]>([])
    const [selectedProject, setSelectedProject] = useState<Project | null>(null)
    const [showModal, setShowModal] = useState(false)
    const [isLoading, setIsLoading] = useState(true)
    const [apiOnline, setApiOnline] = useState(false)

    const { status: wsStatus, events, latency, clearEvents, injectMockEvent } = useWebSocket({
        projectId: selectedProject?.id,
    })

    // ── Data fetching ───────────────────────────────────────────────
    const fetchAll = useCallback(async () => {
        try {
            const [ps, as, ms] = await Promise.allSettled([
                api.listProjects(),
                api.listAgents(),
                api.getMetrics(),
            ])
            if (ps.status === 'fulfilled') setProjects(ps.value)
            if (as.status === 'fulfilled') setAgents(as.value)
            if (ms.status === 'fulfilled') setMetrics(ms.value)
            setApiOnline(true)
        } catch {
            setApiOnline(false)
        } finally {
            setIsLoading(false)
        }
    }, [])

    const fetchTasks = useCallback(async (projectId: string) => {
        try {
            const ts = await api.getProjectTasks(projectId)
            setTasks(ts)
        } catch {
            setTasks([])
        }
    }, [])

    useEffect(() => {
        fetchAll()
        const interval = setInterval(fetchAll, 5000)
        return () => clearInterval(interval)
    }, [fetchAll])

    useEffect(() => {
        if (selectedProject) fetchTasks(selectedProject.id)
        else setTasks([])
    }, [selectedProject, fetchTasks])

    // ── Create project ──────────────────────────────────────────────
    const handleCreate = async (idea: string, budget: number) => {
        const project = await api.createProject({ idea, budget_usd: budget, name: idea.slice(0, 60) })
        setProjects(prev => [project, ...prev])
        setSelectedProject(project)
        // Inject a welcome event
        injectMockEvent({ type: 'system', message: `Project started: ${idea.slice(0, 80)}`, agent: 'system', level: 'info' })
    }

    const activeProject = selectedProject || projects[0] || null

    return (
        <div className="min-h-screen flex flex-col">
            {/* ── Header ─────────────────────────────────────────────── */}
            <header className="glass border-b border-[#252535] px-6 py-3 flex items-center gap-4 sticky top-0 z-40">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <Cpu size={16} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-sm font-bold text-gradient-blue">AI Organization</h1>
                        <p className="text-[10px] text-text-muted">Autonomous · Multi-Agent · Production</p>
                    </div>
                </div>

                <div className="flex items-center gap-2 ml-auto">
                    {/* API status */}
                    <div className={clsx(
                        'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border',
                        apiOnline
                            ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                            : 'text-red-400 bg-red-500/10 border-red-500/20'
                    )}>
                        <span className={clsx('w-1.5 h-1.5 rounded-full', apiOnline ? 'bg-emerald-400' : 'bg-red-400',
                            apiOnline && 'animate-pulse')} />
                        {apiOnline ? 'API Online' : 'API Offline'}
                    </div>

                    <button onClick={fetchAll} className="btn-ghost p-1.5" title="Refresh">
                        <RefreshCw size={13} />
                    </button>

                    <a
                        href="https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost p-1.5"
                    >
                        <Github size={13} />
                    </a>

                    <button onClick={() => setShowModal(true)} className="btn-primary">
                        <Plus size={14} />
                        New Project
                    </button>
                </div>
            </header>

            {/* ── Body ───────────────────────────────────────────────── */}
            <div className="flex flex-1 overflow-hidden">

                {/* Sidebar — Project List */}
                <aside className="w-64 flex-shrink-0 border-r border-[#252535] flex flex-col bg-[#0d0d14]">
                    <div className="px-4 py-3 border-b border-[#252535]">
                        <p className="text-xs text-text-muted uppercase tracking-wider">Projects ({projects.length})</p>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                        {isLoading
                            ? Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="h-20 rounded-xl bg-[#1c1c28] animate-pulse" />
                            ))
                            : projects.length === 0
                                ? <div className="text-center text-xs text-text-muted pt-10">
                                    <p>No projects yet</p>
                                    <button onClick={() => setShowModal(true)} className="mt-3 text-blue-400 hover:text-blue-300 flex items-center gap-1 mx-auto">
                                        <Plus size={12} /> Start one
                                    </button>
                                </div>
                                : projects.map(p => (
                                    <ProjectItem
                                        key={p.id}
                                        project={p}
                                        isSelected={selectedProject?.id === p.id}
                                        onClick={() => setSelectedProject(p)}
                                    />
                                ))
                        }
                    </div>
                </aside>

                {/* Main content */}
                <main className="flex-1 overflow-y-auto p-5 space-y-5">
                    {/* Metrics strip */}
                    <MetricsPanel metrics={metrics} agents={agents} isLoading={isLoading} />

                    {/* Middle row: DAG + Cost */}
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
                        <div className="xl:col-span-2">
                            <DagViewer tasks={tasks} projectId={activeProject?.id || ''} />
                        </div>
                        <div>
                            <CostMeter
                                budgetUsd={activeProject?.budget_usd || 100}
                                spentUsd={activeProject?.spent_usd || 0}
                            />
                        </div>
                    </div>

                    {/* Agent Feed — full width */}
                    <AgentFeed
                        events={events}
                        status={wsStatus}
                        latency={latency}
                        onClear={clearEvents}
                    />
                </main>
            </div>

            {/* Modal */}
            {showModal && (
                <NewProjectModal
                    onClose={() => setShowModal(false)}
                    onCreate={handleCreate}
                />
            )}
        </div>
    )
}
