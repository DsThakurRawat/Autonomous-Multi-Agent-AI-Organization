// ── Typed API client for the AI Organization backend ────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────

export interface ResearchMission {
    id: string
    name: string
    description: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    budget_usd: number
    spent_usd: number
    progress_pct: number
    milestones_total: number
    milestones_done: number
    created_at: string
    updated_at: string
    completed_at?: string
    tasks_done?: number
    tasks_total?: number
}

export type Project = ResearchMission

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

function getCsrfToken() {
    if (typeof document === 'undefined') return '';
    const match = document.cookie.match(new RegExp('(^| )csrf_=([^;]+)'));
    return match ? match[2] : '';
}

async function apiFetch<T>(path: string, options?: RequestInit & { idempotencyKey?: string }): Promise<T> {
    const headers = new Headers(options?.headers);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    if (!headers.has('Accept')) headers.set('Accept', 'application/json');
    if (options?.idempotencyKey) headers.set('X-Idempotency-Key', options.idempotencyKey);
    
    const token = getCsrfToken();
    if (token) headers.set('X-Csrf-Token', token);

    let res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: 'include',
    })

    if (res.status === 401 && !path.includes('/auth/refresh')) {
        try {
            const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
            })
            if (refreshRes.ok) {
                // Retry original request
                res = await fetch(`${API_BASE}${path}`, {
                    ...options,
                    headers,
                    credentials: 'include',
                })
            }
        } catch (e) {
            console.error('Optional token refresh failed', e)
        }
    }

    if (!res.ok) {
        let errorMessage = `API Error (${res.status})`
        if (res.status === 429) errorMessage = 'Rate limit exceeded. Please wait a moment.'
        if (res.status === 409) errorMessage = 'Request is already being processed.'
        
        try {
            const errorBody = await res.json()
            errorMessage = errorBody.error || errorBody.message || errorMessage
        } catch {
            const text = await res.text()
            if (text) errorMessage = text
        }
        throw new Error(errorMessage)
    }

    return res.json() as Promise<T>
}

// ── Projects ─────────────────────────────────────────────────────────

export const api = {
    // Health
    health: () =>
        apiFetch<{ status: string; uptime_seconds: number }>('/health'),

    // Sessions — Python Backend: /sessions
    listMissions: () =>
        apiFetch<ResearchMission[]>('/sessions'),
    listProjects: () =>
        apiFetch<Project[]>('/sessions'),

    getMission: (id: string) =>
        apiFetch<ResearchMission>(`/sessions/${id}`),
    getProjectTasks: (id: string) =>
        apiFetch<TaskNode[]>(`/sessions/${id}/messages`), // Map to messages in this architecture

    createMission: (data: CreateProjectRequest) =>
        apiFetch<ResearchMission>('/sessions', {
            method: 'POST',
            body: JSON.stringify({
                goal: data.idea,
                name: data.name ?? 'New Research Mission',
            }),
        }),
    createProject: (data: CreateProjectRequest) =>
        apiFetch<Project>('/sessions', {
            method: 'POST',
            body: JSON.stringify({
                user_email: "local@sarang.ai",
                title: data.name || "New Research"
            }),
        }),

    cancelProject: (id: string) =>
        apiFetch<void>(`/sessions/${id}`, {
            method: 'DELETE',
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
    Lead_Researcher: '#4f8ef7',
    Math_Architect: '#8b5cf6',
    Implementation_Specialist: '#10b981',
    Visual_Insights: '#22d3ee',
    Reproducibility_Engineer: '#f59e0b',
    Peer_Reviewer: '#ec4899',
    Compute_Monitor: '#6b7280',
    Orchestrator: '#4b5563',
    system: '#3f3f46',
}

export const AGENT_EMOJI: Record<string, string> = {
    Lead_Researcher: '🔬',
    Math_Architect: '📐',
    Implementation_Specialist: '💻',
    Visual_Insights: '📊',
    Reproducibility_Engineer: '♻️',
    Peer_Reviewer: '🔍',
    Compute_Monitor: '⚡',
    Orchestrator: '🧠',
    system: '🤖',
}
