'use client';

import { useSession, signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Sparkles, ArrowRight, LayoutDashboard, Search, Workflow, Zap, ShieldCheck, Terminal } from 'lucide-react';
import Image from 'next/image';

export default function LandingPage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    useEffect(() => {
        if (status === 'authenticated') {
            router.push('/chat');
        }
    }, [status, router]);

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-purple-500/30 flex flex-col relative overflow-hidden">
            
            {/* ── Top Bar ───────────────────────── */}
            <header className="h-16 w-full shrink-0 flex items-center justify-between px-6 md:px-12 sticky top-0 z-50 glass-header">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-md">
                        <Sparkles size={16} className="text-white" />
                    </div>
                    <span className="font-bold text-slate-800 tracking-tight text-xl">Proximus-Nova</span>
                </div>
                
                <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
                    <a href="#features" className="hover:text-slate-900 transition-colors">Platform</a>
                    <a href="#use-cases" className="hover:text-slate-900 transition-colors">Use Cases</a>
                    <a href="#security" className="hover:text-slate-900 transition-colors">Security</a>
                </nav>

                <div className="flex gap-4">
                     <button 
                        onClick={() => signIn('google', { callbackUrl: '/chat' })}
                        className="btn-primary"
                     >
                        Get Started <ArrowRight size={16} />
                    </button>
                </div>
            </header>

            {/* ── Main Content ─────────────────────────── */}
            <main className="flex-1 w-full flex flex-col relative z-10">
                
                {/* Hero Section */}
                <section className="relative w-full pt-32 pb-20 px-6 overflow-hidden flex flex-col items-center text-center">
                    {/* Background Mesh */}
                    <div className="absolute inset-0 -z-10 overflow-hidden">
                        <div className="mesh-blob-1"></div>
                        <div className="mesh-blob-2"></div>
                        <div className="mesh-blob-3"></div>
                    </div>

                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/50 backdrop-blur-sm border border-slate-200/50 text-purple-700 text-xs font-semibold uppercase tracking-widest mb-8 shadow-sm">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                        Amazon Nova Hackathon Live
                    </div>

                    <h1 className="text-6xl md:text-8xl font-extrabold tracking-tight text-slate-900 mb-8 max-w-5xl leading-[1.1]">
                        The AI Company,<br/>
                        <span className="text-gradient-purple">in a Box.</span>
                    </h1>
                    
                    <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed mb-12">
                        Describe your product idea in natural language. Our autonomous agents will architect, build, test, and deploy it instantly.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center gap-4">
                        <button 
                            onClick={() => signIn('google', { callbackUrl: '/chat' })}
                            className="btn-primary text-base px-8 py-4 w-full sm:w-auto"
                        >
                            Sign in with Google
                        </button>
                        <button 
                            onClick={() => signIn('credentials', { username: 'admin', password: 'admin', callbackUrl: '/chat' })}
                            className="btn-secondary text-base px-8 py-4 w-full sm:w-auto"
                        >
                            Try Demo (Local Account)
                        </button>
                    </div>
                </section>

                {/* Feature Previews */}
                <section id="demo" className="py-24 px-6 md:px-12 max-w-7xl mx-auto w-full">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900">Create software with a single prompt</h2>
                        <p className="text-slate-600 text-lg max-w-2xl mx-auto">Build powerful automated sequences that connect your favorite tech stack.</p>
                    </div>

                    <div className="bg-slate-900 rounded-[2rem] p-8 md:p-12 shadow-2xl relative overflow-hidden border border-slate-800">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-teal-400"></div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center relative z-10">
                            <div>
                                <h3 className="text-3xl font-bold text-white mb-6">Micro-Agent Swarm</h3>
                                <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                                    Our proprietary Multi-Agent Swarm divides and conquers. The CEO agent plans the strategy, the CTO architects the system, and engineering agents write front-end and back-end code concurrently.
                                </p>
                                <ul className="space-y-4">
                                    {['Requirements Planning', 'Parallel Code Generation', 'Automated QA & Security', 'Native Cloud Deployment'].map((item, i) => (
                                        <li key={i} className="flex items-center gap-3 text-slate-300">
                                            <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                                                <Zap size={14} />
                                            </div>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="relative">
                                {/* Abstract wireframe representation of the chat UI */}
                                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 shadow-2xl backdrop-blur-xl">
                                    <div className="flex gap-2 mb-6 border-b border-slate-700 pb-4">
                                        <div className="w-3 h-3 rounded-full bg-red-400/80"></div>
                                        <div className="w-3 h-3 rounded-full bg-amber-400/80"></div>
                                        <div className="w-3 h-3 rounded-full bg-green-400/80"></div>
                                    </div>
                                    <div className="space-y-4 font-mono text-sm">
                                        <div className="flex gap-3">
                                            <div className="w-6 h-6 rounded bg-purple-500 shrink-0"></div>
                                            <div className="bg-slate-700 text-slate-300 p-2 rounded-r-lg rounded-bl-lg w-3/4">Analyzing business requirements...</div>
                                        </div>
                                        <div className="flex gap-3">
                                            <div className="w-6 h-6 rounded bg-blue-500 shrink-0"></div>
                                            <div className="bg-slate-700 text-slate-300 p-2 rounded-r-lg rounded-bl-lg w-5/6">Designing database schema and APIs.</div>
                                        </div>
                                        <div className="flex gap-3">
                                            <div className="w-6 h-6 rounded bg-teal-500 shrink-0"></div>
                                            <div className="bg-slate-700 text-slate-300 p-2 rounded-r-lg rounded-bl-lg">Writing Next.js frontend components...</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="absolute -bottom-6 -right-6 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-xl font-medium flex items-center gap-2">
                                    <Sparkles size={16} /> Deploying to AWS
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Features Grid */}
                <section id="features" className="py-24 bg-white border-y border-slate-100">
                    <div className="max-w-7xl mx-auto px-6 md:px-12">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            <div className="card-light flex flex-col items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center">
                                    <LayoutDashboard size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900">Real-time Dashboard</h3>
                                <p className="text-slate-600 leading-relaxed">Watch the agents work live. See code generation, testing, and deployment happen in real-time on your dashboard.</p>
                            </div>
                            <div className="card-light flex flex-col items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                                    <Workflow size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900">Full Visibility</h3>
                                <p className="text-slate-600 leading-relaxed">No black boxes. Every architectural decision, cost estimate, and code commit is logged and traceable.</p>
                            </div>
                            <div className="card-light flex flex-col items-start gap-4">
                                <div className="w-12 h-12 rounded-xl bg-teal-100 text-teal-600 flex items-center justify-center">
                                    <Search size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900">Search Across Apps</h3>
                                <p className="text-slate-600 leading-relaxed">Find information instantly across all generated codebase artifacts with powerful semantic search.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Security Section (Slashy Inspired) */}
                <section id="security" className="py-32 text-center px-6">
                    <div className="w-16 h-16 bg-slate-100 text-slate-800 rounded-full flex items-center justify-center mx-auto mb-8">
                        <ShieldCheck size={32} />
                    </div>
                    <h2 className="text-3xl md:text-5xl font-bold text-slate-900 mb-6 max-w-3xl mx-auto">
                        We prioritize your <span className="underline decoration-purple-500 decoration-4 underline-offset-4">security and privacy</span>,
                        safeguarding your app and databases.
                    </h2>
                    <div className="flex flex-wrap justify-center gap-6 mt-12 text-sm font-semibold text-slate-600">
                        <span className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-500" /> Enterprise-grade auth</span>
                        <span className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-500" /> Vulnerability & Threat Tracking</span>
                        <span className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-500" /> No training on your private code</span>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-slate-200 bg-white py-12 px-6 md:px-12 mt-auto">
                    <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
                        <div className="flex items-center gap-2 text-slate-900 font-bold">
                            <Sparkles size={18} className="text-purple-600" /> Proximus-Nova
                        </div>
                        <div className="text-slate-500 text-sm">
                            © 2026 AI Org. All rights reserved.
                        </div>
                    </div>
                </footer>
            </main>
        </div>
    );
}
