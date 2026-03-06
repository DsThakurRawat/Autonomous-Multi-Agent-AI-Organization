'use client'

import { signIn, useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Rocket, ShieldCheck, Database, Search, Workflow, Clock, Layers } from 'lucide-react'
import { useEffect } from 'react'

export default function LandingPage() {
    const { data: session, status } = useSession()
    const router = useRouter()

    const authDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === 'true'

    useEffect(() => {
        // Local mode: skip login, go straight to dashboard
        if (authDisabled) {
            router.push('/dashboard')
            return
        }
        // SaaS mode: redirect logged-in users to dashboard
        if (status === 'authenticated') {
            router.push('/dashboard')
        }
    }, [status, router, authDisabled])

    const handleLogin = () => {
        signIn('google', { callbackUrl: '/dashboard' })
    }


    // Google Icon SVG 
    const GoogleIcon = () => (
        <svg viewBox="0 0 24 24" y="1024" xmlns="http://www.w3.org/2000/svg" className="w-4 h-4">
            <path fill="#4285F4" d="M23.7449 12.27C23.7449 11.48 23.6849 10.73 23.5549 10H12.2549V14.51H18.7249C18.4349 15.99 17.5849 17.24 16.3249 18.09V21.09H20.1849C22.4449 19.01 23.7449 15.92 23.7449 12.27Z" />
            <path fill="#34A853" d="M12.255 24C15.495 24 18.205 22.92 20.185 21.09L16.325 18.09C15.245 18.81 13.875 19.25 12.255 19.25C9.12498 19.25 6.47498 17.14 5.52498 14.29H1.54498V17.38C3.51498 21.3 7.56498 24 12.255 24Z" />
            <path fill="#FBBC05" d="M5.52496 14.29C5.27496 13.57 5.14496 12.8 5.14496 12C5.14496 11.2 5.27496 10.43 5.52496 9.71V6.62H1.54496C0.72496 8.24 0.25496 10.06 0.25496 12C0.25496 13.94 0.72496 15.76 1.54496 17.38L5.52496 14.29Z" />
            <path fill="#EA4335" d="M12.255 4.75C14.025 4.75 15.605 5.36 16.855 6.55L20.275 3.13C18.205 1.19 15.495 0 12.255 0C7.56498 0 3.51498 2.7 1.54498 6.62L5.52498 9.71C6.47498 6.86 9.12498 4.75 12.255 4.75Z" />
        </svg>
    )

    return (
        <div className="min-h-screen bg-white text-gray-900 font-sans selection:bg-teal-200">
            {/* ── Navbar ────────────────────────────────────────── */}
            <nav className="fixed w-full z-50 bg-white/80 backdrop-blur-md border-b border-gray-100 transition-all duration-300">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-r from-teal-400 to-indigo-500 rounded-lg flex items-center justify-center">
                            <Layers className="text-white w-4 h-4" />
                        </div>
                        <span className="font-bold text-xl tracking-tight text-gray-900">AI Org</span>
                    </div>

                    <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
                        <a href="#" className="hover:text-gray-900 transition-colors">Pricing</a>
                        <a href="#" className="hover:text-gray-900 transition-colors">Use Cases</a>
                        <a href="#" className="hover:text-gray-900 transition-colors">Enterprise</a>
                    </div>

                    <div className="flex items-center gap-4">
                        <button className="hidden sm:block px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200">
                            Book a demo
                        </button>
                        <button
                            onClick={handleLogin}
                            className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-all shadow-md active:scale-95"
                        >
                            <GoogleIcon />
                            Start now
                        </button>
                    </div>
                </div>
            </nav>

            {/* ── Hero Section ──────────────────────────────────── */}
            <main>
                <section className="relative pt-32 pb-20 overflow-hidden">
                    {/* Background Gradient similar to slashy.ai */}
                    <div className="absolute inset-x-0 -top-20 -z-10 h-[800px] bg-gradient-to-b from-teal-100/50 via-indigo-50/50 to-white transform-gpu rounded-b-[100px] overflow-hidden opacity-80" />

                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 shadow-sm mb-8 animate-fade-in">
                            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Backed by</span>
                            <div className="flex items-center gap-1.5">
                                <div className="w-4 h-4 bg-[#ff6600] text-white flex items-center justify-center text-[10px] font-bold rounded-sm">Y</div>
                                <span className="text-xs font-semibold text-gray-800">Combinator</span>
                            </div>
                        </div>

                        <h1 className="text-6xl md:text-8xl font-black tracking-tight text-gray-900 mb-6 font-sans">
                            The AI for <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-500 to-indigo-600">Work</span>
                        </h1>
                        <p className="max-w-2xl mx-auto text-lg md:text-xl text-gray-600 mb-10 leading-relaxed font-medium">
                            The Autonomous AI Organization connects to all your tools to complete entire cross-functional software tasks instantly.
                        </p>

                        <button
                            onClick={handleLogin}
                            className="bg-white hover:bg-gray-50 text-gray-900 border border-gray-200 px-8 py-4 rounded-xl text-base font-bold transition-all shadow-xl hover:shadow-2xl flex items-center gap-3 mx-auto active:scale-95 mb-12"
                        >
                            <GoogleIcon />
                            Start now
                        </button>

                        <div className="flex flex-wrap justify-center gap-2.5 max-w-3xl mx-auto">
                            {['Meetings', 'Workflow', 'Search', 'Gmail', 'Notion', 'Leads'].map((pill, i) => (
                                <span key={pill} className={`px-4 py-2 rounded-full text-sm font-semibold border ${i === 0 ? 'bg-gray-900 text-white border-gray-900 shadow-md' : 'bg-white/60 text-gray-700 border-gray-200 hover:bg-white'} backdrop-blur-sm cursor-pointer transition-colors duration-200`}>
                                    {pill}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Window Mockup */}
                    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 mt-16 relative">
                        <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent z-20 h-full pointer-events-none" />
                        <div className="bg-white rounded-2xl md:rounded-[32px] shadow-2xl border border-gray-100 overflow-hidden transform-gpu flex flex-col items-center">
                            <div className="w-full h-12 bg-gray-50/80 border-b border-gray-100 flex items-center px-6 gap-2 shrink-0">
                                <div className="w-3 h-3 rounded-full bg-red-400" />
                                <div className="w-3 h-3 rounded-full bg-amber-400" />
                                <div className="w-3 h-3 rounded-full bg-emerald-400" />
                            </div>
                            <div className="w-full h-[500px] p-8 text-left relative flex overflow-hidden">
                                <div className="w-1/3 border-r border-gray-100 pr-8 h-full">
                                    <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-6">Thinking Process</div>
                                    <div className="space-y-4">
                                        <div className="h-4 bg-gray-100 rounded w-3/4 animate-pulse" />
                                        <div className="h-4 bg-gray-100 rounded w-full animate-pulse" />
                                        <div className="h-4 bg-gray-100 rounded w-5/6 animate-pulse" />
                                        <div className="h-4 bg-gray-100 rounded w-1/2 animate-pulse mt-8" />
                                    </div>
                                </div>
                                <div className="w-2/3 pl-8 flex flex-col pt-4">
                                    <h3 className="text-2xl font-bold text-gray-900 mb-4">API Route Generation</h3>
                                    <p className="text-gray-600 leading-relaxed mb-6">
                                        Perfect! I&apos;ve analyzed your database schema and generated all required CRUD endpoints for the FastAPI backend layer. All endpoints have been successfully mocked and tested against our isolated Docker sandbox.
                                    </p>
                                    <div className="bg-gray-50 p-6 rounded-xl border border-gray-100 w-full flex-1">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className="w-8 h-8 rounded bg-teal-100 text-teal-600 flex items-center justify-center font-bold font-mono text-xs">GET</div>
                                            <span className="font-mono text-sm text-gray-700">/api/v1/metrics/users</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Feature: Workflows ──────────────────────────────── */}
                <section className="py-32 bg-white relative">
                    <div className="max-w-4xl mx-auto px-4 text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-extrabold text-gray-900 mb-6 tracking-tight">Create automated workflows</h2>
                        <p className="text-xl text-gray-600 font-medium">Build powerful automation sequences that connect your favorite tools and streamline your daily developer tasks.</p>
                    </div>

                    <div className="max-w-5xl mx-auto px-4">
                        <div className="rounded-[40px] p-8 md:p-12 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-2xl overflow-hidden relative group">
                            <div className="absolute inset-0 bg-grid-white/[0.05] bg-[length:32px_32px]" />
                            <div className="bg-white/95 backdrop-blur-md rounded-2xl shadow-xl overflow-hidden border border-white/20 transform-gpu transition-transform duration-500 group-hover:scale-[1.02]">
                                <div className="p-6 md:p-8">
                                    <div className="flex items-center gap-3 mb-6">
                                        <Workflow className="w-6 h-6 text-indigo-500" />
                                        <h3 className="text-xl font-bold text-gray-900">Daily Scrum Aggregator</h3>
                                        <span className="ml-auto text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">Live</span>
                                    </div>
                                    <div className="space-y-4">
                                        <div className="flex items-start gap-4 p-4 border border-gray-100 rounded-xl bg-gray-50/50">
                                            <div className="w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center border border-gray-200 flex-shrink-0">1</div>
                                            <div>
                                                <h4 className="font-semibold text-gray-900">Triggered at 9:00 AM</h4>
                                                <p className="text-sm text-gray-500">Scheduled by DevOps cron job</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-4 p-4 border border-gray-100 rounded-xl bg-white shadow-sm">
                                            <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100 font-bold flex-shrink-0 text-xs">JS</div>
                                            <div>
                                                <h4 className="font-semibold text-gray-900">Execute Javascript Agent</h4>
                                                <p className="text-sm text-gray-500">Collect pull request statuses and format markdown summary.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Feature: Search ──────────────────────────────────── */}
                <section className="py-32 bg-white relative">
                    <div className="max-w-4xl mx-auto px-4 text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-extrabold text-gray-900 mb-6 tracking-tight">Search across repositories</h2>
                        <p className="text-xl text-gray-600 font-medium">Find code, architecture documents, and deployment logic instantly across all your agent workspaces.</p>
                    </div>

                    <div className="max-w-5xl mx-auto px-4">
                        <div className="rounded-[40px] p-8 md:p-12 bg-gradient-to-tr from-teal-400 to-emerald-500 shadow-2xl relative">
                            <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-white/20">
                                <div className="border-b border-gray-100 p-4 bg-gray-50/50">
                                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 px-4 py-3 flex items-center gap-3">
                                        <Search className="w-5 h-5 text-gray-400" />
                                        <input type="text" placeholder="Find database schema for..." className="bg-transparent border-none outline-none w-full text-gray-700 font-medium placeholder-gray-400" readOnly />
                                    </div>
                                </div>
                                <div className="p-8">
                                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Omni-Agent Knowledge graph</h4>
                                    <div className="space-y-6">
                                        <div className="flex gap-4">
                                            <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center border border-indigo-100 shrink-0">
                                                <Database className="w-5 h-5 text-indigo-500" />
                                            </div>
                                            <div>
                                                <h5 className="font-bold text-gray-900 text-lg">Postgres Users Schema</h5>
                                                <p className="text-gray-500 text-sm mt-1">Found in Project ID: e8e2-9f12 — Generated by Backend Engineer.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Security Section ─────────────────────────────────── */}
                <section className="py-40 bg-white border-t border-gray-100">
                    <div className="max-w-5xl mx-auto px-4 text-center">
                        <h2 className="text-4xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-[1.1] mb-16">
                            We prioritize your <span className="relative inline-block"><span className="relative z-10">security and privacy</span><div className="absolute bottom-1.5 left-0 w-full h-3 bg-teal-200/60 -z-10" /></span>, safeguarding your app connections and upholding strict data protection standards.
                        </h2>

                        <div className="flex flex-wrap justify-center gap-8 md:gap-16 text-sm font-semibold text-gray-600">
                            <div className="flex items-center gap-2">
                                <Database className="w-5 h-5 text-gray-400" />
                                Data Retention Policies
                            </div>
                            <div className="flex items-center gap-2">
                                <ShieldCheck className="w-5 h-5 text-gray-400" />
                                Vulnerability & Threat Tracking
                            </div>
                            <div className="flex items-center gap-2">
                                <Rocket className="w-5 h-5 text-gray-400" />
                                Sandboxed Execution
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* ── Footer ────────────────────────────────────────────── */}
            <footer className="bg-white border-t border-gray-100 pt-20 pb-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 mb-16">
                        <div className="col-span-2 lg:col-span-2">
                            <div className="flex items-center gap-2 mb-6">
                                <div className="w-6 h-6 bg-gray-900 rounded-md flex items-center justify-center">
                                    <Layers className="text-white w-3 h-3" />
                                </div>
                                <span className="font-bold text-lg tracking-tight text-gray-900">AI Org</span>
                            </div>
                            <p className="text-gray-500 text-sm leading-relaxed max-w-xs font-medium">
                                AI Organization is the OS built to make you extraordinarily productive. Connect your tools, orchestrate agents, and transform how software is built.
                            </p>
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-900 mb-6">Product</h4>
                            <ul className="space-y-4 text-sm text-gray-500 font-medium">
                                <li><a href="#" className="hover:text-gray-900">Use Cases</a></li>
                                <li><a href="#" className="hover:text-gray-900">Pricing</a></li>
                                <li><a href="#" className="hover:text-gray-900">Enterprise</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-900 mb-6">Resources</h4>
                            <ul className="space-y-4 text-sm text-gray-500 font-medium">
                                <li><a href="#" className="hover:text-gray-900">Documentation</a></li>
                                <li><a href="#" className="hover:text-gray-900">API Reference</a></li>
                                <li><a href="#" className="hover:text-gray-900">Security</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-900 mb-6">Legal</h4>
                            <ul className="space-y-4 text-sm text-gray-500 font-medium">
                                <li><a href="#" className="hover:text-gray-900">Privacy Policy</a></li>
                                <li><a href="#" className="hover:text-gray-900">Terms of Service</a></li>
                            </ul>
                        </div>
                    </div>
                    <div className="border-t border-gray-100 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
                        <p className="text-xs text-gray-400 font-medium">
                            © 2026 AI Organization. All rights reserved. Open Source via MIT License.
                        </p>
                        <div className="flex items-center gap-4 text-gray-400">
                            {/* Social Icons Placeholder */}
                            <a href="#" className="hover:text-gray-900 transition-colors">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z" /></svg>
                            </a>
                            <a href="#" className="hover:text-gray-900 transition-colors">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" /></svg>
                            </a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    )
}
