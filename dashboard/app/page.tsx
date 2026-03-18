'use client';

import { useSession, signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Sparkles, ArrowRight, LayoutDashboard, Search, Workflow, Zap, ShieldCheck, Terminal } from 'lucide-react';

export default function LandingPage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    useEffect(() => {
        if (status === 'authenticated') {
            router.push('/chat');
        }
    }, [status, router]);

    return (
        <div className="min-h-screen bg-[#09090b] text-white font-sans selection:bg-purple-500/30 flex flex-col relative overflow-hidden">
            
            {/* ── Top Bar ───────────────────────── */}
            <header className="h-16 w-full shrink-0 flex items-center justify-between px-6 md:px-12 sticky top-0 z-50 glass-header">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-[0_0_20px_rgba(168,85,247,0.4)]">
                        <Sparkles size={16} className="text-white" />
                    </div>
                    <span className="font-bold text-white tracking-tight text-xl">Proximus-Nova</span>
                </div>
                
                <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-400">
                    <a href="#features" className="hover:text-white transition-colors">Platform</a>
                    <a href="#use-cases" className="hover:text-white transition-colors">Use Cases</a>
                    <a href="#security" className="hover:text-white transition-colors">Security</a>
                </nav>

                <div className="flex gap-4">
                     <button 
                        onClick={() => signIn('google', { callbackUrl: '/chat' })}
                        className="btn-primary border border-white/10 hover:border-purple-500/50"
                     >
                        Get Started <ArrowRight size={16} />
                    </button>
                </div>
            </header>

            {/* ── Main Content ─────────────────────────── */}
            <main className="flex-1 w-full flex flex-col relative z-10">
                
                {/* Hero Section */}
                <section className="relative w-full pt-32 pb-20 px-6 overflow-hidden flex flex-col items-center text-center">
                    {/* Background Mesh (Dark Premium) */}
                    <div className="absolute inset-0 -z-10 overflow-hidden opacity-40">
                        <div className="mesh-blob-1 bg-purple-900/40"></div>
                        <div className="mesh-blob-2 bg-blue-900/40"></div>
                        <div className="mesh-blob-3 bg-teal-900/30"></div>
                    </div>

                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 backdrop-blur-xl border border-white/10 text-purple-400 text-xs font-semibold uppercase tracking-widest mb-8 shadow-2xl">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                        Amazon Nova Hackathon Live
                    </div>

                    <h1 className="text-6xl md:text-8xl font-extrabold tracking-tight text-white mb-8 max-w-5xl leading-[1.1]">
                        The AI Company,<br/>
                        <span className="text-gradient-purple">in a Box.</span>
                    </h1>
                    
                    <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-12">
                        Describe your product idea. Our autonomous agents will architect, build, test, and deploy it instantly.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center gap-4">
                        <button 
                            onClick={() => signIn('google', { callbackUrl: '/chat' })}
                            className="btn-primary text-base px-10 py-4 w-full sm:w-auto bg-white text-black hover:bg-slate-200"
                        >
                            Sign in with Google
                        </button>
                        <button 
                            onClick={() => {
                                if (process.env.NODE_ENV !== 'production') {
                                    signIn('credentials', { username: 'admin', password: 'admin', callbackUrl: '/chat' });
                                }
                            }}
                            className="bg-white/5 border border-white/10 backdrop-blur-md px-10 py-4 rounded-full text-base font-semibold hover:bg-white/10 transition-all w-full sm:w-auto"
                        >
                            Try Demo (Local)
                        </button>
                    </div>
                </section>

                {/* Feature Previews */}
                <section id="demo" className="py-24 px-6 md:px-12 max-w-7xl mx-auto w-full">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold mb-4 text-white">Create software with a single prompt</h2>
                        <p className="text-slate-400 text-lg max-w-2xl mx-auto">Build powerful automated sequences that connect your favorite tech stack.</p>
                    </div>

                    <div className="bg-slate-900/40 backdrop-blur-2xl rounded-[2.5rem] p-8 md:p-16 shadow-[0_0_80px_rgba(0,0,0,0.5)] relative overflow-hidden border border-white/5">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-teal-400 opacity-50"></div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center relative z-10">
                            <div>
                                <h3 className="text-4xl font-bold text-white mb-8">Micro-Agent Swarm</h3>
                                <p className="text-slate-400 text-lg mb-10 leading-relaxed">
                                    Our proprietary Swarm divides and conquers. The CEO plans, the CTO architects, and engineering agents build front-end and back-end concurrently.
                                </p>
                                <ul className="space-y-6">
                                    {['Requirements Planning', 'Parallel Code Generation', 'Automated QA & Security', 'Native Cloud Deployment'].map((item, i) => (
                                        <li key={i} className="flex items-center gap-4 text-slate-300">
                                            <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/30">
                                                <Zap size={16} />
                                            </div>
                                            <span className="text-lg font-medium">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="relative group">
                                <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-1000"></div>
                                <div className="bg-black/60 border border-white/10 rounded-2xl p-6 shadow-2xl backdrop-blur-3xl relative">
                                    <div className="flex gap-2 mb-8 border-b border-white/5 pb-4">
                                        <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
                                        <div className="w-3 h-3 rounded-full bg-amber-500/50"></div>
                                        <div className="w-3 h-3 rounded-full bg-green-500/50"></div>
                                    </div>
                                    <div className="space-y-6 font-mono text-sm leading-relaxed">
                                        <div className="flex gap-4">
                                            <div className="w-6 h-6 rounded bg-purple-600/80 shrink-0 flex items-center justify-center text-[10px]">P</div>
                                            <div className="text-slate-300">Analyzing business requirements... <span className="text-purple-400 animate-pulse">|</span></div>
                                        </div>
                                        <div className="flex gap-4 ml-8 border-l border-white/10 pl-4">
                                            <div className="w-6 h-6 rounded bg-blue-600/80 shrink-0 flex items-center justify-center text-[10px]">A</div>
                                            <div className="text-slate-400">Designing database schema and APIs.</div>
                                        </div>
                                        <div className="flex gap-4 ml-8 border-l border-white/10 pl-4">
                                            <div className="w-6 h-6 rounded bg-teal-600/80 shrink-0 flex items-center justify-center text-[10px]">E</div>
                                            <div className="text-slate-400">Writing Next.js frontend components...</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="absolute -bottom-6 -right-6 bg-blue-600 text-white px-5 py-3 rounded-2xl shadow-2xl font-bold flex items-center gap-3 animate-float">
                                    <Sparkles size={18} /> Deploying to Cloudflare
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Features Grid */}
                            {[
                                { icon: <LayoutDashboard size={24} />, title: "Real-time Dashboard", desc: "Watch the agents work live. See code generation, testing, and deployment happen in real-time.", color: "purple" },
                                { icon: <Workflow size={24} />, title: "Full Visibility", desc: "No black boxes. Every architectural decision and code commit is logged and traceable.", color: "blue" },
                                { icon: <Search size={24} />, title: "Semantic Search", desc: "Find information instantly across all generated codebase artifacts with powerful search.", color: "teal" }
                            ].map((f, i) => {
                                const colorMap: Record<string, string> = {
                                    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
                                    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
                                    teal: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
                                };
                                const colors = colorMap[f.color as keyof typeof colorMap] || 'bg-slate-500/10 text-slate-400 border-slate-500/20';
                                return (
                                    <div key={i} className="bg-white/5 border border-white/10 rounded-[2rem] p-8 hover:bg-white/[0.08] transition-all hover:-translate-y-2 duration-300">
                                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-6 border shadow-inner ${colors}`}>
                                            {f.icon}
                                        </div>
                                        <h3 className="text-2xl font-bold text-white mb-4">{f.title}</h3>
                                        <p className="text-slate-400 leading-relaxed text-lg">{f.desc}</p>
                                    </div>
                                );
                            })}

                {/* Security Section (Slashy Inspired) */}
                <section id="security" className="py-32 text-center px-6 bg-gradient-to-b from-transparent to-purple-900/10">
                    <div className="w-20 h-20 bg-white/5 border border-white/10 text-white rounded-3xl flex items-center justify-center mx-auto mb-10 shadow-2xl">
                        <ShieldCheck size={36} />
                    </div>
                    <h2 className="text-4xl md:text-6xl font-bold text-white mb-8 max-w-4xl mx-auto leading-tight">
                        Built for enterprise <span className="text-gradient-purple">security and privacy</span>.
                    </h2>
                    <div className="flex flex-wrap justify-center gap-10 mt-16 text-lg font-medium text-slate-400">
                        <span className="flex items-center gap-3"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"/> Enterprise Auth</span>
                        <span className="flex items-center gap-3"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"/> Threat Tracking</span>
                        <span className="flex items-center gap-3"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"/> Private Codebase</span>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-white/5 bg-black py-16 px-6 md:px-12 mt-auto">
                    <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
                        <div className="flex items-center gap-3 text-white font-bold text-2xl">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                                <Sparkles size={20} />
                            </div>
                            Proximus-Nova
                        </div>
                        <div className="text-slate-500 text-base">
                            © 2026 Proximus Org. All rights reserved.
                        </div>
                    </div>
                </footer>
            </main>
        </div>
    );
}
