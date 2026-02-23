import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
    ArrowLeft, ClipboardCheck, CheckCircle2, XCircle,
    BarChart3, Info, Calendar, Tag, Hash, Sparkles,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';
import { getEvalResult } from '../../../services/evaluationsApi';

// ─── Score Bar ─────────────────────────────────────────────────────
function ScoreBar({ value, passed, threshold }) {
    const pct = Math.min(Math.max((value || 0) * 100, 0), 100);
    const color = passed === true
        ? 'bg-emerald-500'
        : passed === false
            ? 'bg-rose-500'
            : pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500';

    return (
        <div className="flex items-center gap-3 w-full">
            <div className="flex-1 h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden relative">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                    className={`h-full rounded-full ${color}`}
                />
                {threshold != null && (
                    <div
                        className="absolute top-0 h-full w-0.5 bg-slate-900 dark:bg-white opacity-40"
                        style={{ left: `${threshold * 100}%` }}
                        title={`Threshold: ${threshold}`}
                    />
                )}
            </div>
            <span className="text-sm font-bold text-slate-900 dark:text-white min-w-[48px] text-right">
                {pct.toFixed(1)}%
            </span>
        </div>
    );
}

// ─── Score Card ────────────────────────────────────────────────────
function ScoreCard({ name, value, passed, rationale, index }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06 }}
        >
            <Card hover={false} className="p-5">
                <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${passed === true ? 'bg-emerald-500' : passed === false ? 'bg-rose-500' : 'bg-slate-400'}`} />
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{name}</h4>
                    </div>
                    {passed != null && (
                        passed ? (
                            <Badge variant="success" className="gap-1 text-xs">
                                <CheckCircle2 size={10} /> Pass
                            </Badge>
                        ) : (
                            <Badge variant="danger" className="gap-1 text-xs">
                                <XCircle size={10} /> Fail
                            </Badge>
                        )
                    )}
                </div>

                <ScoreBar value={typeof value === 'number' ? value : 0} passed={passed} />

                {rationale && (
                    <div className="mt-3">
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                        >
                            <Info size={12} />
                            {expanded ? 'Hide rationale' : 'Show rationale'}
                        </button>
                        {expanded && (
                            <motion.p
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="text-xs text-slate-500 dark:text-slate-400 mt-2 bg-slate-50 dark:bg-slate-900 rounded-lg p-3 leading-relaxed"
                            >
                                {rationale}
                            </motion.p>
                        )}
                    </div>
                )}
            </Card>
        </motion.div>
    );
}

// ─── Metadata Row ──────────────────────────────────────────────────
function MetaRow({ icon: Icon, label, value }) {
    return (
        <div className="flex items-center gap-3 py-2">
            <Icon size={14} className="text-slate-400 shrink-0" />
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 min-w-[100px]">{label}</span>
            <span className="text-sm text-slate-900 dark:text-white font-mono">{value || '—'}</span>
        </div>
    );
}

// ─── Detail Page ───────────────────────────────────────────────────
export function EvaluationDetail() {
    const { evalId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchDetail = async () => {
            setLoading(true);
            try {
                const result = await getEvalResult(evalId);
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchDetail();
    }, [evalId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4">
                <XCircle size={48} className="text-rose-400" />
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">Evaluation not found</h2>
                <p className="text-sm text-slate-500">{error || 'No data available'}</p>
                <Button variant="secondary" size="sm" onClick={() => navigate('/evaluations')}>
                    <ArrowLeft size={14} className="mr-2" /> Back to Evaluations
                </Button>
            </div>
        );
    }

    // Parse scores from summary or detailed results
    const scores = Object.entries(data.summary || data.metrics || {}).map(([name, value]) => ({
        name,
        value: typeof value === 'number' ? value : parseFloat(value) || 0,
        passed: data.passed,
        rationale: data.rationale?.[name] || null,
    }));

    const passRate = data.pass_rate ?? (scores.length > 0 ? scores.filter(s => s.value >= 0.5).length / scores.length : 0);

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="max-w-[1800px] mx-auto">
                    {/* Breadcrumb */}
                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
                        <Link to="/evaluations" className="hover:text-primary-600 transition-colors">Evaluations</Link>
                        <span>/</span>
                        <span className="text-slate-700 dark:text-slate-300 font-mono">{evalId?.substring(0, 12)}…</span>
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Button variant="ghost" size="icon" onClick={() => navigate('/evaluations')}>
                                <ArrowLeft size={20} />
                            </Button>
                            <div>
                                <h1 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <Sparkles className="text-teal-500" size={20} />
                                    Evaluation Run
                                </h1>
                                <p className="text-xs text-slate-500 font-mono mt-0.5">{evalId}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            {data.passed != null && (
                                data.passed ? (
                                    <Badge variant="success" className="gap-1.5 text-sm px-3 py-1.5">
                                        <CheckCircle2 size={14} /> All Passed
                                    </Badge>
                                ) : (
                                    <Badge variant="danger" className="gap-1.5 text-sm px-3 py-1.5">
                                        <XCircle size={14} /> Failed
                                    </Badge>
                                )
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-[1800px] mx-auto space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <Card hover={false} className="p-4 flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600">
                                <BarChart3 size={18} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Pass Rate</p>
                                <p className="text-lg font-bold text-slate-900 dark:text-white">{(passRate * 100).toFixed(1)}%</p>
                            </div>
                        </Card>
                        <Card hover={false} className="p-4 flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-violet-100 dark:bg-violet-900/30 text-violet-600">
                                <Hash size={18} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Scorers</p>
                                <p className="text-lg font-bold text-slate-900 dark:text-white">{scores.length}</p>
                            </div>
                        </Card>
                        <Card hover={false} className="p-4 flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600">
                                <Tag size={18} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Experiment</p>
                                <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{data.experiment || data.pipeline_name || '—'}</p>
                            </div>
                        </Card>
                        <Card hover={false} className="p-4 flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600">
                                <Calendar size={18} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Created</p>
                                <p className="text-sm font-semibold text-slate-900 dark:text-white">{data.created_at || data.start_time || '—'}</p>
                            </div>
                        </Card>
                    </div>

                    {/* Scores Grid */}
                    <div>
                        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-4">
                            Score Breakdown
                        </h2>
                        {scores.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {scores.map((s, i) => (
                                    <ScoreCard key={s.name} {...s} index={i} />
                                ))}
                            </div>
                        ) : (
                            <Card hover={false} className="text-center py-8">
                                <p className="text-slate-500">No individual scores available</p>
                            </Card>
                        )}
                    </div>

                    {/* Metadata */}
                    <Card hover={false}>
                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3">
                            Metadata
                        </h3>
                        <div className="divide-y divide-slate-100 dark:divide-slate-700">
                            <MetaRow icon={Hash} label="Eval ID" value={evalId} />
                            <MetaRow icon={Tag} label="Experiment" value={data.experiment || data.pipeline_name} />
                            <MetaRow icon={Tag} label="Dataset" value={data.dataset_name} />
                            <MetaRow icon={Calendar} label="Created" value={data.created_at || data.start_time} />
                            <MetaRow icon={BarChart3} label="Pass Rate" value={`${(passRate * 100).toFixed(1)}%`} />
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
