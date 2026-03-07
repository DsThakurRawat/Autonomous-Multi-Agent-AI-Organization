// ── Typed API client for the AI Organization backend ────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

// ── Types ─────────────────────────────────────────────────────────────

export interface Project {
    id: string
    name: string
    description: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    budget_usd: number
    spent_usd: number
    progress_pct: number
    tasks_total: number
    tasks_done: number
    created_at: string
    completed_at?: string
}

export interface AgentStatus {
    role: string
    status: 'idle' | 'processing' | 'error'
    tasks_done: number
    success_rate: number
    avg_latency_ms: number
    current_task?: string
}

export interface SystemMetrics {
    active_projects: number
    total_projects: number
    total_tasks_run: number
    total_llm_cost_usd: number
    uptime_seconds: number
    kafka_lag: Record<string, number>
}

export interface CreateProjectRequest {
    idea: string
    budget_usd: number
    name?: string
}

export interface TaskNode {
    id: string
    name: string
    agent_role: string
    status: string
    depends_on: string[]
    started_at?: string
    duration_ms?: number
}

// ── Fetch helper ─────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options?.headers as Record<string, string>),
        },
        ...options,
    })

    if (!res.ok) {
        let errorMessage = `API Error (${res.status})`
        try {
            const errorBody = await res.json()
            errorMessage = errorBody.error || errorBody.message || errorMessage
        } catch {
            const text = await res.text()
            errorMessage = text || errorMessage
        }
        throw new Error(errorMessage)
    }

    return res.json() as Promise<T>
}

// ── Projects ─────────────────────────────────────────────────────────

export const api = {
    // Health
    health: () =>
        apiFetch<{ status: string; uptime_seconds: number }>('/healthz'),

    // Projects — Go Gateway: /v1/projects
    listProjects: () =>
        apiFetch<Project[]>('/v1/projects'),

    getProject: (id: string) =>
        apiFetch<Project>(`/v1/projects/${id}`),

    createProject: (data: CreateProjectRequest) =>
        apiFetch<Project>('/v1/projects', {
            method: 'POST',
            body: JSON.stringify({
                idea: data.idea,
                budget: { max_cost_usd: data.budget_usd },
                name: data.name ?? '',
                // user_id and tenant_id come from the JWT in the Go Gateway middleware
            }),
        }),

    cancelProject: (id: string, reason = 'User cancelled') =>
        apiFetch<void>(`/v1/projects/${id}`, {
            method: 'DELETE',
            body: JSON.stringify({ reason }),
        }),

    // Tasks / DAG — Go Gateway: /v1/projects/:id/tasks
    getProjectTasks: (projectId: string) =>
        apiFetch<TaskNode[]>(`/v1/projects/${projectId}/tasks`),

    // Cost report — Go Gateway: /v1/projects/:id/cost
    getProjectCost: (projectId: string) =>
        apiFetch<{ total_usd: number; by_agent: Record<string, number> }>(
            `/v1/projects/${projectId}/cost`
        ),

    // Settings — LLM key management (Go Gateway: /v1/settings/keys)
    listKeys: () =>
        apiFetch<{ keys: unknown[]; total: number }>('/v1/settings/keys'),

    addKey: (provider: string, apiKey: string, label = 'default') =>
        apiFetch<unknown>('/v1/settings/keys', {
            method: 'POST',
            body: JSON.stringify({ provider, api_key: apiKey, label }),
        }),

    deleteKey: (id: string) =>
        apiFetch<void>(`/v1/settings/keys/${id}`, { method: 'DELETE' }),

    // Settings — Agent model preferences (Go Gateway: /v1/settings/agent-prefs)
    getAgentPrefs: () =>
        apiFetch<{ prefs: unknown[] }>('/v1/settings/agent-prefs'),

    setAgentPref: (payload: {
        agent_role: string;
        provider: string;
        model_name: string;
        key_id?: string;
        model_params?: Record<string, unknown>;
    }) =>
        apiFetch<unknown>('/v1/settings/agent-prefs', {
            method: 'POST',
            body: JSON.stringify(payload),
        }),

    resetAgentPref: (role: string) =>
        apiFetch<void>(`/v1/settings/agent-prefs/${role}`, { method: 'DELETE' }),
}

// ── Utility helpers ───────────────────────────────────────────────────

export function formatCost(usd: number): string {
    if (usd < 0.001) return `$${(usd * 1000).toFixed(3)}m`
    if (usd < 1) return `$${usd.toFixed(4)}`
    return `$${usd.toFixed(2)}`
}

export function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
    return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`
}

export const AGENT_COLORS: Record<string, string> = {
    CEO: '#4f8ef7',
    CTO: '#8b5cf6',
    Engineer_Backend: '#10b981',
    Engineer_Frontend: '#22d3ee',
    QA: '#f59e0b',
    DevOps: '#ec4899',
    Finance: '#6b7280',
    system: '#4b5563',
}

export const AGENT_EMOJI: Record<string, string> = {
    CEO: '👔',
    CTO: '🏗️',
    Engineer_Backend: '⚙️',
    Engineer_Frontend: '🎨',
    QA: '🔍',
    DevOps: '🚀',
    Finance: '💰',
    system: '🤖',
}
