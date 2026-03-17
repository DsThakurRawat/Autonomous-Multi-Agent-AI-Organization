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
        <div className="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden">
            
            {/* Sidebar */}
            <aside className="w-64 bg-slate-900 text-slate-300 shrink-0 border-r border-slate-800 hidden md:flex flex-col">
                <div className="p-4">
                    <button className="w-full flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg p-2.5 transition-colors text-sm font-medium">
                        <Plus size={18} /> New Workspace
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto px-2 space-y-1">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-3 py-2 mb-1">Recent Projects</p>
                    {['SaaS Dashboard Platform', 'E-commerce API', 'Internal Admin Tool'].map((proj, i) => (
                        <button key={i} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800 text-sm truncate flex items-center gap-2">
                            <MessageSquare size={14} className="text-slate-500" /> {proj}
                        </button>
                    ))}
                </div>

                <div className="p-4 border-t border-slate-800 space-y-2">
                    <div className="flex items-center gap-3 mb-4 px-2">
                        {session.user?.image ? (
                            <Image src={session.user.image} alt="User" width={32} height={32} className="w-8 h-8 rounded-full border border-slate-700" />
                        ) : (
                            <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center text-white font-bold">{session.user?.name?.charAt(0) || 'U'}</div>
                        )}
                        <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-medium text-white truncate">{session.user?.name}</span>
                            <span className="text-xs text-slate-500 truncate">{session.user?.email}</span>
                        </div>
                    </div>
                    <Link href="/settings" className="w-full flex items-center gap-3 text-slate-400 hover:text-white px-2 py-1.5 rounded-lg hover:bg-slate-800 transition-colors text-sm">
                        <Settings size={16} /> Settings
                    </Link>
                    <button onClick={() => signOut()} className="w-full flex items-center gap-3 text-slate-400 hover:text-red-400 px-2 py-1.5 rounded-lg hover:bg-slate-800 transition-colors text-sm">
                        <LogOut size={16} /> Sign out
                    </button>
                </div>
            </aside>

            {/* Main Chat Area */}
            <main className="flex-1 flex flex-col bg-white relative">
                
                {/* Mobile Header */}
                <header className="md:hidden flex items-center justify-between p-4 border-b border-slate-200 bg-white">
                    <div className="flex items-center gap-2">
                        <Sparkles size={20} className="text-purple-600" />
                        <span className="font-bold">Proximus-Nova</span>
                    </div>
                </header>

                {/* Chat History */}
                <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
                    {logs.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]">
                            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-100 to-blue-100 text-purple-600 flex items-center justify-center mb-6 shadow-inner">
                                <Sparkles size={32} />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800 mb-2">What do you want to build?</h2>
                            <p className="text-slate-500 mb-8 max-w-md">Our multi-agent swarm is ready to architect, develop, and deploy your next big idea.</p>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                                {[
                                    "Build a CRM dashboard for real estate agents",
                                    "Create a Next.js blog with an admin panel",
                                    "Develop a REST API for a task management app",
                                    "Set up an e-commerce storefront"
                                ].map((suggestion, i) => (
                                    <button 
                                        key={i} 
                                        onClick={() => setPrompt(suggestion)}
                                        className="text-left text-sm p-3 rounded-xl border border-slate-200 hover:border-purple-300 hover:bg-purple-50 transition-colors text-slate-600 hover:text-purple-700"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="max-w-4xl mx-auto space-y-6">
                            {logs.map((log, i) => {
                                const isUser = log.role === 'User';
                                const isSystem = log.role === 'System';
                                
                                if (isUser) {
                                    return (
                                        <div key={i} className="flex justify-end animate-fade-in group">
                                            <div className="bg-slate-900 text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[85%] shadow-sm">
                                                <p className="text-[15px] leading-relaxed">{log.text}</p>
                                            </div>
                                        </div>
                                    );
                                }
                                
                                return (
                                    <div key={i} className="flex gap-4 animate-fade-in max-w-[90%]">
                                        <div 
                                            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm text-white font-bold text-xs"
                                            style={{ backgroundColor: log.color, opacity: isSystem ? 0.6 : 1 }}
                                        >
                                            {isSystem ? <Terminal size={14} /> : log.role?.charAt(0)}
                                        </div>
                                        <div className="flex flex-col gap-1.5 pt-1">
                                            <span className="text-xs font-semibold text-slate-500 tracking-wider flex items-center gap-2">
                                                {log.role}
                                                {isExecuting && i === logs.length - 1 && !isSystem && <span className="flex items-center"><Loader2 size={10} className="animate-spin ml-1" /></span>}
                                            </span>
                                            <div className="text-[15px] text-slate-700 leading-relaxed font-mono bg-slate-50 border border-slate-100 p-3 rounded-xl rounded-tl-sm">
                                                {log.text}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={logsEndRef} className="h-4" />
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 md:p-6 bg-white border-t border-slate-100">
                    <div className="max-w-4xl mx-auto relative">
                        <form onSubmit={handlePromptSubmit} className="relative flex items-center">
                            <textarea 
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                disabled={isExecuting}
                                placeholder="Message the Swarm..."
                                className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-4 pr-14 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-purple-400 focus:ring-4 focus:ring-purple-500/10 resize-none overflow-hidden transition-all text-[15px]"
                                rows={1}
                                style={{ minHeight: '60px', maxHeight: '200px' }}
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
                                className="absolute right-3 bottom-3 p-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
                            >
                                {isExecuting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                            </button>
                        </form>
                        <div className="text-center mt-3 text-xs text-slate-400">
                            Agents may hallucinate. Trace everything in the execution dashboard and check your AWS bill.
                        </div>
                    </div>
                </div>

            </main>

            {/* Agent Feed Sidebar (Desktop/Tablet) */}
            {activeProject && (
                <aside className="w-[350px] xl:w-[450px] border-l border-slate-200 bg-[#09090b] hidden md:flex flex-col">
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
