'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ArrowLeft, Key, Settings as SettingsIcon, Shield, Cpu, BookOpen, Check, Trash2, Plus, Loader2, Sparkles } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

type Provider = 'bedrock' | 'openai' | 'anthropic' | 'google';

interface LLMKey {
    id: string;
    provider: Provider;
    label: string;
    key_hint: string;
    is_valid: boolean;
    created_at: string;
}

interface AgentPref {
    id?: string;
    agent_role: string;
    provider: Provider;
    model_name: string;
    key_id: string | null;
    model_params: Record<string, unknown>;
    is_default: boolean;
}

const PROVIDER_LABELS: Record<Provider, string> = {
    bedrock: 'Amazon Bedrock (Nova)',
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google Gemini',
};

const AGENT_LABELS: Record<string, string> = {
    CEO: 'CEO — Strategy',
    CTO: 'CTO — Architecture',
    Engineer_Backend: 'Engineer — Backend',
    Engineer_Frontend: 'Engineer — Frontend',
    QA: 'QA — Testing',
    DevOps: 'DevOps — Infrastructure',
    Finance: 'Finance — Budget',
};

const MODEL_OPTIONS: Record<Provider, string[]> = {
    bedrock: ['amazon.nova-pro-v1:0', 'amazon.nova-lite-v1:0', 'amazon.nova-micro-v1:0'],
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    anthropic: ['claude-3-5-sonnet-latest', 'claude-3-haiku-20240307', 'claude-3-opus-latest'],
    google: ['gemini-2.5-pro-exp-03-25', 'gemini-2.0-flash', 'gemini-1.5-pro'],
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusDot({ active }: { active: boolean }) {
    return (
        <span
            className={`inline-block w-2.5 h-2.5 rounded-full mr-2 ${active ? 'bg-emerald-500 ring-4 ring-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-slate-700'}`}
        />
    );
}

function SectionHeader({ icon: Icon, title, subtitle }: { icon: import('lucide-react').LucideIcon; title: string; subtitle: string }) {
    return (
        <div className="mb-8 flex gap-4">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/20 shadow-inner">
                <Icon size={24} />
            </div>
            <div>
                <h2 className="text-xl font-bold text-white tracking-tight">{title}</h2>
                <p className="text-sm text-slate-500 mt-1 leading-relaxed">{subtitle}</p>
            </div>
        </div>
    );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`bg-white/5 border border-white/5 rounded-[2rem] p-8 shadow-2xl backdrop-blur-3xl ${className}`}>
            {children}
        </div>
    );
}

// ── Section 1: LLM Keys ───────────────────────────────────────────────────────

