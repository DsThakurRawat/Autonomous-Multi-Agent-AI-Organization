'use client'

import { useState } from 'react'
import { AlertTriangle, Check, X, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export interface InterventionData {
    projectId: string
    taskId: string
    agentRole: string
    actionType: string
    costEstimate: number
    details: string
}

interface InterventionModalProps {
    data: InterventionData
    onClose: () => void
}

export default function InterventionModal({ data, onClose }: InterventionModalProps) {
    const [busy, setBusy] = useState(false)

    const handleAction = async (approved: boolean) => {
        setBusy(true)
        try {
            await api.postIntervention(data.projectId, data.taskId, approved)
        } catch (e) {
            console.error('Intervention failed', e)
        } finally {
            setBusy(false)
            onClose()
        }
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-fade-in">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={() => !busy && onClose()} />
            <div className="relative bg-[#09090b] border-2 border-amber-500/50 rounded-2xl p-6 w-full max-w-md shadow-[0_0_40px_-10px_rgba(245,158,11,0.3)] z-10 animate-slide-up">
                
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500 border border-amber-500/20">
                        <AlertTriangle size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Human Authorization Required</h2>
                        <p className="text-xs text-amber-400 font-mono tracking-wider uppercase">Agent: {data.agentRole.replace('Engineer_', 'Eng·')}</p>
                    </div>
                </div>

                <div className="bg-[#121214] border border-white/5 rounded-xl p-4 mb-6">
                    <p className="text-sm text-zinc-300 font-medium mb-1">Action:</p>
                    <p className="text-base text-white font-semibold mb-4">{data.actionType}</p>
                    
                    {data.details && (
                        <>
                            <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-1">Details:</p>
                            <p className="text-sm text-zinc-400 mb-4 bg-black/50 p-2 rounded border border-white/5 font-mono text-xs overflow-hidden break-words">{data.details}</p>
                        </>
                    )}

                    <div className="flex items-center justify-between border-t border-white/5 pt-3">
                        <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Estimated Cost:</span>
                        <span className="text-sm font-bold text-amber-500">${(data.costEstimate || 0).toFixed(2)}</span>
                    </div>
                </div>

                <div className="flex gap-3">
                    <button 
                        onClick={() => handleAction(false)} 
                        disabled={busy}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 text-sm font-bold transition-all disabled:opacity-50"
                    >
                        {busy ? <Loader2 size={16} className="animate-spin" /> : <X size={16} />}
                        Deny Execution
                    </button>
                    <button 
                        onClick={() => handleAction(true)} 
                        disabled={busy}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black border border-emerald-500 text-sm font-bold transition-all disabled:opacity-50 shadow-[0_0_20px_-5px_CurrentColor]"
                    >
                        {busy ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                        Authorize
                    </button>
                </div>
            </div>
        </div>
    )
}
