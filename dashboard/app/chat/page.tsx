'use client';

import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useEffect, useState, useRef, useCallback } from 'react';
import { Loader2, Send, Plus, Settings, LogOut, Terminal, Sparkles, MessageSquare, Trash2, User as UserIcon } from 'lucide-react';
import { AGENT_COLORS } from '../../lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const AUTH_DISABLED = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface LogEntry {
    text: string;
    color: string;
    role?: string;
    timestamp?: string;
}

interface ResearchSession {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export default function ChatPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    
    // Debug: Check if session contains image
    useEffect(() => {
        if (session) {
            console.log("SARANG Session Data:", session);
        }
    }, [session]);
    
    const [prompt, setPrompt] = useState('');
    const [isExecuting, setIsExecuting] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [sessions, setSessions] = useState<ResearchSession[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);
    
    const logsEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    const { status: wsStatus, events, sendMessage } = useWebSocket({
        onEvent: (event) => {
            if (event.type === 'message' && event.session_id === currentSessionId) {
                setLogs(prev => [...prev, {
                    role: event.agent,
                    text: event.message,
                    color: AGENT_COLORS[event.agent] || '#a855f7',
                    timestamp: event.timestamp
                }]);
                setIsExecuting(false);
                fetchSessions();
            } else if (event.type === 'status' && event.session_id === currentSessionId) {
                // Show temporary status in logs
                setLogs(prev => {
                    const filtered = prev.filter(l => l.role !== 'Status');
                    return [...filtered, {
                        role: 'Status',
                        text: event.message,
                        color: '#64748b'
                    }];
                });
            }
        }
    });

    const fetchSessions = useCallback(async () => {
        if (!session?.user?.email && !AUTH_DISABLED) return;
        const email = session?.user?.email || 'local@sarang.ai';
        try {
            const resp = await fetch(`${API_BASE}/sessions?user_email=${email}`);
            const data = await resp.json();
            setSessions(data);
        } catch (err) {
            console.error("Failed to fetch sessions", err);
        }
    }, [session?.user?.email]);

