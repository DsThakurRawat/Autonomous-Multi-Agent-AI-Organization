'use client'

import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { api, Project, TaskNode, AGENT_EMOJI } from '@/lib/api'
import AgentFeed from '@/components/AgentFeed'
import DagViewer from '@/components/DagViewer'
import CostMeter from '@/components/CostMeter'
import MetricsPanel from '@/components/MetricsPanel'
import InterventionModal, { InterventionData } from '@/components/InterventionModal'
import {
    Plus, RefreshCw, Cpu, ChevronRight,
    CheckCircle2, Clock, AlertCircle, Loader2,
    Braces, Github, Settings, Sparkles, Folder, Activity
} from 'lucide-react'
import Link from 'next/link'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'

// ── New Project Modal ─────────────────────────────────────────────
function NewProjectModal({ onClose, onCreate }: {
    onClose: () => void
    onCreate: (idea: string, budget: number) => Promise<void>
}) {
    const [idea, setIdea] = useState('')
    const [budget, setBudget] = useState(10)
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
            <div className="relative bg-[#09090b] border border-white/10 rounded-2xl p-6 w-full max-w-lg shadow-2xl z-10 animate-slide-up">
                <h2 className="text-lg font-semibold mb-1 text-white flex items-center gap-2">
                    <Sparkles size={18} className="text-emerald-500" /> Start New Project
                </h2>
                <p className="text-sm text-zinc-400 mb-5">Describe your idea — the AI agents will do the rest</p>

                {/* Idea input */}
                <div className="mb-4">
                    <label className="block text-xs text-zinc-500 mb-1.5 uppercase tracking-wider font-semibold">Business Idea</label>
                    <textarea
                        value={idea}
                        onChange={e => setIdea(e.target.value)}
                        placeholder="What do you want to build?"
                        rows={4}
                        className="w-full bg-[#121214] border border-white/5 rounded-xl p-3 text-sm text-white
                       placeholder-zinc-600 resize-none focus:outline-none focus:border-emerald-500/50
                       focus:ring-1 focus:ring-emerald-500/20 transition-all font-sans"
                    />
                </div>

                {/* Example ideas */}
                <div className="mb-4">
                    <p className="text-xs text-zinc-500 mb-2 font-semibold">Examples:</p>
                    <div className="flex flex-wrap gap-1.5">
                        {EXAMPLES.map((ex, i) => (
                            <button
                                key={i}
                                onClick={() => setIdea(ex)}
                                className="text-[11px] px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-white/5
                               text-zinc-400 hover:text-white
                               rounded-full transition-all duration-150 cursor-pointer text-left"
                            >
                                {ex.slice(0, 45)}…
                            </button>
                        ))}
                    </div>
                </div>

                {/* Budget slider */}
                <div className="mb-6">
                    <label className="flex items-center justify-between text-xs text-zinc-500 mb-1.5 uppercase tracking-wider font-semibold">
                        Budget
                        <span className="text-emerald-400 font-mono font-medium">${budget}</span>
                    </label>
                    <input
                        type="range"
                        min={5} max={100} step={5}
                        value={budget}
                        onChange={e => setBudget(Number(e.target.value))}
                        className="w-full accent-emerald-500 cursor-pointer"
                    />
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg bg-[#18181b] hover:bg-[#27272a] text-white text-sm font-medium transition-colors flex-1">Cancel</button>
                    <button
                        onClick={handleSubmit}
                        disabled={!idea.trim() || busy}
                        className={clsx(
                            'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors',
                            (!idea.trim() || busy) && 'opacity-50 cursor-not-allowed'
                        )}
                    >
                        {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
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
        pending: { icon: <Clock size={12} />, color: 'text-zinc-400' },
        running: { icon: <Loader2 size={12} className="animate-spin" />, color: 'text-blue-400' },
        completed: { icon: <CheckCircle2 size={12} />, color: 'text-emerald-400' },
        failed: { icon: <AlertCircle size={12} />, color: 'text-red-400' },
    }[project.status] || { icon: null, color: 'text-zinc-400' }

    return (
        <button
            onClick={onClick}
            className={clsx(
                'w-full text-left p-3 rounded-xl transition-all duration-200 group',
                isSelected
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : 'bg-transparent border border-transparent hover:bg-white/5'
            )}
        >
            <div className="flex items-start justify-between gap-2">
                <p className={clsx("text-sm font-medium truncate", isSelected ? 'text-emerald-400' : 'text-zinc-300 group-hover:text-white')}>{project.name}</p>
                <span className={clsx("flex items-center gap-1 text-xs", statusConfig.color)}>
                    {statusConfig.icon}
                </span>
            </div>
            {/* Progress bar */}
            {project.status === 'running' && (
                <div className="mt-2 h-1 bg-black/50 rounded-full overflow-hidden border border-white/5">
                    <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                        style={{ width: `${project.progress_pct || 0}%` }}
                    />
                </div>
            )}
            <div className="flex items-center gap-3 mt-2 text-[11px] text-zinc-500 font-mono">
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
    const [tasks, setTasks] = useState<TaskNode[]>([])
    const [selectedProject, setSelectedProject] = useState<Project | null>(null)
    const [showModal, setShowModal] = useState(false)
    const [interventionData, setInterventionData] = useState<InterventionData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [apiOnline, setApiOnline] = useState(false)

    const { status: wsStatus, events, latency, clearEvents, injectMockEvent } = useWebSocket({
        projectId: selectedProject?.id,
    })

    // ── Data fetching ───────────────────────────────────────────────
    const fetchAll = useCallback(async () => {
        try {
            const [ps] = await Promise.allSettled([
                api.listProjects(),
            ])
            if (ps.status === 'fulfilled') setProjects(ps.value)
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

    // ── Live Stream Synchronization ──────────────────────────────────
    useEffect(() => {
        if (events.length === 0) return
        const latestEvent = events[0] // Newest event

        // 1. Instantly animate the DAG Viewer nodes
        if (['task_start', 'task_complete', 'task_failed'].includes(latestEvent.type)) {
            const taskId = latestEvent.data?.task_id as string | undefined
            if (taskId) {
                const newStatus = latestEvent.type === 'task_start' ? 'running' : 
                                  latestEvent.type === 'task_complete' ? 'completed' : 'failed'
                setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t))
            } else {
                if (selectedProject) fetchTasks(selectedProject.id)
            }
        }

        // 2. Handle Human-in-the-Loop Interventions
        if (latestEvent.type === 'phase_change' && latestEvent.data?.status === 'pending_approval') {
            const d = latestEvent.data
            setInterventionData({
                projectId: (d.project_id || latestEvent.project_id) as string,
                taskId: (d.task_id || '') as string,
                agentRole: (d.agent_role || latestEvent.agent) as string,
                actionType: d.action_type as string,
                costEstimate: d.cost_estimate as number,
                details: d.details as string
            })
        }
    }, [events, selectedProject, fetchTasks])

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
        <div className="min-h-screen flex flex-col bg-[#09090b] text-white selection:bg-emerald-500/30">
            {/* ── Header ─────────────────────────────────────────────── */}
            <header className="bg-[#09090b]/80 backdrop-blur-md border-b border-white/5 px-6 py-3 flex items-center justify-between sticky top-0 z-40">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                        <Sparkles size={16} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-sm font-semibold tracking-tight text-white">Proximus</h1>
                        <p className="text-[10px] text-emerald-400 font-medium">Live Orchestrator</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* API status */}
                    <div className={clsx(
                        'flex items-center gap-1.5 text-[11px] px-3 py-1 rounded-full font-mono uppercase tracking-wider',
                        apiOnline
                            ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                            : 'text-red-400 bg-red-500/10 border border-red-500/20'
                    )}>
                        <span className={clsx('w-1.5 h-1.5 rounded-full', apiOnline ? 'bg-emerald-400' : 'bg-red-400',
                            apiOnline && 'animate-pulse')} />
                        {apiOnline ? 'Online' : 'Offline'}
                    </div>

                    <div className="h-4 w-px bg-white/10 mx-1"></div>

                    <button onClick={fetchAll} className="p-2 text-zinc-400 hover:text-white transition-colors" title="Refresh">
                        <RefreshCw size={16} />
                    </button>

                    <Link href="/settings" className="p-2 text-zinc-400 hover:text-white transition-colors" title="Settings">
                        <Settings size={16} />
                    </Link>

                    <Link href="/observability" className="p-2 text-zinc-400 hover:text-white transition-colors" title="System Health">
                        <Activity size={16} />
                    </Link>

                    <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white text-black hover:bg-zinc-200 text-sm font-medium transition-colors ml-2">
                        <Plus size={16} />
                        New Project
                    </button>
                </div>
            </header>

            {/* Offline Banner */}
            {(wsStatus === 'disconnected' || wsStatus === 'error' || wsStatus === 'connecting') && activeProject && (
                <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 flex items-center justify-center gap-2 text-amber-500 text-xs font-medium w-full z-40 relative">
                    <Loader2 size={12} className="animate-spin flex-shrink-0" />
                    <span>{wsStatus === 'connecting' ? 'Connecting to orchestrator...' : 'Connection lost. Trying to reconnect...'}</span>
                </div>
            )}

            {/* ── Body ───────────────────────────────────────────────── */}
            <div className="flex flex-1 overflow-hidden relative">

                {/* Sidebar — Project List */}
                <aside className="w-72 flex-shrink-0 border-r border-white/5 flex flex-col bg-[#09090b]">
                    <div className="px-5 py-4 flex items-center gap-2 border-b border-white/5 flex-shrink-0">
                        <Folder size={14} className="text-zinc-500" />
                        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">Projects</p>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar">
                        {isLoading
                            ? Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="h-[76px] rounded-xl bg-white/5 animate-pulse" />
                            ))
                            : projects.length === 0
                                ? <div className="text-center text-xs text-zinc-500 pt-10">
                                    <p>No projects yet</p>
                                    <button onClick={() => setShowModal(true)} className="mt-4 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white flex items-center justify-center gap-2 mx-auto transition-colors">
                                        <Plus size={14} /> Start one
                                    </button>
                                </div>
                                : projects.map(p => (
                                    <div key={p.id} className="relative group/item">
                                        <ProjectItem
                                            project={p}
                                            isSelected={selectedProject?.id === p.id}
                                            onClick={() => setSelectedProject(p)}
                                        />
                                        {selectedProject?.id === p.id && (
                                            <div className="absolute right-2 top-2 hidden group-hover/item:flex items-center gap-1">
                                                 <button className="p-1.5 rounded bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors border border-white/5 backdrop-blur" title="Fork Context" onClick={(e) => { e.stopPropagation(); alert('Forking context...') }}>
                                                     <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="18" r="3"></circle><circle cx="6" cy="6" r="3"></circle><circle cx="18" cy="6" r="3"></circle><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"></path><path d="M12 12v3"></path></svg>
                                                 </button>
                                                 <button className="p-1.5 rounded bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-red-400 transition-colors border border-white/5 backdrop-blur" title="Rollback System" onClick={(e) => { e.stopPropagation(); alert('Rolling back to previous checkpoint...') }}>
                                                     <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
                                                 </button>
                                            </div>
                                        )}
                                    </div>
                                ))
                        }
                    </div>
                </aside>

                {/* Main content */}
                <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
                    {/* Metrics strip */}
                    <MetricsPanel metrics={null} agents={[]} isLoading={isLoading} />

                    {/* Middle row: DAG + Cost */}
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                        <div className="xl:col-span-2 bg-[#121214] border border-white/5 rounded-2xl overflow-hidden shadow-sm hover:border-white/10 transition-colors">
                            <DagViewer tasks={tasks} projectId={activeProject?.id || ''} />
                        </div>
                        <div className="bg-[#121214] border border-white/5 rounded-2xl p-6 shadow-sm hover:border-white/10 transition-colors">
                            <CostMeter
                                budgetUsd={activeProject?.budget_usd || 100}
                                spentUsd={activeProject?.spent_usd || 0}
                            />
                        </div>
                    </div>

                    {/* Agent Feed — full width */}
                    <div className="w-full">
                        <AgentFeed
                            events={events}
                            status={wsStatus}
                            latency={latency}
                            onClear={clearEvents}
                        />
                    </div>
                </main>
            </div>

            {/* Modals */}
            {showModal && (
                <NewProjectModal
                    onClose={() => setShowModal(false)}
                    onCreate={handleCreate}
                />
            )}
            
            {interventionData && (
                <InterventionModal
                    data={interventionData}
                    onClose={() => setInterventionData(null)}
                />
            )}
        </div>
    )
}
