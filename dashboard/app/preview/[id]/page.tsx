'use client'

export const runtime = 'edge';

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { ArrowLeft, Code, Database, Globe, Server, CheckCircle2, ChevronRight, FileJson, Sparkles, Terminal } from 'lucide-react'
import { clsx } from 'clsx'

export default function ProjectPreview() {
    const params = useParams()
    const router = useRouter()
    const [project, setProject] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [activeTab, setActiveTab] = useState('preview') // preview | code | architecture
    const [activeFile, setActiveFile] = useState<any>(null)

    useEffect(() => {
        if (!params.id) return
        api.getProject(params.id as string)
            .then((res: any) => {
                setProject(res)
                
                // If there are code files, set the first one as active
                if (res.artifacts?.by_type?.code?.length > 0) {
                    setActiveFile(res.artifacts.by_type.code[0])
                }
                
                setLoading(false)
            })
            .catch((err: any) => {
                console.error(err)
                setError('Failed to load simulated deployment. The backend may have been restarted.')
                setLoading(false)
            })
    }, [params.id])

    if (loading) {
        return (
            <div className="min-h-screen bg-[#09090b] text-white flex flex-col items-center justify-center gap-4">
                <Sparkles className="animate-pulse text-emerald-500" size={32} />
                <p className="text-zinc-400 font-mono text-sm tracking-widest uppercase">Connecting to Fargate Sandbox...</p>
            </div>
        )
    }

    if (error || !project) {
        return (
            <div className="min-h-screen bg-[#09090b] text-white flex flex-col items-center justify-center gap-4">
                <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mb-4">
                    <Globe size={24} />
                </div>
                <h1 className="text-xl font-bold">Preview Environment Unavailable</h1>
                <p className="text-zinc-500">{error}</p>
                <button onClick={() => router.push('/chat')} className="mt-4 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/5">
                    Return to Dashboard
                </button>
            </div>
        )
    }

    // Extract artifacts safely
    const codeFiles = project.artifacts?.by_type?.code || []
    const documents = project.artifacts?.by_type?.document || []
    
    // Find business plan and architecture if available
    const planArtifact = documents.find((d: any) => d.name === 'business_plan')
    const archArtifact = documents.find((d: any) => d.name === 'system_architecture')
    
    // Parse strings if they were saved as strings, else use object directly
    let plan = planArtifact?.content_preview || {}
    let arch = archArtifact?.content_preview || {}
    try { if (typeof plan === 'string') plan = JSON.parse(plan) } catch(e){}
    try { if (typeof arch === 'string') arch = JSON.parse(arch) } catch(e){}

    const features = plan.mvp_features || [
        { name: 'User Authentication', priority: 'P0', description: 'Secure login system' },
        { name: 'Core Dashboard', priority: 'P0', description: 'Main user interface' },
    ]

    return (
        <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col selection:bg-emerald-500/30">
            {/* Header / Browser Chrome Bar */}
            <div className="h-14 border-b border-white/10 bg-[#09090b]/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-50">
                <div className="flex items-center gap-4">
                    <button onClick={() => router.push('/chat')} className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 text-zinc-400 hover:text-white transition-colors">
                        <ArrowLeft size={16} />
                    </button>
                    <div className="flex items-center gap-2 text-sm font-mono text-zinc-500 bg-white/5 px-3 py-1 rounded-full border border-white/5">
                        <Globe size={14} className="text-emerald-500" />
                        <span>preview.{params.id}.proximus.net</span>
                    </div>
                </div>
                
                <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/5">
                    {['preview', 'architecture', 'code'].map(tab => (
                        <button 
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={clsx(
                                "px-3 py-1.5 text-xs font-medium rounded-md capitalize transition-all",
                                activeTab === tab ? "bg-white/10 text-white shadow-sm" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
                            )}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {activeTab === 'preview' && (
                    <div className="flex-1 overflow-y-auto w-full custom-scrollbar">
                        {/* Mock Deployed Application UI */}
                        <div className="max-w-5xl mx-auto p-8 w-full mt-8">
                            <div className="bg-white text-slate-900 rounded-2xl shadow-2xl overflow-hidden min-h-[600px] flex flex-col border border-slate-200">
                                {/* App Nav */}
                                <div className="h-16 border-b border-slate-100 flex items-center px-6 justify-between flex-shrink-0 bg-white">
                                    <div className="font-bold text-xl tracking-tight text-slate-800 flex items-center gap-2">
                                        <div className="w-6 h-6 rounded bg-indigo-600"></div>
                                        {plan.vision ? plan.vision.split(' ')[0] + 'App' : 'AI-Generated App'}
                                    </div>
                                    <div className="flex items-center gap-4 text-sm font-medium text-slate-500">
                                        <span>Dashboard</span>
                                        <span>Settings</span>
                                        <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 ml-2"></div>
                                    </div>
                                </div>
                                
                                <div className="flex-1 p-8 bg-slate-50">
                                    <h1 className="text-3xl font-extrabold text-slate-900 mb-2">{plan.vision || "Your Generated Application"}</h1>
                                    <p className="text-slate-500 mb-8 max-w-2xl leading-relaxed">
                                        {plan.problem_statement || "This app was autonomously built from your prompt. The CTO drafted the architecture, and the engineers wrote the React frontend and FastAPI backend."}
                                    </p>
                                    
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {features.map((f: any, i: number) => (
                                            <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex gap-4">
                                                <div className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 flex-shrink-0">
                                                    <CheckCircle2 size={20} />
                                                </div>
                                                <div>
                                                    <h3 className="font-bold text-slate-800">{f.name}</h3>
                                                    <p className="text-sm text-slate-500 mt-1">{f.description}</p>
                                                    <span className="inline-block mt-3 text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                                                        {f.priority || 'P0'}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'architecture' && (
                    <div className="flex-1 overflow-y-auto p-8 w-full custom-scrollbar">
                        <div className="max-w-4xl mx-auto space-y-8">
                            <div>
                                <h2 className="text-2xl font-bold flex items-center gap-3">
                                    <Database className="text-purple-400" />
                                    System Architecture
                                </h2>
                                <p className="text-zinc-400 mt-2">The blueprint generated by the virtual CTO agent.</p>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-white/[0.03] border border-white/10 rounded-xl p-6">
                                    <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2 mb-4">
                                        <Globe size={18} /> Frontend
                                    </h3>
                                    <ul className="space-y-3 font-mono text-sm text-zinc-300">
                                        <li className="flex gap-2">
                                            <span className="text-zinc-500 w-24">Framework:</span> 
                                            <span className="text-white">{arch.frontend?.framework || 'Next.js'}</span>
                                        </li>
                                        <li className="flex gap-2">
                                            <span className="text-zinc-500 w-24">Hosting:</span> 
                                            <span className="text-white">{arch.frontend?.hosting || 'Vercel / ECS'}</span>
                                        </li>
                                    </ul>
                                </div>

                                <div className="bg-white/[0.03] border border-white/10 rounded-xl p-6">
                                    <h3 className="text-lg font-semibold text-blue-400 flex items-center gap-2 mb-4">
                                        <Server size={18} /> Backend
                                    </h3>
                                    <ul className="space-y-3 font-mono text-sm text-zinc-300">
                                        <li className="flex gap-2">
                                            <span className="text-zinc-500 w-24">Framework:</span> 
                                            <span className="text-white">{arch.backend?.framework || 'FastAPI'}</span>
                                        </li>
                                        <li className="flex gap-2">
                                            <span className="text-zinc-500 w-24">Database:</span> 
                                            <span className="text-white">{arch.database?.type || 'PostgreSQL'}</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>

                            {/* Raw Plan Fallback */}
                            <div className="mt-8">
                                <h3 className="text-lg font-semibold mb-3">Raw CTO Blueprint Output</h3>
                                <pre className="bg-[#121214] border border-white/10 rounded-xl p-4 overflow-x-auto text-xs font-mono text-zinc-300 whitespace-pre-wrap">
                                    {JSON.stringify(arch, null, 2)}
                                </pre>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'code' && (
                    <div className="flex-1 flex overflow-hidden">
                        {/* File Tree Sidebar */}
                        <div className="w-64 border-r border-white/5 bg-[#09090b] flex flex-col flex-shrink-0">
                            <div className="p-4 border-b border-white/5 font-semibold text-sm flex items-center gap-2">
                                <Terminal size={14} className="text-emerald-400" /> Source Files
                            </div>
                            <div className="flex-1 overflow-y-auto p-2 space-y-0.5 custom-scrollbar">
                                {codeFiles.map((file: any) => (
                                    <button
                                        key={file.id}
                                        onClick={() => setActiveFile(file)}
                                        className={clsx(
                                            "w-full text-left px-3 py-2 text-xs font-mono rounded flex items-center gap-2 transition-colors",
                                            activeFile?.id === file.id ? "bg-white/10 text-emerald-400" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                                        )}
                                    >
                                        <Code size={12} className="opacity-50" />
                                        <span className="truncate">{file.name}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                        
                        {/* Code Editor View */}
                        <div className="flex-1 bg-[#121214] flex flex-col overflow-hidden relative">
                            {activeFile ? (
                                <>
                                    <div className="h-10 bg-[#09090b] border-b border-white/5 flex items-center px-4 gap-2 text-xs font-mono text-zinc-400">
                                        <FileJson size={12} /> {activeFile.name}
                                    </div>
                                    <div className="flex-1 overflow-auto p-4 custom-scrollbar text-xs font-mono leading-loose text-zinc-300 whitespace-pre">
                                        {activeFile.content_preview || "/* File content could not be loaded into preview buffer */"}
                                        {/* If it's fully truncated we'd need a separate endpoint to fetch original content, but content_preview has the first 300 chars or so. For the demo, this is sufficient. */}
                                    </div>
                                </>
                            ) : (
                                <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
                                    Select a file from the tree to view its contents.
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
