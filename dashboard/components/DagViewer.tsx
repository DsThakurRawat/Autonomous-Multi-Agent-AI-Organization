'use client'

import { useCallback, useMemo } from 'react'
import ReactFlow, {
    Node,
    Edge,
    Background,
    Controls,
    MiniMap,
    BackgroundVariant,
    MarkerType,
    NodeProps,
    Handle,
    Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { TaskNode, AGENT_COLORS, AGENT_EMOJI } from '@/lib/api'
import { clsx } from 'clsx'
import { GitBranch } from 'lucide-react'

// ── Status → style mapping ─────────────────────────────────────────
const STATUS_STYLE: Record<string, { border: string; bg: string; dot: string; label: string }> = {
    completed: { border: '#10b981', bg: '#10b98115', dot: 'bg-emerald-400', label: 'Completed' },
    running: { border: '#4f8ef7', bg: '#4f8ef715', dot: 'bg-blue-400', label: 'Running' },
    pending: { border: '#252535', bg: '#16161f', dot: 'bg-slate-500', label: 'Pending' },
    failed: { border: '#ef4444', bg: '#ef444415', dot: 'bg-red-400', label: 'Failed' },
    retrying: { border: '#f59e0b', bg: '#f59e0b15', dot: 'bg-amber-400', label: 'Retrying' },
}

// ── Custom Task Node ───────────────────────────────────────────────
function TaskNodeComponent({ data }: NodeProps) {
    const style = STATUS_STYLE[data.status] || STATUS_STYLE.pending
    const color = AGENT_COLORS[data.agent_role] || '#94a3b8'
    const emoji = AGENT_EMOJI[data.agent_role] || '🤖'

    return (
        <div
            className="rounded-xl px-3 py-2.5 min-w-[160px] shadow-lg transition-all duration-200"
            style={{
                background: style.bg,
                border: `1px solid ${style.border}`,
                boxShadow: data.status === 'running' ? `0 0 12px ${style.border}50` : undefined,
            }}
        >
            <Handle type="target" position={Position.Left} style={{ background: color, border: 'none', width: 8, height: 8 }} />
            <Handle type="source" position={Position.Right} style={{ background: color, border: 'none', width: 8, height: 8 }} />

            <div className="flex items-center gap-2">
                {/* Agent avatar */}
                <span
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0"
                    style={{ backgroundColor: `${color}25`, border: `1px solid ${color}50` }}
                >
                    {emoji}
                </span>

                <div className="flex flex-col min-w-0">
                    {/* Task name */}
                    <span className="text-xs font-medium text-text-primary truncate max-w-[110px]">
                        {data.label}
                    </span>
                    {/* Agent role */}
                    <span className="text-[10px] truncate" style={{ color }}>
                        {data.agent_role?.replace('Engineer_', 'Eng·')}
                    </span>
                </div>

                {/* Status dot */}
                <span
                    className={clsx('w-2 h-2 rounded-full flex-shrink-0 ml-auto', style.dot,
                        data.status === 'running' && 'animate-pulse'
                    )}
                />
            </div>

            {/* Duration badge */}
            {data.duration_ms && (
                <div className="mt-1.5 text-[10px] text-text-muted font-mono">
                    {data.duration_ms < 1000
                        ? `${data.duration_ms}ms`
                        : `${(data.duration_ms / 1000).toFixed(1)}s`}
                </div>
            )}
        </div>
    )
}

const nodeTypes = { task: TaskNodeComponent }

// ── DagViewer ─────────────────────────────────────────────────────
interface DagViewerProps {
    tasks: TaskNode[]
    projectId: string
}

export default function DagViewer({ tasks, projectId }: DagViewerProps) {
    // Convert tasks → React Flow nodes with auto-layout (simple column layout)
    const { nodes, edges } = useMemo(() => {
        // Group tasks by dependency depth (topological columns)
        const depthMap = new Map<string, number>()
        const taskMap = new Map(tasks.map(t => [t.id, t]))

        function getDepth(id: string, visited = new Set<string>()): number {
            if (depthMap.has(id)) return depthMap.get(id)!
            if (visited.has(id)) return 0
            visited.add(id)
            const task = taskMap.get(id)
            if (!task || task.depends_on.length === 0) {
                depthMap.set(id, 0)
                return 0
            }
            const maxParentDepth = Math.max(...task.depends_on.map(d => getDepth(d, visited)))
            const depth = maxParentDepth + 1
            depthMap.set(id, depth)
            return depth
        }

        tasks.forEach(t => getDepth(t.id))

        // Count nodes per column for vertical positioning
        const colCount = new Map<number, number>()
        tasks.forEach(t => {
            const d = depthMap.get(t.id) || 0
            colCount.set(d, (colCount.get(d) || 0) + 1)
        })
        const colIndex = new Map<number, number>()

        const nodes: Node[] = tasks.map(task => {
            const col = depthMap.get(task.id) || 0
            const idx = colIndex.get(col) || 0
            colIndex.set(col, idx + 1)
            const total = colCount.get(col) || 1

            return {
                id: task.id,
                type: 'task',
                position: {
                    x: col * 220 + 40,
                    y: (idx - (total - 1) / 2) * 110 + 200,
                },
                data: {
                    label: task.name,
                    agent_role: task.agent_role,
                    status: task.status,
                    duration_ms: task.duration_ms,
                },
            }
        })

        const edges: Edge[] = tasks.flatMap(task =>
            task.depends_on.map(depId => ({
                id: `${depId}-${task.id}`,
                source: depId,
                target: task.id,
                type: 'smoothstep',
                animated: task.status === 'running',
                markerEnd: { type: MarkerType.ArrowClosed, color: '#4f8ef7' },
                style: { stroke: '#4f8ef760', strokeWidth: 1.5 },
            }))
        )

        return { nodes, edges }
    }, [tasks])

    if (tasks.length === 0) {
        return (
            <div className="card flex items-center justify-center h-[360px]">
                <div className="flex flex-col items-center gap-3 text-text-muted">
                    <GitBranch size={32} className="opacity-30" />
                    <p className="text-sm">No task graph yet</p>
                    <p className="text-xs opacity-60">Start a project to see the execution DAG</p>
                </div>
            </div>
        )
    }

    return (
        <div className="card p-0 overflow-hidden h-[360px]">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[#252535]">
                <GitBranch size={14} className="text-purple-400" />
                <h2 className="text-sm font-semibold">Task Execution Graph</h2>
                <span className="text-xs text-text-muted ml-auto">{tasks.length} tasks</span>
            </div>

            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.3}
                maxZoom={1.5}
                defaultEdgeOptions={{ animated: false }}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
            >
                <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#252535" />
                <Controls showInteractive={false} className="!bg-[#16161f] !border-[#252535]" />
                <MiniMap
                    nodeColor={(n) => {
                        const style = STATUS_STYLE[n.data?.status] || STATUS_STYLE.pending
                        return style.border
                    }}
                    maskColor="rgba(10,10,15,0.7)"
                    className="!bg-[#111118] !border-[#252535]"
                />
            </ReactFlow>
        </div>
    )
}