function LLMKeysSection() {
    const [keys, setKeys] = useState<LLMKey[]>([]);
    const [loading, setLoading] = useState(true);
    const [addingFor, setAddingFor] = useState<Provider | null>(null);
    const [form, setForm] = useState({ api_key: '', label: '' });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        try {
            const data = await apiFetch<{ keys: LLMKey[] }>('/v1/settings/keys');
            setKeys(data.keys);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const handleSave = async (provider: Provider) => {
        if (!form.api_key.trim()) { setError('API key is required'); return; }
        setSaving(true); setError('');
        try {
            await apiFetch('/v1/settings/keys', {
                method: 'POST',
                body: JSON.stringify({ provider, api_key: form.api_key, label: form.label || 'default' }),
            });
            setForm({ api_key: '', label: '' });
            setAddingFor(null);
            await load();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Save failed');
        } finally { setSaving(false); }
    };

    const handleDelete = async (id: string) => {
        try {
            await apiFetch(`/v1/settings/keys/${id}`, { method: 'DELETE' });
            await load();
        } catch (e: any) {
            setError(e.message || 'Delete failed');
        }
    };

    const providers: Provider[] = ['bedrock', 'openai', 'anthropic', 'google'];

    return (
        <Card>
            <SectionHeader
                icon={Key}
                title="API Keys"
                subtitle="Configure your LLM provider keys. Keys are encrypted with AES-256 and never fully exposed."
            />
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="animate-spin text-purple-500" />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {providers.map((provider) => {
                        const providerKeys = keys.filter(k => k.provider === provider);
                        const isAdding = addingFor === provider;
                        return (
                            <div key={provider} className={`border rounded-[1.5rem] p-6 transition-all duration-300 ${isAdding ? 'border-purple-500/50 bg-purple-500/5' : 'border-white/5 bg-white/5 hover:bg-white/[0.08]'}`}>
                                <div className="flex items-center justify-between mb-6">
                                    <div className="flex flex-col">
                                        <span className="text-base font-bold text-white">
                                            {PROVIDER_LABELS[provider]}
                                        </span>
                                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mt-1">
                                            {providerKeys.length} active key{providerKeys.length !== 1 ? 's' : ''}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => setAddingFor(isAdding ? null : provider)}
                                        className={`p-2.5 rounded-xl transition-all active:scale-95 ${isAdding ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}
                                    >
                                        {isAdding ? <ArrowLeft size={18} /> : <Plus size={18} />}
                                    </button>
                                </div>

                                {/* Existing keys */}
                                {providerKeys.length > 0 && !isAdding && (
                                    <div className="space-y-3">
                                        {providerKeys.map(key => (
                                            <div key={key.id} className="flex items-center justify-between bg-black/40 border border-white/5 rounded-xl px-4 py-3 shadow-inner group/key">
                                                <div className="flex items-center min-w-0 gap-2">
                                                    <StatusDot active={key.is_valid} />
                                                    <span className="text-xs text-slate-300 font-mono truncate">{key.key_hint}</span>
                                                    <span className="text-[10px] text-slate-500 font-bold ml-1 px-1.5 py-0.5 bg-white/5 rounded-md uppercase tracking-tight">{key.label}</span>
                                                </div>
                                                <button
                                                    onClick={() => handleDelete(key.id)}
                                                    className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover/key:opacity-100"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Add key form */}
                                {isAdding && (
                                    <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
                                        <div className="space-y-2">
                                            <label htmlFor="api_key" className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Secret Key</label>
                                            <input
                                                id="api_key"
                                                type="password"
                                                placeholder="sk-..."
                                                value={form.api_key}
                                                onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                                                className="w-full text-sm bg-black/40 border border-white/10 rounded-xl px-4 py-3 font-mono text-white placeholder-slate-600 focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label htmlFor="key_label" className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Label</label>
                                            <input
                                                id="key_label"
                                                type="text"
                                                placeholder="e.g. Production, Testing"
                                                value={form.label}
                                                onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
                                                className="w-full text-sm bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all"
                                            />
                                        </div>
                                        {error && <p className="text-xs text-red-400 ml-1">{error}</p>}
                                        <button
                                            onClick={() => handleSave(provider)}
                                            disabled={saving}
                                            className="w-full text-sm px-4 py-3.5 rounded-xl bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-all font-bold shadow-lg shadow-purple-500/20 active:scale-[0.98]"
                                        >
                                            {saving ? <Loader2 size={18} className="animate-spin mx-auto" /> : 'Save API Key'}
                                        </button>
                                    </div>
                                )}

                                {!isAdding && providerKeys.length === 0 && (
                                    <div className="py-4 text-center border-2 border-dashed border-white/5 rounded-2xl">
                                        <p className="text-[11px] text-slate-600 font-bold uppercase tracking-widest">No keys configured</p>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </Card>
    );
}

// ── Section 2: Agent Model Preferences ───────────────────────────────────────

function AgentPrefsSection() {
    const [prefs, setPrefs] = useState<AgentPref[]>([]);
    const [keys, setKeys] = useState<LLMKey[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            const [prefsData, keysData] = await Promise.all([
                apiFetch<{ prefs: AgentPref[] }>('/v1/settings/agent-prefs'),
                apiFetch<{ keys: LLMKey[] }>('/v1/settings/keys'),
            ]);
            setPrefs(prefsData.prefs);
            setKeys(keysData.keys);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const handleUpdate = async (pref: AgentPref, field: string, value: string) => {
        const previousPrefs = [...prefs];
        const updated = { ...pref, [field]: value };
        setPrefs(ps => ps.map(p => p.agent_role === pref.agent_role ? updated : p));

        setSaving(pref.agent_role);
        try {
            await apiFetch('/v1/settings/agent-prefs', {
                method: 'POST',
                body: JSON.stringify({
                    agent_role: updated.agent_role,
                    provider: updated.provider,
                    model_name: updated.model_name,
                    key_id: updated.key_id ?? '',
                }),
            });
        } catch (e) {
            setPrefs(previousPrefs);
            console.error('Failed to update agent preference:', e);
        } finally { setSaving(null); }
    };

    const handleReset = async (role: string) => {
        await apiFetch(`/v1/settings/agent-prefs/${role}`, { method: 'DELETE' });
        await load();
    };

    return (
        <Card className="p-0 overflow-hidden border-white/5">
            <div className="p-8 pb-4">
                <SectionHeader
                    icon={Cpu}
                    title="Agent Model Preferences"
                    subtitle="Override platform defaults by assigning specific models to each agent role."
                />
            </div>
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="animate-spin text-purple-500" />
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm border-collapse">
                        <thead>
                            <tr className="bg-white/5 border-y border-white/5">
                                <th className="text-left py-4 px-8 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Agent Role</th>
                                <th className="text-left py-4 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Provider</th>
                                <th className="text-left py-4 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Model</th>
                                <th className="text-left py-4 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">API Key Override</th>
                                <th className="text-right py-4 px-8 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {prefs.map(pref => {
                                const providerKeys = keys.filter(k => k.provider === pref.provider && k.is_valid);
                                const isSaving = saving === pref.agent_role;
                                return (
                                    <tr key={pref.agent_role} className="hover:bg-white/[0.03] transition-colors group">
                                        <td className="py-5 px-8 font-bold text-white text-sm">
                                            {AGENT_LABELS[pref.agent_role] ?? pref.agent_role}
                                        </td>
                                        <td className="py-5 px-4">
                                            <select
                                                value={pref.provider}
                                                onChange={e => handleUpdate(pref, 'provider', e.target.value)}
                                                className="text-xs font-bold bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all cursor-pointer hover:bg-white/10"
                                            >
                                                {Object.entries(PROVIDER_LABELS).map(([v, l]) => (
                                                    <option key={v} value={v} className="bg-slate-900">{l}</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="py-5 px-4">
                                            <select
                                                value={pref.model_name}
                                                onChange={e => handleUpdate(pref, 'model_name', e.target.value)}
                                                className="text-xs font-semibold bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all cursor-pointer hover:bg-white/10"
                                            >
                                                {MODEL_OPTIONS[pref.provider]?.map(m => (
                                                    <option key={m} value={m} className="bg-slate-900">{m}</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="py-5 px-4">
                                            <select
                                                value={pref.key_id ?? ''}
                                                onChange={e => handleUpdate(pref, 'key_id', e.target.value || '')}
                                                className="text-xs bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all cursor-pointer min-w-[160px] hover:bg-white/10"
                                            >
                                                <option value="" className="bg-slate-900 italic">Platform Default</option>
                                                {providerKeys.map(k => (
                                                    <option key={k.id} value={k.id} className="bg-slate-900">{k.label} ({k.key_hint})</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="py-5 px-8 text-right">
                                            <div className="flex items-center justify-end gap-3">
                                                {isSaving ? (
                                                    <Loader2 size={14} className="animate-spin text-purple-500" />
                                                ) : (
                                                    <span className={`text-[10px] px-2.5 py-1 rounded-lg font-bold uppercase tracking-widest ${pref.is_default ? 'bg-white/5 text-slate-500' : 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'}`}>
                                                        {pref.is_default ? 'Default' : 'Custom'}
                                                    </span>
                                                )}
                                                {!pref.is_default && (
                                                    <button
                                                        onClick={() => handleReset(pref.agent_role)}
                                                        className="p-1.5 text-slate-600 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100"
                                                        title="Reset to default"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </Card>
    );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
    return (
        <div className="min-h-screen bg-[#09090b] text-white selection:bg-purple-500/30">
            <div className="max-w-6xl mx-auto px-6 py-12 md:py-24">
                
                {/* Navigation Header */}
                <div className="mb-16 flex items-center justify-between">
                    <Link 
                        href="/chat"
                        className="flex items-center gap-3 text-slate-500 hover:text-white font-bold text-base transition-all group"
                    >
                        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" /> Back to Chat
                    </Link>
                    <div className="flex items-center gap-3 px-4 py-2 bg-emerald-500/10 text-emerald-400 rounded-full text-[11px] font-bold uppercase tracking-widest border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.15)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        Secure Session Active
                    </div>
                </div>

                {/* Page Header */}
                <div className="mb-16">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-bold uppercase tracking-widest mb-6">
                        <SettingsIcon size={16} /> Configuration
                    </div>
                    <h1 className="text-5xl md:text-6xl font-black text-white tracking-tighter mb-6 leading-tight">
                        System <span className="text-gradient-purple">Settings</span>
                    </h1>
                    <p className="text-lg text-slate-400 max-w-3xl leading-relaxed">
                        Fine-tune your autonomous workforce. Manage API orchestration keys and override default agent brain models for specialized tasks.
                    </p>
                </div>

                <div className="space-y-12">
                    <LLMKeysSection />
                    <AgentPrefsSection />

                    {/* Prompting Guides Reference */}
                    <Card>
                        <SectionHeader
                            icon={BookOpen}
                            title="Orchestration Guides"
                            subtitle="Official documentation for high-performance agent behavior across leading providers."
                        />
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-4">
                            {[
                                { provider: 'AWS Bedrock', model: 'Nova Pro', url: 'https://docs.aws.amazon.com/nova/latest/userguide/prompt-engineering.html', icon: <Cpu />, color: 'purple' },
                                { provider: 'OpenAI', model: 'GPT-4o', url: 'https://platform.openai.com/docs/guides/prompt-engineering', icon: <Cpu />, color: 'blue' },
                                { provider: 'Google', model: 'Gemini 2.5', url: 'https://ai.google.dev/gemini-api/docs/prompting-strategies', icon: <Sparkles />, color: 'teal' },
                                { provider: 'Anthropic', model: 'Claude 3.5', url: 'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview', icon: <Shield />, color: 'pink' },
                            ].map(g => (
                                <a
                                    key={g.provider}
                                    href={g.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block p-6 bg-white/5 border border-white/5 rounded-[1.5rem] hover:border-purple-500/50 hover:bg-white/10 transition-all group relative overflow-hidden"
                                >
                                    <div className="flex items-center justify-between mb-6">
                                        <div className="p-2 rounded-xl bg-white/5 text-white bg-opacity-10 group-hover:scale-110 transition-transform">
                                            {g.icon}
                                        </div>
                                        <ArrowLeft size={16} className="rotate-180 text-slate-600 group-hover:text-white group-hover:translate-x-1 transition-all" />
                                    </div>
                                    <p className="text-base font-bold text-white mb-1">{g.provider}</p>
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{g.model}</p>
                                    <div className="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-purple-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                </a>
                            ))}
                        </div>
                    </Card>
                    
                    <div className="text-center py-12 border-t border-white/5">
                        <p className="text-xs text-slate-600 font-bold uppercase tracking-[0.2em] italic">
                            Platform keys are managed by Proximus-Nova admin • Personal overrides take precedence
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
