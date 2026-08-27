import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useToast } from '../../contexts/ToastContext';
import { fetchApi } from '../../utils/api';
import {
    Activity, Zap, MessageSquare, Clock, DollarSign,
    Search, RefreshCw, ChevronRight, ChevronDown, Hash,
    GitBranch, Database, Cpu, Globe, Workflow, ArrowLeft,
    Layers, AlertTriangle, FileCode, Tag, ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useProject } from '../../contexts/ProjectContext';
import { EmptyState } from '../../components/ui/EmptyState';
import { Button } from '../../components/ui/Button';

// ─── Constants ──────────────────────────────────────────────────────
// All class names are STATIC strings — required for Tailwind purging.
const EVENT_TYPE_CONFIG = {
    llm:            { icon: MessageSquare, label: 'LLM',         iconBg: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500',   pill: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',   cardBg: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500' },
    chat_model:     { icon: MessageSquare, label: 'Chat Model',  iconBg: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500',   pill: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',   cardBg: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500' },
    tool:           { icon: Zap,           label: 'Tool',        iconBg: 'bg-amber-50 dark:bg-amber-900/20 text-amber-500',      pill: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',      cardBg: 'bg-amber-50 dark:bg-amber-900/20 text-amber-500' },
    chain:          { icon: GitBranch,     label: 'Chain',       iconBg: 'bg-violet-50 dark:bg-violet-900/20 text-violet-500',   pill: 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400',   cardBg: 'bg-violet-50 dark:bg-violet-900/20 text-violet-500' },
    agent:          { icon: Cpu,           label: 'Agent',       iconBg: 'bg-rose-50 dark:bg-rose-900/20 text-rose-500',         pill: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400',           cardBg: 'bg-rose-50 dark:bg-rose-900/20 text-rose-500' },
    agent_action:   { icon: Cpu,           label: 'Action',      iconBg: 'bg-rose-50 dark:bg-rose-900/20 text-rose-500',         pill: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400',           cardBg: 'bg-rose-50 dark:bg-rose-900/20 text-rose-500' },
    embedding:      { icon: Database,      label: 'Embedding',   iconBg: 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-500',        pill: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400',           cardBg: 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-500' },
    retriever:      { icon: Search,        label: 'Retriever',   iconBg: 'bg-teal-50 dark:bg-teal-900/20 text-teal-500',        pill: 'bg-teal-100 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400',           cardBg: 'bg-teal-50 dark:bg-teal-900/20 text-teal-500' },
    graph_node:     { icon: Workflow,      label: 'Graph Node',  iconBg: 'bg-purple-50 dark:bg-purple-900/20 text-purple-500',  pill: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',   cardBg: 'bg-purple-50 dark:bg-purple-900/20 text-purple-500' },
    session:        { icon: Globe,         label: 'Session',     iconBg: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500', pill: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400', cardBg: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500' },
    genai_session:  { icon: Globe,         label: 'Session',     iconBg: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500', pill: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400', cardBg: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500' },
};

const STATUS_CONFIG = {
    success:   { dot: 'bg-emerald-500', badge: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' },
    completed: { dot: 'bg-emerald-500', badge: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' },
    error:     { dot: 'bg-rose-500',    badge: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400' },
    errored:   { dot: 'bg-rose-500',    badge: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400' },
    failed:    { dot: 'bg-rose-500',    badge: 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400' },
    running:   { dot: 'bg-amber-500 animate-pulse', badge: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' },
    active:    { dot: 'bg-amber-500 animate-pulse', badge: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' },
};

const DEFAULT_EVENT = { icon: Activity, label: 'Event', iconBg: 'bg-slate-50 dark:bg-slate-800/60 text-slate-500', pill: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400', cardBg: 'bg-slate-50 dark:bg-slate-800/60 text-slate-500' };
const DEFAULT_STATUS = { dot: 'bg-slate-400', badge: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400' };

// ─── Helpers ────────────────────────────────────────────────────────
function formatDuration(d) {
    if (d == null) return '—';
    const ms = d * 1000;
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
}

function formatCost(c) {
    if (!c) return null;
    return c < 0.01 ? `$${c.toFixed(6)}` : `$${c.toFixed(4)}`;
}

function timeAgo(ts) {
    if (!ts) return '';
    const diff = (Date.now() / 1000) - ts;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function getConfig(type) { return EVENT_TYPE_CONFIG[type] || DEFAULT_EVENT; }
function getStatusConfig(status) { return STATUS_CONFIG[status] || DEFAULT_STATUS; }

// ─── Skeleton Loader ────────────────────────────────────────────────
function TraceListSkeleton() {
    return (
        <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-9 h-9 rounded-lg bg-slate-200 dark:bg-slate-700" />
                        <div className="flex-1">
                            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-2" />
                            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/5" />
                        </div>
                        <div className="h-5 w-16 bg-slate-200 dark:bg-slate-700 rounded-full" />
                    </div>
                    <div className="grid grid-cols-4 gap-4">
                        {[...Array(4)].map((_, j) => (
                            <div key={j}>
                                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-2/3 mb-1.5" />
                                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2" />
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

// ─── KPI Card ───────────────────────────────────────────────────────
function KPICard({ icon: Icon, label, value, subtitle, color = 'primary', trend, index = 0 }) {
    const colors = {
        primary: { card: 'border-primary-200/60 dark:border-primary-800/40', icon: 'text-primary-500 bg-primary-50 dark:bg-primary-900/30', gradient: 'from-primary-500/5' },
        emerald: { card: 'border-emerald-200/60 dark:border-emerald-800/40', icon: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30', gradient: 'from-emerald-500/5' },
        amber:   { card: 'border-amber-200/60 dark:border-amber-800/40',   icon: 'text-amber-500 bg-amber-50 dark:bg-amber-900/30',   gradient: 'from-amber-500/5' },
        violet:  { card: 'border-violet-200/60 dark:border-violet-800/40', icon: 'text-violet-500 bg-violet-50 dark:bg-violet-900/30', gradient: 'from-violet-500/5' },
    };
    const c = colors[color] || colors.primary;
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06, type: 'spring', stiffness: 300, damping: 24 }}
            className={`relative overflow-hidden bg-gradient-to-br ${c.gradient} to-transparent bg-white dark:bg-slate-800/50 border ${c.card} rounded-xl p-4 lg:p-5`}
        >
            <div className="flex items-start gap-3">
                <div className={`p-2.5 rounded-lg ${c.icon} shadow-sm`}>
                    <Icon size={18} strokeWidth={2.2} />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</p>
                    <p className="text-2xl lg:text-[28px] font-bold text-slate-900 dark:text-white mt-0.5 tracking-tight">{value}</p>
                    {subtitle && <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
                </div>
            </div>
        </motion.div>
    );
}

// ─── Waterfall Bar ──────────────────────────────────────────────────
function WaterfallBar({ duration, maxDuration }) {
    if (!duration || !maxDuration) return null;
    const pct = Math.min((duration / maxDuration) * 100, 100);
    const color = pct > 75 ? 'bg-rose-400' : pct > 40 ? 'bg-amber-400' : 'bg-emerald-400';
    return (
        <div className="w-20 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden" title={formatDuration(duration)}>
            <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className={`h-full rounded-full ${color}`}
            />
        </div>
    );
}

// ─── Token Progress Bar ─────────────────────────────────────────────
function TokenBar({ prompt, completion, total }) {
    if (!total) return null;
    const promptPct = (prompt / total) * 100;
    return (
        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden flex" title={`Prompt: ${prompt?.toLocaleString() || 0} / Completion: ${completion?.toLocaleString() || 0}`}>
                <div className="h-full bg-indigo-400 rounded-l-full" style={{ width: `${promptPct}%` }} />
                <div className="h-full bg-violet-400 rounded-r-full flex-1" />
            </div>
            <span className="tabular-nums font-medium shrink-0">{total?.toLocaleString()}</span>
        </div>
    );
}

// ─── Trace Tree Node (Collapsible) ──────────────────────────────────
function TraceTreeNode({ event, level = 0, maxDuration }) {
    const [expanded, setExpanded] = useState(level < 2);
    const hasChildren = event.children && event.children.length > 0;
    const cfg = getConfig(event.event_type);
    const stCfg = getStatusConfig(event.status);
    const Icon = cfg.icon;

    return (
        <div className={level > 0 ? 'ml-3 lg:ml-5' : ''}>
            <div
                className={`group flex items-center gap-2.5 py-2 px-3 rounded-lg transition-all cursor-pointer
                    ${level === 0 ? 'bg-slate-50 dark:bg-slate-800/60' : ''}
                    hover:bg-slate-100 dark:hover:bg-slate-700/50`}
                onClick={() => hasChildren && setExpanded(!expanded)}
            >
                {/* Expand/collapse toggle */}
                <div className="w-4 shrink-0">
                    {hasChildren && (
                        <motion.div animate={{ rotate: expanded ? 0 : -90 }} transition={{ duration: 0.15 }}>
                            <ChevronDown size={14} className="text-slate-400" />
                        </motion.div>
                    )}
                </div>

                {/* Event type icon */}
                <div className={`p-1.5 rounded-md ${cfg.iconBg} shrink-0`}>
                    <Icon size={14} />
                </div>

                {/* Name + type tag */}
                <div className="flex-1 min-w-0 flex items-center gap-2">
                    <span className="font-medium text-sm text-slate-900 dark:text-white truncate">{event.name}</span>
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${cfg.pill}`}>
                        {cfg.label}
                    </span>
                </div>

                {/* Model badge */}
                {event.model && (
                    <span className="hidden lg:inline text-[10px] px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-md font-mono border border-slate-200 dark:border-slate-600">
                        {event.model}
                    </span>
                )}

                {/* Status dot */}
                <div className={`w-2 h-2 rounded-full ${stCfg.dot} shrink-0`} title={event.status || 'unknown'} />

                {/* Waterfall bar */}
                <WaterfallBar duration={event.duration} maxDuration={maxDuration} />

                {/* Token count */}
                {event.total_tokens > 0 && (
                    <span className="hidden sm:inline text-[11px] tabular-nums text-slate-500 dark:text-slate-400 font-medium shrink-0">
                        {event.total_tokens.toLocaleString()} tok
                    </span>
                )}

                {/* Cost */}
                {event.cost > 0 && (
                    <span className="hidden md:inline text-[11px] tabular-nums text-emerald-600 dark:text-emerald-400 font-medium shrink-0">
                        {formatCost(event.cost)}
                    </span>
                )}

                {/* Duration */}
                <span className="text-[11px] tabular-nums text-slate-500 dark:text-slate-400 font-medium shrink-0 w-14 text-right">
                    {formatDuration(event.duration)}
                </span>
            </div>

            {/* Children */}
            <AnimatePresence>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden border-l-2 border-slate-200 dark:border-slate-700 ml-5"
                    >
                        {event.children.map((child, idx) => (
                            <TraceTreeNode key={child.event_id || idx} event={child} level={level + 1} maxDuration={maxDuration} />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─── Expandable Section ─────────────────────────────────────────────
function ExpandableSection({ title, icon: Icon, children, defaultOpen = false }) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 px-4 py-3 bg-slate-50 dark:bg-slate-800/50 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
            >
                <Icon size={14} className="text-slate-400" />
                <span className="flex-1 text-left">{title}</span>
                <motion.div animate={{ rotate: open ? 0 : -90 }} transition={{ duration: 0.15 }}>
                    <ChevronDown size={14} className="text-slate-400" />
                </motion.div>
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 text-sm">{children}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─── Detail Panel ───────────────────────────────────────────────────
function TraceDetailPanel({ traceData, onClose }) {
    if (!traceData) return null;

    // Calculate max duration for waterfall scaling
    const allDurations = [];
    const collectDurations = (events) => {
        (events || []).forEach(e => {
            if (e.duration) allDurations.push(e.duration);
            if (e.children) collectDurations(e.children);
        });
    };
    collectDurations(traceData);
    const maxDuration = Math.max(...allDurations, 0.001);

    // Aggregate root-level metrics
    const root = traceData[0];
    const totalSpans = allDurations.length;

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="h-full flex flex-col bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700"
        >
            {/* Detail Header */}
            <div className="shrink-0 px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-slate-50 to-white dark:from-slate-800/80 dark:to-slate-800">
                <div className="flex items-center justify-between mb-3">
                    <button
                        onClick={onClose}
                        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                    >
                        <ArrowLeft size={14} />
                        <span className="hidden sm:inline">Back</span>
                    </button>
                    <div className="flex items-center gap-2">
                        {root?.status && (
                            <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${getStatusConfig(root.status).badge}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${getStatusConfig(root.status).dot}`} />
                                {root.status}
                            </span>
                        )}
                    </div>
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white truncate">{root?.name || 'Trace Details'}</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-1">{root?.trace_id}</p>
            </div>

            {/* Quick Stats */}
            <div className="shrink-0 grid grid-cols-3 gap-px bg-slate-200 dark:bg-slate-700 border-b border-slate-200 dark:border-slate-700">
                {[
                    { label: 'Duration', value: formatDuration(root?.duration), icon: Clock },
                    { label: 'Spans', value: totalSpans, icon: Layers },
                    { label: 'Cost', value: formatCost(root?.cost) || '—', icon: DollarSign },
                ].map(({ label, value, icon: I }) => (
                    <div key={label} className="bg-white dark:bg-slate-800 px-4 py-3 text-center">
                        <I size={13} className="mx-auto text-slate-400 mb-1" />
                        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
                        <p className="text-sm font-bold text-slate-900 dark:text-white">{value}</p>
                    </div>
                ))}
            </div>

            {/* Token Usage Bar */}
            {root?.total_tokens > 0 && (
                <div className="shrink-0 px-5 py-3 border-b border-slate-200 dark:border-slate-700">
                    <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Token Usage</p>
                    <TokenBar prompt={root.prompt_tokens} completion={root.completion_tokens} total={root.total_tokens} />
                    <div className="flex justify-between mt-1.5 text-[10px] text-slate-400">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-400 inline-block" /> Prompt: {(root.prompt_tokens || 0).toLocaleString()}</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-400 inline-block" /> Completion: {(root.completion_tokens || 0).toLocaleString()}</span>
                    </div>
                </div>
            )}

            {/* Prompt / Completion Preview */}
            {root && (root.inputs || root.outputs) && (
                <div className="shrink-0 px-5 py-3 border-b border-slate-200 dark:border-slate-700 space-y-3">
                    <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Quick Preview</p>
                    {root.inputs && Object.keys(root.inputs).length > 0 && (
                        <div>
                            <p className="text-[10px] font-medium text-indigo-500 dark:text-indigo-400 mb-1 flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-indigo-400 inline-block" /> Prompt / Input
                            </p>
                            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-2.5 border border-slate-200 dark:border-slate-700">
                                <p className="text-xs text-slate-600 dark:text-slate-300 font-mono whitespace-pre-wrap break-words line-clamp-4">
                                    {(() => {
                                        const val = typeof root.inputs === 'string' ? root.inputs : JSON.stringify(root.inputs, null, 2);
                                        return val.length > 300 ? val.substring(0, 300) + '…' : val;
                                    })()}
                                </p>
                            </div>
                        </div>
                    )}
                    {root.outputs && Object.keys(root.outputs).length > 0 && (
                        <div>
                            <p className="text-[10px] font-medium text-violet-500 dark:text-violet-400 mb-1 flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-violet-400 inline-block" /> Completion / Output
                            </p>
                            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-2.5 border border-slate-200 dark:border-slate-700">
                                <p className="text-xs text-slate-600 dark:text-slate-300 font-mono whitespace-pre-wrap break-words line-clamp-4">
                                    {(() => {
                                        const val = typeof root.outputs === 'string' ? root.outputs : JSON.stringify(root.outputs, null, 2);
                                        return val.length > 300 ? val.substring(0, 300) + '…' : val;
                                    })()}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Span Tree */}
            <div className="flex-1 overflow-y-auto px-3 py-4">
                <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 px-2">Span Waterfall</p>
                {traceData.map((event, idx) => (
                    <TraceTreeNode key={event.event_id || idx} event={event} level={0} maxDuration={maxDuration} />
                ))}

                {/* Inputs / Outputs */}
                {root && (
                    <div className="mt-6 space-y-3 px-2">
                        {root.inputs && Object.keys(root.inputs).length > 0 && (
                            <ExpandableSection title="Inputs" icon={FileCode}>
                                <pre className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg overflow-x-auto max-h-60 font-mono">
                                    {JSON.stringify(root.inputs, null, 2)}
                                </pre>
                            </ExpandableSection>
                        )}
                        {root.outputs && Object.keys(root.outputs).length > 0 && (
                            <ExpandableSection title="Outputs" icon={ExternalLink}>
                                <pre className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg overflow-x-auto max-h-60 font-mono">
                                    {JSON.stringify(root.outputs, null, 2)}
                                </pre>
                            </ExpandableSection>
                        )}
                        {root.error && (
                            <ExpandableSection title="Error" icon={AlertTriangle} defaultOpen>
                                <pre className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 p-3 rounded-lg overflow-x-auto max-h-40 font-mono">
                                    {typeof root.error === 'string' ? root.error : JSON.stringify(root.error, null, 2)}
                                </pre>
                            </ExpandableSection>
                        )}
                        {root.metadata && Object.keys(root.metadata).length > 0 && (
                            <ExpandableSection title="Metadata" icon={Tag}>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(root.metadata).map(([k, v]) => (
                                        <span key={k} className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-slate-600 dark:text-slate-300 font-mono">
                                            {k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                        </span>
                                    ))}
                                </div>
                            </ExpandableSection>
                        )}
                    </div>
                )}
            </div>
        </motion.div>
    );
}

// ─── Main Traces Page ───────────────────────────────────────────────
export function Traces() {
    const toast = useToast();
    const [traces, setTraces] = useState([]);
    const [selectedTrace, setSelectedTrace] = useState(null);
    const [detailData, setDetailData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [detailLoading, setDetailLoading] = useState(false);
    const [filterType, setFilterType] = useState('all');
    const [search, setSearch] = useState('');
    const { selectedProject } = useProject();

    useEffect(() => { fetchTraces(); }, [filterType, selectedProject]);

    const fetchTraces = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterType !== 'all') params.append('event_type', filterType);
            if (selectedProject) params.append('project', selectedProject);
            const response = await fetchApi(`/api/traces/?${params}`);
            setTraces(await response.json());
        } catch (error) {
            console.error('Failed to fetch traces:', error);
            toast.error(`Could not load traces: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const selectTrace = useCallback(async (traceId) => {
        setSelectedTrace(traceId);
        setDetailLoading(true);
        try {
            const response = await fetchApi(`/api/traces/${traceId}`);
            setDetailData(await response.json());
        } catch (error) {
            console.error('Failed to fetch trace details:', error);
            toast.error(`Could not load trace details: ${error.message}`);
        } finally {
            setDetailLoading(false);
        }
    }, []);

    const maxListDuration = useMemo(() => Math.max(...traces.map(t => t.duration || 0), 0.001), [traces]);

    const kpis = useMemo(() => {
        const total = traces.length;
        const totalTokens = traces.reduce((s, t) => s + (t.total_tokens || 0), 0);
        const totalCost = traces.reduce((s, t) => s + (t.cost || 0), 0);
        const avgDuration = total > 0 ? traces.reduce((s, t) => s + (t.duration || 0), 0) / total : 0;
        return { total, totalTokens, totalCost, avgDuration };
    }, [traces]);

    const filteredTraces = useMemo(() => {
        if (!search) return traces;
        const q = search.toLowerCase();
        return traces.filter(t =>
            (t.name || '').toLowerCase().includes(q) ||
            (t.trace_id || '').toLowerCase().includes(q) ||
            (t.model || '').toLowerCase().includes(q)
        );
    }, [traces, search]);

    const showDetail = selectedTrace && detailData && !detailLoading;

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* ──── Gradient Header ──── */}
            <div className="shrink-0 bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 dark:from-indigo-900 dark:via-violet-900 dark:to-purple-900 px-4 md:px-6 py-5 lg:py-6">
                <div className="max-w-[1800px] mx-auto">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                            <h1 className="text-xl lg:text-2xl font-bold text-white flex items-center gap-2.5">
                                <div className="p-2 rounded-lg bg-white/10 backdrop-blur-sm">
                                    <Activity size={20} />
                                </div>
                                GenAI Traces
                            </h1>
                            <p className="text-sm text-white/70 mt-1">
                                Full observability for LLM calls, agents, tools, chains &amp; sessions
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <select
                                value={filterType}
                                onChange={(e) => setFilterType(e.target.value)}
                                className="px-3 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-sm text-white focus:ring-2 focus:ring-white/30 focus:border-transparent [&>option]:text-slate-900 [&>option]:bg-white"
                            >
                                <option value="all">All Types</option>
                                <option value="session">Sessions</option>
                                <option value="llm">LLM Calls</option>
                                <option value="chat_model">Chat Models</option>
                                <option value="tool">Tool Calls</option>
                                <option value="chain">Chains</option>
                                <option value="agent">Agents</option>
                                <option value="embedding">Embeddings</option>
                                <option value="retriever">Retrievers</option>
                                <option value="graph_node">Graph Nodes</option>
                            </select>
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={fetchTraces}
                                className="!bg-white/10 !border-white/20 !text-white hover:!bg-white/20"
                            >
                                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                            </Button>
                        </div>
                    </div>

                    {/* KPI Row */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
                        <KPICard icon={Layers} label="Total Traces" value={kpis.total} color="primary" index={0} />
                        <KPICard icon={Clock} label="Avg Latency" value={formatDuration(kpis.avgDuration)} subtitle="per trace" color="violet" index={1} />
                        <KPICard icon={Hash} label="Total Tokens" value={kpis.totalTokens.toLocaleString()} color="amber" index={2} />
                        <KPICard icon={DollarSign} label="Est. Cost" value={`$${kpis.totalCost.toFixed(4)}`} color="emerald" index={3} />
                    </div>
                </div>
            </div>

            {/* ──── Master-Detail Body ──── */}
            <div className="flex-1 flex overflow-hidden">
                {/* ──── Trace List (Left) ──── */}
                <div className={`${showDetail ? 'hidden lg:flex' : 'flex'} flex-col flex-1 min-w-0 overflow-hidden border-r border-slate-200 dark:border-slate-700`}>
                    {/* Search */}
                    <div className="shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                        <div className="relative max-w-md">
                            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search by name, trace ID, or model..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
                            />
                        </div>
                    </div>

                    {/* List */}
                    <div className="flex-1 overflow-y-auto bg-slate-50/50 dark:bg-slate-900/20">
                        {loading ? (
                            <div className="p-4"><TraceListSkeleton /></div>
                        ) : filteredTraces.length === 0 ? (
                            <div className="p-6">
                                <EmptyState
                                    icon={Activity}
                                    title="No traces found"
                                    description={search
                                        ? "No traces match your search. Try adjusting your filters."
                                        : "Use @observe decorator on any agent function to get full traces here. Works with LangGraph, LangChain, OpenAI, and any custom GenAI code."
                                    }
                                />
                            </div>
                        ) : (
                            <div className="p-3 space-y-2">
                                {filteredTraces.map((trace, idx) => {
                                    const cfg = getConfig(trace.event_type);
                                    const stCfg = getStatusConfig(trace.status);
                                    const Icon = cfg.icon;
                                    const isActive = selectedTrace === trace.trace_id;

                                    return (
                                        <motion.div
                                            key={trace.event_id || idx}
                                            initial={{ opacity: 0, y: 8 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: Math.min(idx * 0.02, 0.3) }}
                                            onClick={() => selectTrace(trace.trace_id)}
                                            className={`group rounded-xl border transition-all duration-200 cursor-pointer p-3.5
                                                ${isActive
                                                    ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-300 dark:border-indigo-700 shadow-sm'
                                                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600'
                                                }`}
                                        >
                                            {/* Row 1: Icon + Name + Status */}
                                            <div className="flex items-center gap-3 mb-2.5">
                                                <div className={`p-2 rounded-lg ${cfg.cardBg} shrink-0`}>
                                                    <Icon size={16} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="font-semibold text-sm text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                                                        {trace.name}
                                                    </h3>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        <span className="text-[10px] text-slate-400 font-mono">{trace.trace_id?.slice(0, 8)}</span>
                                                        {trace.start_time && (
                                                            <span className="text-[10px] text-slate-400">{timeAgo(trace.start_time)}</span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2 shrink-0">
                                                    {trace.model && (
                                                        <span className="text-[10px] px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 rounded-md font-mono border border-indigo-200 dark:border-indigo-700 truncate max-w-[140px]">
                                                            {trace.model}
                                                        </span>
                                                    )}
                                                    <span className={`w-2 h-2 rounded-full ${stCfg.dot}`} />
                                                    <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
                                                </div>
                                            </div>

                                            {/* Row 2: Metrics strip */}
                                            <div className="flex items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400">
                                                <div className="flex items-center gap-1">
                                                    <Clock size={11} />
                                                    <span className="tabular-nums font-medium">{formatDuration(trace.duration)}</span>
                                                </div>
                                                {trace.total_tokens > 0 && (
                                                    <div className="flex items-center gap-1">
                                                        <Hash size={11} />
                                                        <span className="tabular-nums font-medium">{trace.total_tokens.toLocaleString()}</span>
                                                    </div>
                                                )}
                                                {trace.cost > 0 && (
                                                    <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                                                        <DollarSign size={11} />
                                                        <span className="tabular-nums font-medium">{formatCost(trace.cost)}</span>
                                                    </div>
                                                )}
                                                {trace.model && (
                                                    <span className="hidden lg:inline ml-auto text-[10px] px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded font-mono truncate max-w-[120px]">
                                                        {trace.model}
                                                    </span>
                                                )}
                                                <WaterfallBar duration={trace.duration} maxDuration={maxListDuration} />
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>

                {/* ──── Detail Panel (Right) ──── */}
                <AnimatePresence>
                    {showDetail && (
                        <div className="w-full lg:w-[480px] xl:w-[560px] shrink-0 overflow-hidden">
                            <TraceDetailPanel
                                traceData={detailData}
                                onClose={() => { setSelectedTrace(null); setDetailData(null); }}
                            />
                        </div>
                    )}
                </AnimatePresence>

                {/* Detail Loading */}
                {selectedTrace && detailLoading && (
                    <div className="w-full lg:w-[480px] xl:w-[560px] shrink-0 flex items-center justify-center bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700">
                        <div className="text-center">
                            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
                            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Loading trace…</p>
                        </div>
                    </div>
                )}

                {/* No selection state */}
                {!selectedTrace && !loading && filteredTraces.length > 0 && (
                    <div className="hidden lg:flex w-[480px] xl:w-[560px] shrink-0 items-center justify-center bg-slate-50/50 dark:bg-slate-900/20 border-l border-slate-200 dark:border-slate-700">
                        <div className="text-center max-w-xs">
                            <div className="mx-auto w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mb-4">
                                <Activity size={28} className="text-indigo-500" />
                            </div>
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Select a trace</h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Click on any trace to view its span tree, token usage, costs, and full details</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
