'use client';

import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useEffect, useState, useRef } from 'react';
import { Loader2, Send, Plus, Settings, LogOut, MessageSquare, Terminal, ChevronRight, Sparkles } from 'lucide-react';
import { api, AGENT_COLORS } from '../../lib/api';
import AgentFeed from '@/components/AgentFeed';
import { useWebSocket } from '@/hooks/useWebSocket';

interface LogEntry {
    text: string;
    color: string;
    role?: string;
}

export default function ChatPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    
    const [prompt, setPrompt] = useState('');
    const [isExecuting, setIsExecuting] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const logsEndRef = useRef<HTMLDivElement>(null);

    const [activeProject, setActiveProject] = useState<string>('');
    const [currentPhase, setCurrentPhase] = useState<string>('');

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080';

    const { status: wsStatus, events, connect, disconnect } = useWebSocket({
        projectId: activeProject,
        onEvent: (event) => {
            if (event.type === 'phase_change') {
                setCurrentPhase(event.message);
            }
        }
    });

    // Mirror websocket events into chat logs, but ONLY show high-level events.
    // Granular task/thinking events are handled by the AgentFeed sidebar.
    useEffect(() => {
        if (events.length > 0) {
            const latest = events[0];
            
            // Filter out granular noise from the central chat
            if (['task_start', 'task_complete', 'task_completed', 'thinking', 'system'].includes(latest.type)) {
                return;
            }

            setLogs(prev => {
                if (prev.length > 0 && prev[prev.length - 1].text === latest.message) return prev;
                
                // Map agent roles for display
                let roleLabel = latest.agent;
                if (roleLabel === 'system') roleLabel = 'System';
                roleLabel = roleLabel.replace('Engineer_', 'Eng_');
                
                return [...prev, {
                    role: roleLabel,
                    text: latest.message,
                    color: AGENT_COLORS[latest.agent] || AGENT_COLORS['system'] || '#cbd5e1'
                }];
            });
            
            logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [events, activeProject]);

    useEffect(() => {
        if (status === 'unauthenticated') {
            router.push('/');
        }
    }, [status, router]);

    const handlePromptSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim() || isExecuting) return;

        setIsExecuting(true);
        const userPrompt = prompt;
        setPrompt('');
        
        // Add user prompt to the chat
        setLogs(prev => [...prev, { text: userPrompt, color: '#f8fafc', role: 'User' }]);
        setTimeout(() => {
            setLogs(prev => [...prev, { text: `Initializing project & assembling agent swarm...`, color: '#64748b', role: 'System' }]);
        }, 500);

        try {
            const project = await api.createProject({
                idea: userPrompt,
                budget_usd: 10
            });

            // The useWebSocket hook at the top will automatically connect to the new activeProject
            setActiveProject(project.id);
            setLogs(prev => [...prev, { text: `Project initialization commanded. Launching Swarm...`, color: '#64748b', role: 'System' }]);
            
        } catch (error: any) {
            setLogs(prev => [...prev, { text: `Error: Failed to start orchestrator: ${error.message}`, color: '#ef4444', role: 'System' }]);
            setIsExecuting(false);
        }
    };

    if (status === 'loading') {
        return <div className="min-h-screen flex items-center justify-center bg-white"><Loader2 className="animate-spin text-purple-600" size={32} /></div>;
    }

    if (!session) return null; // handled by useEffect redirect

    return (
        <div className="flex h-screen bg-[#09090b] text-white font-sans overflow-hidden">
            
            {/* Sidebar */}
            <aside className="w-72 bg-[#0c0c0e] shrink-0 border-r border-white/5 hidden md:flex flex-col">
                <div className="p-6">
                    <button className="w-full flex items-center justify-center gap-2 bg-white text-black rounded-2xl py-3.5 transition-all text-sm font-bold hover:bg-slate-200 active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                        <Plus size={18} /> New Workspace
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto px-4 space-y-2 mt-4">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest px-3 mb-4">Recent Projects</p>
                    {['SaaS Dashboard Platform', 'E-commerce API', 'Internal Admin Tool'].map((proj, i) => (
                        <button key={i} className="w-full text-left px-4 py-3 rounded-xl hover:bg-white/5 transition-colors text-sm truncate flex items-center gap-3 text-slate-400 hover:text-white group">
                            <div className="w-2 h-2 rounded-full bg-slate-700 group-hover:bg-purple-500 transition-colors" />
                            {proj}
                        </button>
                    ))}
                </div>

                <div className="p-6 border-t border-white/5 bg-[#09090b]/50">
                    <div className="flex items-center gap-4 mb-6 px-2">
                        {session.user?.image ? (
                            <Image src={session.user.image} alt="User" width={40} height={40} className="w-10 h-10 rounded-xl border border-white/10" />
                        ) : (
                            <div className="w-10 h-10 rounded-xl bg-purple-600 flex items-center justify-center text-white font-bold">{session.user?.name?.charAt(0) || 'U'}</div>
                        )}
                        <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-bold text-white truncate">{session.user?.name}</span>
                            <span className="text-xs text-slate-500 truncate">{session.user?.email}</span>
                        </div>
                    </div>
                    <div className="space-y-1">
                        <Link href="/settings" className="w-full flex items-center gap-3 text-slate-500 hover:text-white px-3 py-2.5 rounded-xl hover:bg-white/5 transition-all text-sm">
                            <Settings size={18} /> Settings
                        </Link>
                        <button onClick={() => signOut()} className="w-full flex items-center gap-3 text-slate-500 hover:text-red-400 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-all text-sm">
                            <LogOut size={18} /> Sign out
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Chat Area */}
            <main className="flex-1 flex flex-col bg-[#09090b] relative">
                
                {/* Mobile Header */}
                <header className="md:hidden flex items-center justify-between p-4 border-b border-white/5 bg-[#09090b]">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                            <Sparkles size={16} />
                        </div>
                        <span className="font-bold">Proximus</span>
                    </div>
                </header>

                {/* Connection Status Banner */}
                {(wsStatus === 'disconnected' || wsStatus === 'error' || wsStatus === 'connecting') && activeProject && (
                    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 flex items-center justify-center gap-2 text-amber-500 text-xs font-medium w-full z-50">
                        <Loader2 size={14} className="animate-spin" />
                        {wsStatus === 'connecting' ? 'Connecting to orchestrator...' : 'Connection lost. Reconnecting...'}
                    </div>
                )}

                {/* Chat History */}
                <div className="flex-1 overflow-y-auto p-4 md:p-12 space-y-8 scroll-smooth">
                    {logs.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
                            <div className="w-20 h-20 rounded-[2.5rem] bg-white/5 border border-white/10 text-purple-400 flex items-center justify-center mb-8 shadow-2xl animate-float">
                                <Sparkles size={40} />
                            </div>
                            <h2 className="text-4xl font-bold text-white mb-4">What shall we build?</h2>
                            <p className="text-slate-500 text-lg mb-12 max-w-md">Our multi-agent swarm is ready to architect, develop, and deploy your next big idea.</p>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl">
                                {[
                                    "Build a CRM dashboard for real estate agents",
                                    "Create a Next.js blog with an admin panel",
                                    "Develop a REST API for a task management app",
                                    "Set up an e-commerce storefront"
                                ].map((suggestion, i) => (
                                    <button 
                                        key={i} 
                                        onClick={() => setPrompt(suggestion)}
                                        className="text-left text-[15px] p-5 rounded-2xl border border-white/5 bg-white/5 hover:border-purple-500/50 hover:bg-white/10 transition-all text-slate-300 hover:text-white"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="max-w-4xl mx-auto space-y-8">
                            {logs.map((log, i) => {
                                const isUser = log.role === 'User';
                                const isSystem = log.role === 'System';
                                
                                if (isUser) {
                                    return (
                                        <div key={i} className="flex justify-end animate-fade-in group">
                                            <div className="bg-white text-black rounded-3xl rounded-tr-sm px-6 py-4 max-w-[85%] shadow-2xl font-medium">
                                                <p className="text-[15px] leading-relaxed">{log.text}</p>
                                            </div>
                                        </div>
                                    );
                                }
                                
                                return (
                                    <div key={i} className="flex gap-6 animate-fade-in max-w-[95%]">
                                        <div 
                                            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg text-white font-bold text-sm border border-white/10"
                                            style={{ backgroundColor: isSystem ? '#1e293b' : log.color }}
                                        >
                                            {isSystem ? <Terminal size={18} /> : log.role?.charAt(0)}
                                        </div>
                                        <div className="flex flex-col gap-2 pt-1">
                                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-3">
                                                {log.role}
                                                {isExecuting && i === logs.length - 1 && !isSystem && <span className="flex items-center"><div className="w-1 h-1 rounded-full bg-purple-500 animate-ping" /></span>}
                                            </span>
                                            <div className="text-[15px] text-slate-200 leading-relaxed font-mono bg-white/5 border border-white/5 p-5 rounded-2xl rounded-tl-sm backdrop-blur-md">
                                                {log.text}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={logsEndRef} className="h-8" />
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-6 md:p-10 bg-gradient-to-t from-[#09090b] to-transparent">
                    <div className="max-w-4xl mx-auto relative">
                        <form onSubmit={handlePromptSubmit} className="relative flex items-center">
                            <textarea 
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                disabled={isExecuting}
                                placeholder="Command the swarm..."
                                className="w-full bg-white/5 border border-white/10 rounded-[2rem] py-5 pl-6 pr-16 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-4 focus:ring-purple-500/5 resize-none overflow-hidden transition-all text-base backdrop-blur-2xl shadow-2xl"
                                rows={1}
                                style={{ minHeight: '70px', maxHeight: '200px' }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handlePromptSubmit(e as any);
                                    }
                                }}
                            />
                            <button 
                                type="submit" 
                                disabled={isExecuting || !prompt.trim()} 
                                className="absolute right-4 bottom-4 p-3 bg-white text-black rounded-2xl hover:bg-slate-200 disabled:opacity-20 disabled:bg-white/10 transition-all active:scale-90"
                            >
                                {isExecuting ? <Loader2 size={24} className="animate-spin" /> : <Send size={24} />}
                            </button>
                        </form>
                        <div className="text-center mt-4 text-[11px] font-medium text-slate-600 uppercase tracking-wider">
                            Multi-Agent Swarm Orchestration • AWS Nova-Pro
                        </div>
                    </div>
                </div>

            </main>

            {/* Agent Feed Sidebar (Desktop/Tablet) */}
            {activeProject && (
                <aside className="w-[400px] xl:w-[500px] border-l border-white/5 bg-[#070708] hidden md:flex flex-col relative">
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-purple-500 to-blue-500" />
                    <AgentFeed 
                        events={events} 
                        status={wsStatus} 
                        latency={null} 
                        onClear={() => {}} 
                    />
                </aside>
            )}
        </div>
    );
}