    const loadSessionHistory = async (sessionId: string) => {
        setIsLoadingHistory(true);
        setCurrentSessionId(sessionId);
        try {
            const resp = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
            const data = await resp.json();
            const formattedLogs = data.map((m: any) => ({
                role: m.role,
                text: m.content,
                color: m.role === 'User' ? '#f8fafc' : (AGENT_COLORS[m.role] || '#a855f7'),
                timestamp: m.timestamp
            }));
            setLogs(formattedLogs);
        } catch (err) {
            console.error("Failed to load history", err);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const createNewSession = async () => {
        const email = session?.user?.email || 'local@sarang.ai';
        try {
            const resp = await fetch(`${API_BASE}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_email: email, title: "New Research" })
            });
            const newSess = await resp.json();
            setSessions(prev => [newSess, ...prev]);
            setCurrentSessionId(newSess.id);
            setLogs([]);
        } catch (err) {
            console.error("Failed to create session", err);
        }
    };

    const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        const email = session?.user?.email || 'local@sarang.ai';
        try {
            await fetch(`${API_BASE}/sessions/${sessionId}?user_email=${email}`, { method: 'DELETE' });
            setSessions(prev => prev.filter(s => s.id !== sessionId));
            if (currentSessionId === sessionId) {
                setCurrentSessionId(null);
                setLogs([]);
            }
        } catch (err) {
            console.error("Failed to delete session", err);
        }
    };

    useEffect(() => {
        if (status === 'authenticated' || AUTH_DISABLED) {
            fetchSessions();
        }
    }, [status]);

    useEffect(() => {
        scrollToBottom();
    }, [logs, scrollToBottom]);

    useEffect(() => {
        if (!AUTH_DISABLED && status === 'unauthenticated') {
            router.push('/');
        }
    }, [status, router]);

    const handlePromptSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim() || isExecuting) return;

        let activeSessionId = currentSessionId;
        if (!activeSessionId) {
            // Auto-create session on first prompt if none selected
            const email = session?.user?.email || 'local@sarang.ai';
            try {
                const resp = await fetch(`${API_BASE}/sessions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_email: email, title: "New Research" })
                });
                const newSess = await resp.json();
                activeSessionId = newSess.id;
                setSessions(prev => [newSess, ...prev]);
                setCurrentSessionId(activeSessionId);
            } catch (err) {
                console.error("Failed to auto-create session", err);
                return;
            }
        }

        setIsExecuting(true);
        const userPrompt = prompt;
        setPrompt('');
        
        setLogs(prev => [...prev, { text: userPrompt, color: '#f8fafc', role: 'User' }]);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s timeout

        if (wsStatus === 'connected') {
            sendMessage(userPrompt, 'Research_Intelligence', activeSessionId!);
        } else {
            // REST fallback
            try {
                const resp = await fetch(`${API_BASE}/agents/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: userPrompt, 
                        role: 'Research_Intelligence',
                        session_id: activeSessionId
                    }),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                if (!resp.ok) {
                    const errorData = await resp.json();
                    throw new Error(errorData.detail || 'Service error');
                }

                const data = await resp.json();
                setLogs(prev => [...prev, {
                    role: data.agent_role,
                    text: data.content,
                    color: AGENT_COLORS[data.agent_role] || '#a855f7'
                }]);
                setIsExecuting(false);
                fetchSessions(); // Refresh title
            } catch (error: any) {
                console.error("Chat error:", error);
                const errorMsg = error.name === 'AbortError' 
                    ? "Agent took too long to respond. Please try again."
                    : `Error: ${error.message || 'Service unavailable'}`;
                
                setLogs(prev => [...prev, { text: errorMsg, color: '#ef4444', role: 'System' }]);
                setIsExecuting(false);
            }
        }
    };

    if (!AUTH_DISABLED && status === 'loading') {
        return <div className="min-h-screen flex items-center justify-center bg-[#09090b]"><Loader2 className="animate-spin text-purple-600" size={32} /></div>;
    }

    const userName = session?.user?.name || 'Researcher';
    const userEmail = session?.user?.email || 'local@sarang.ai';
    const userImage = session?.user?.image;

    return (
        <div className="flex h-screen bg-[#09090b] text-white font-sans overflow-hidden">
            
            {/* Sidebar */}
            <aside className="w-80 bg-[#0c0c0e] shrink-0 border-r border-white/5 hidden md:flex flex-col">
                <div className="p-6">
                    <button 
                        onClick={createNewSession}
                        className="w-full flex items-center justify-center gap-2 bg-white text-black rounded-2xl py-3.5 transition-all text-sm font-bold hover:bg-slate-200 active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                    >
                        <Plus size={18} /> New Research
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto px-4 space-y-1 mt-2 custom-scrollbar">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3 mb-4 mt-2">Recent Missions</p>
                    {sessions.map((sess) => (
                        <div 
                            key={sess.id}
                            onClick={() => loadSessionHistory(sess.id)}
                            className={`group w-full text-left px-4 py-3.5 rounded-xl text-sm cursor-pointer transition-all flex items-center justify-between ${currentSessionId === sess.id ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`}
                        >
                            <div className="flex items-center gap-3 truncate">
                                <MessageSquare size={16} className={currentSessionId === sess.id ? 'text-purple-400' : 'text-slate-500'} />
                                <span className="truncate font-medium">{sess.title}</span>
                            </div>
                            <button 
                                onClick={(e) => deleteSession(sess.id, e)}
                                className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/20 hover:text-red-400 rounded-lg transition-all"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                </div>

                <div className="p-6 border-t border-white/5 bg-[#09090b]/50">
                    <div className="flex items-center gap-4 mb-6 px-2">
                        {userImage ? (
                            <Image 
                                src={userImage} 
                                alt="User" 
                                width={40}
                                height={40}
                                unoptimized={true}
                                className="w-10 h-10 rounded-xl border border-white/10 object-cover" 
                            />
                        ) : (
                            <div className="w-10 h-10 rounded-xl bg-purple-600 flex items-center justify-center text-white shadow-lg">
                                <UserIcon size={20} />
                            </div>
                        )}
                        <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-bold text-white truncate">{userName}</span>
                            <span className="text-[10px] text-slate-500 truncate font-mono uppercase tracking-tighter">{userEmail}</span>
                        </div>
                    </div>
                    <div className="space-y-1">
                        <Link href="/settings" className="w-full flex items-center gap-3 text-slate-500 hover:text-white px-3 py-2.5 rounded-xl hover:bg-white/5 transition-all text-sm font-medium">
                            <Settings size={18} /> Settings
                        </Link>
                        {!AUTH_DISABLED && (
                            <button onClick={() => signOut()} className="w-full flex items-center gap-3 text-slate-500 hover:text-red-400 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-all text-sm font-medium">
                                <LogOut size={18} /> Sign out
                            </button>
                        )}
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
                        <span className="font-bold">SARANG</span>
                    </div>
                </header>

                {/* Chat History */}
                <div className="flex-1 overflow-y-auto p-4 md:p-12 space-y-8 scroll-smooth custom-scrollbar">
                    {isLoadingHistory ? (
                        <div className="h-full flex items-center justify-center">
                            <Loader2 className="animate-spin text-purple-600" size={32} />
                        </div>
                    ) : logs.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
                            <div className="w-20 h-20 rounded-[2.5rem] bg-white/5 border border-white/10 text-purple-400 flex items-center justify-center mb-8 shadow-2xl animate-float">
                                <Sparkles size={40} />
                            </div>
                            <h2 className="text-4xl font-bold text-white mb-4">
                                Hello, {userName.split(' ')[0]}.<br/>
                                <span className="text-slate-400 text-3xl">Ready for deep research?</span>
                            </h2>
                            <p className="text-slate-500 text-lg mb-12 max-w-md">The agent swarm is active and backed by Gemini 2.5 Flash.</p>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl">
                                {[
                                    "Deconstruct a paper on Quantum Computing",
                                    "Extract math from a Deep Learning PDF",
                                    "Analyze a genomics dataset (FASTQ)",
                                    "Synthesize a validated Python simulation"
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
                        <div className="max-w-4xl mx-auto space-y-8 pb-10">
                            {logs.map((log, i) => {
                                const isUser = log.role === 'User';
                                const isSystem = log.role === 'System';
                                
                                if (isUser) {
                                    return (
                                        <div key={i} className="flex justify-end animate-fade-in group">
                                            <div className="bg-white text-black rounded-3xl rounded-tr-sm px-6 py-4 max-w-[85%] shadow-2xl font-medium">
                                                <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{log.text}</p>
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
                                        <div className="flex flex-col gap-2 pt-1 w-full overflow-hidden">
                                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-3">
                                                {log.role}
                                                {isExecuting && i === logs.length - 1 && <span className="flex items-center"><div className="w-1 h-1 rounded-full bg-purple-500 animate-ping" /></span>}
                                            </span>
                                            <div className="text-[15px] text-slate-200 leading-relaxed bg-white/5 border border-white/5 p-6 rounded-2xl rounded-tl-sm backdrop-blur-md overflow-x-auto prose prose-invert max-w-none">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {log.text}
                                                </ReactMarkdown>
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
                <div className="p-6 md:p-10 bg-gradient-to-t from-[#09090b] via-[#09090b]/90 to-transparent">
                    <div className="max-w-4xl mx-auto relative">
                        <form onSubmit={handlePromptSubmit} className="relative flex items-center">
                            <textarea 
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                disabled={isExecuting}
                                placeholder="Enter research goal..."
                                className="w-full bg-white/5 border border-white/10 rounded-[2rem] py-5 pl-8 pr-16 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-4 focus:ring-purple-500/5 resize-none overflow-hidden transition-all text-base backdrop-blur-2xl shadow-2xl"
                                rows={1}
                                style={{ minHeight: '72px', maxHeight: '200px' }}
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
                                className="absolute right-4 bottom-4 p-3.5 bg-white text-black rounded-2xl hover:bg-slate-200 disabled:opacity-20 disabled:bg-white/10 transition-all active:scale-90 shadow-xl"
                            >
                                {isExecuting ? <Loader2 size={24} className="animate-spin" /> : <Send size={24} />}
                            </button>
                        </form>
                        <div className="text-center mt-5 text-[10px] font-bold text-slate-600 uppercase tracking-[0.2em] opacity-50">
                            SARANG Scientific Intelligence • Powered by Gemini 2.5
                        </div>
                    </div>
                </div>

            </main>
        </div>
    );
}
