'use client';

import { useSession, signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Sparkles, ArrowRight, LayoutDashboard, Search, Workflow, Zap, ShieldCheck } from 'lucide-react';

export default function LandingPage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    useEffect(() => {
        if (status === 'authenticated') {
            router.push('/chat');
        }
    }, [status, router]);

    return (
        <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-purple-500/30 flex flex-col relative overflow-hidden">
            
            {/* ── Top Bar ───────────────────────── */}
            <header className="h-20 w-full shrink-0 flex items-center justify-between px-6 md:px-12 sticky top-0 z-50 glass-header">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-md">
                        <Sparkles size={16} className="text-white" />
                    </div>
                    <span className="text-zinc-400 text-sm font-medium tracking-tight">RESEARCH ENGINE v1.0 • POWERED BY GEMINI, CLAUDE & GPT</span>
                </div>
                
                <nav className="hidden md:flex items-center gap-10 text-sm font-semibold text-slate-600">
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
                <section className="relative w-full pt-32 pb-32 px-6 overflow-hidden flex flex-col items-center text-center">
                    {/* Soft Light Background Mesh */}
                    <div className="absolute inset-0 -z-10 overflow-hidden pointer-events-none">
                        <div className="mesh-blob-1"></div>
                        <div className="mesh-blob-2"></div>
                    </div>

                    <div className="badge mb-10 text-purple-600 border-purple-100 bg-white/50 backdrop-blur-sm">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                        SARANG OPEN SOURCE RESEARCH ENGINE
                    </div>

                    <h1 className="text-6xl md:text-[5.5rem] font-extrabold tracking-tight text-slate-900 mb-6 max-w-4xl leading-[1.05]">
                        The Research Lab,<br/>
                        <span className="text-fuchsia-500">in a Box.</span>
                    </h1>
                    
                    <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed mb-12 font-medium">
                        Deconstruct scientific papers into validated, reproducible implementations. Our autonomous agents extract math, logic, and code from PDFs in real-time.
                    </p>

                    <div className="flex flex-col items-center gap-6">
                            <div className="flex gap-4">
                                <span className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div> Gemini 1.5 Flash
                                </span>
                                <span className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-purple-500"></div> Claude 3.5 Sonnet
                                </span>
                                <span className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> GPT-4o
                                </span>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link href="/chat" className="bg-white text-black px-10 py-5 rounded-2xl font-bold hover:bg-slate-200 transition-all flex items-center gap-3 text-lg shadow-[0_0_40px_rgba(255,255,255,0.15)] active:scale-95">
                                    Sign in with Google
                                </Link>
                                <Link href="/chat" className="bg-transparent border border-white/10 text-white px-10 py-5 rounded-2xl font-bold hover:bg-white/5 transition-all text-lg active:scale-95">
                                    Try Demo (Local Account)
                                </Link>
                            </div>
                        </div>
                </section>

                {/* "Single Prompt" Section */}
                <section className="py-24 px-6 md:px-12 max-w-6xl mx-auto w-full">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold mb-4 text-slate-900 tracking-tight">Paper to implementation in minutes</h2>
                        <p className="text-slate-500 text-lg max-w-2xl mx-auto font-medium">A specialized agent swarm built for professional researchers, postdocs, and professors.</p>
                    </div>

                    {/* Dark Concept Card */}
                    <div className="bg-[#0f111a] rounded-[2rem] p-10 md:p-16 shadow-2xl relative overflow-hidden border border-slate-800">
                        {/* Top rainbow border line */}
                        <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-purple-500 via-blue-500 to-teal-400"></div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center relative z-10">
                            {/* Left Side: Text */}
                            <div>
                                <h3 className="text-3xl md:text-4xl font-bold text-white mb-6">Research Agent Swarm</h3>
                                <p className="text-slate-400 text-lg mb-10 leading-relaxed font-medium">
                                    Our multi-agent ecosystem is designed for deep scientific reasoning. We use a hybrid Agent + Swarm method where specialized researchers collaborate to deconstruct papers, extract math, and verify reproducibility.
                                </p>
                                <ul className="space-y-6">
                                    {[
                                        'Scientific Deconstruction', 
                                        'Mathematical Extraction', 
                                        'Peer-Review Validation', 
                                        'Reproducible Sandboxing'
                                    ].map((item, i) => (
                                        <li key={i} className="flex items-center gap-4 text-slate-300">
                                            <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/30">
                                                <Zap size={12} fill="currentColor" />
                                            </div>
                                            <span className="text-base font-medium">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            
                            {/* Right Side: Terminal Graphic */}
                            <div className="relative group">
                                <div className="bg-[#1a1e2e] border border-slate-800 rounded-2xl p-6 shadow-2xl relative">
                                    {/* Mac OS Window Dots */}
                                    <div className="flex gap-2 mb-8">
                                        <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                                        <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
                                        <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
                                    </div>
                                    
                                    {/* Terminal Lines */}
                                    <div className="space-y-4 font-mono text-xs leading-relaxed">
                                        
                                        <div className="flex items-center gap-4">
                                            <div className="w-5 h-5 rounded bg-purple-500 shrink-0"></div>
                                            <div className="bg-slate-800/80 text-slate-300 px-4 py-2.5 rounded-lg w-full max-w-[80%] border border-slate-700/50">
                                                [Lead_Researcher] Deconstructing scientific PDF... <span className="text-purple-400 animate-pulse">|</span>
                                            </div>
                                        </div>
                                        
                                        <div className="flex items-center gap-4 ml-6 border-l-2 border-slate-700/50 pl-4 py-2">
                                            <div className="w-5 h-5 rounded bg-blue-500 shrink-0"></div>
                                            <div className="bg-slate-800/80 text-slate-400 px-4 py-2.5 rounded-lg w-full max-w-[85%] border border-slate-700/50">
                                                [Math_Architect] Extracting mathematical equations...
                                            </div>
                                        </div>
                                        
                                        <div className="flex items-center gap-4 ml-6 border-l-2 border-slate-700/50 pl-4 pb-2">
                                            <div className="w-5 h-5 rounded bg-teal-500 shrink-0"></div>
                                            <div className="bg-slate-800/80 text-slate-400 px-4 py-2.5 rounded-lg w-full max-w-[90%] border border-slate-700/50">
                                                [Implementation_Specialist] Synthesizing validated logic...
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                {/* Floating Blue Button */}
                                <div className="absolute -bottom-5 -right-5 bg-blue-600 text-white px-5 py-3 rounded-xl shadow-2xl font-bold flex items-center gap-3 text-sm animate-float">
                                    <Sparkles size={16} /> Validating reproducibility
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Features Row - 3 Cards */}
                <section className="py-20 px-6 md:px-12 max-w-7xl mx-auto w-full z-10 relative bg-white/50">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { icon: <LayoutDashboard size={20} />, title: "Research Notebook", desc: "Watch the agents deconstruct papers live. See the math extraction and code synthesis happen in real-time.", color: "purple" },
                            { icon: <Workflow size={20} />, title: "Auditable Reasoning", desc: "No black boxes. Every mathematical derivation and research assumption is logged and traceable.", color: "blue" },
                            { icon: <Search size={20} />, title: "Literature Search", desc: "Find insights instantly across your research project with deep semantic search and citation tracking.", color: "teal" }
                        ].map((f, i) => {
                            const colorMap: Record<string, string> = {
                                purple: 'bg-purple-100 text-purple-600',
                                blue: 'bg-blue-100 text-blue-600',
                                teal: 'bg-teal-100 text-teal-600',
                            };
                            const colors = colorMap[f.color as keyof typeof colorMap] || 'bg-slate-100 text-slate-600';
                            
                            return (
                                <div key={i} className="card-light flex flex-col items-start border-slate-200">
                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-6 shadow-sm ${colors}`}>
                                        {f.icon}
                                    </div>
                                    <h3 className="text-xl font-bold text-slate-900 mb-4">{f.title}</h3>
                                    <p className="text-slate-500 leading-relaxed text-[15px] font-medium">{f.desc}</p>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* Security Section */}
                <section id="security" className="py-32 text-center px-6 bg-slate-50 mt-16 border-t border-slate-100">
                    <div className="w-16 h-16 bg-slate-100 border border-slate-200 text-slate-800 rounded-full flex items-center justify-center mx-auto mb-12 shadow-sm">
                        <ShieldCheck size={28} />
                    </div>
                    
                    <h2 className="text-4xl md:text-[3.2rem] font-extrabold text-[#0f111a] mb-12 max-w-4xl mx-auto leading-[1.15] tracking-tight">
                        We prioritize your <span className="underline decoration-purple-500 decoration-4 underline-offset-8">data privacy and</span><br/>
                        <span className="underline decoration-purple-500 decoration-4 underline-offset-8">IP safety</span>, safeguarding your research<br/>
                        and discoveries.
                    </h2>
                    
                    <div className="flex flex-wrap justify-center gap-8 mt-12 text-[15px] font-bold text-slate-500">
                        <span className="flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-500" /> Enterprise-grade auth</span>
                        <span className="flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-500" /> Vulnerability & Threat Tracking</span>
                        <span className="flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-500" /> No training on your private code</span>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-slate-200 bg-white py-12 px-6 md:px-12 mt-auto">
                    <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
                        <div className="flex items-center gap-3 text-slate-900 font-bold text-xl">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                                <Sparkles size={16} className="text-white" />
                            </div>
                            SARANG
                        </div>
                        <div className="text-slate-400 text-sm font-medium">
                            © 2026 SARANG Org. All rights reserved.
                        </div>
                    </div>
                </footer>
            </main>
        </div>
    );
}
