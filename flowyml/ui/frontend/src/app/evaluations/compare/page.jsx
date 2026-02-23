import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
    ArrowLeft, ArrowUpRight, ArrowDownRight, Minus,
    ClipboardCheck, BarChart3,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';
import { compareEvaluations, getEvalResult } from '../../../services/evaluationsApi';

// ─── Delta indicator ───────────────────────────────────────────────
function DeltaIndicator({ value, higherIsBetter = true }) {
    if (value == null || value === 0) {
        return <Minus size={14} className="text-slate-400" />;
    }
    const isPositive = higherIsBetter ? value > 0 : value < 0;
    return (
        <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
            {value > 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {Math.abs(value * 100).toFixed(1)}%
        </span>
    );
}

// ─── Comparison Page ───────────────────────────────────────────────
export function EvaluationCompare() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const evalIds = useMemo(() => (searchParams.get('ids') || '').split(',').filter(Boolean), [searchParams]);

    const [comparison, setComparison] = useState(null);
    const [evalDetails, setEvalDetails] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (evalIds.length < 2) {
            setError('At least 2 evaluation IDs required');
            setLoading(false);
            return;
        }
        const fetchComparison = async () => {
            setLoading(true);
            try {
                const [compResult, ...details] = await Promise.all([
                    compareEvaluations(evalIds),
                    ...evalIds.map(id => getEvalResult(id).catch(() => null)),
                ]);
                setComparison(compResult);
                const detailMap = {};
                evalIds.forEach((id, i) => { detailMap[id] = details[i]; });
                setEvalDetails(detailMap);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchComparison();
    }, [evalIds]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4">
                <p className="text-rose-500 font-medium">{error}</p>
                <Button variant="secondary" size="sm" onClick={() => navigate('/evaluations')}>
                    <ArrowLeft size={14} className="mr-2" /> Back
                </Button>
            </div>
        );
    }

    const metrics = Object.keys(comparison?.metrics || {}).sort();
    const baseId = evalIds[0];

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="max-w-[1800px] mx-auto">
                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
                        <Link to="/evaluations" className="hover:text-primary-600 transition-colors">Evaluations</Link>
                        <span>/</span>
                        <span className="text-slate-700 dark:text-slate-300">Compare</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" onClick={() => navigate('/evaluations')}>
                            <ArrowLeft size={20} />
                        </Button>
                        <div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <BarChart3 className="text-teal-500" size={20} />
                                Compare Evaluations
                            </h1>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Comparing {evalIds.length} evaluation runs
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-[1800px] mx-auto space-y-6">
                    {/* Summary row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {evalIds.map((id, idx) => {
                            const detail = evalDetails[id];
                            return (
                                <motion.div
                                    key={id}
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.08 }}
                                >
                                    <Card hover={false} className={`p-4 ${idx === 0 ? 'ring-2 ring-primary-300 dark:ring-primary-700' : ''}`}>
                                        <div className="flex items-center justify-between mb-2">
                                            <Badge variant={idx === 0 ? 'primary' : 'default'} className="text-[10px]">
                                                {idx === 0 ? 'Baseline' : `Run ${idx + 1}`}
                                            </Badge>
                                            {detail?.passed != null && (
                                                detail.passed
                                                    ? <Badge variant="success" className="text-[10px]">Passed</Badge>
                                                    : <Badge variant="danger" className="text-[10px]">Failed</Badge>
                                            )}
                                        </div>
                                        <p className="font-mono text-xs text-slate-700 dark:text-slate-300 truncate">{id}</p>
                                        <p className="text-xs text-slate-500 mt-1">{detail?.experiment || detail?.pipeline_name || '—'}</p>
                                        <p className="text-lg font-bold text-slate-900 dark:text-white mt-2">
                                            {detail?.pass_rate != null ? `${(detail.pass_rate * 100).toFixed(1)}%` : '—'}
                                        </p>
                                        <p className="text-[10px] text-slate-400">Pass Rate</p>
                                    </Card>
                                </motion.div>
                            );
                        })}
                    </div>

                    {/* Comparison Table */}
                    {metrics.length > 0 ? (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm"
                        >
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                            Metric
                                        </th>
                                        {evalIds.map((id, idx) => (
                                            <th key={id} className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                                {idx === 0 ? 'Baseline' : `Run ${idx + 1}`}
                                                <br />
                                                <span className="font-mono text-[10px] text-slate-400 normal-case">{id.substring(0, 8)}…</span>
                                            </th>
                                        ))}
                                        {evalIds.length === 2 && (
                                            <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                                Delta
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    {metrics.map((metric, idx) => {
                                        const values = comparison.metrics[metric] || {};
                                        const baseVal = values[baseId];
                                        return (
                                            <motion.tr
                                                key={metric}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                transition={{ delay: idx * 0.03 }}
                                                className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                                            >
                                                <td className="px-5 py-3.5">
                                                    <span className="text-sm font-medium text-slate-900 dark:text-white">{metric}</span>
                                                </td>
                                                {evalIds.map(id => {
                                                    const val = values[id];
                                                    return (
                                                        <td key={id} className="px-5 py-3.5 text-center">
                                                            <div className="flex flex-col items-center gap-1">
                                                                <span className="text-sm font-bold text-slate-900 dark:text-white">
                                                                    {val != null ? (typeof val === 'number' ? val.toFixed(4) : String(val)) : '—'}
                                                                </span>
                                                                {val != null && typeof val === 'number' && (
                                                                    <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                                        <div
                                                                            className={`h-full rounded-full ${val >= 0.8 ? 'bg-emerald-500' : val >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                                                            style={{ width: `${Math.min(val * 100, 100)}%` }}
                                                                        />
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </td>
                                                    );
                                                })}
                                                {evalIds.length === 2 && (
                                                    <td className="px-5 py-3.5 text-center">
                                                        {baseVal != null && values[evalIds[1]] != null && typeof baseVal === 'number' ? (
                                                            <DeltaIndicator value={values[evalIds[1]] - baseVal} />
                                                        ) : (
                                                            <Minus size={14} className="text-slate-400 mx-auto" />
                                                        )}
                                                    </td>
                                                )}
                                            </motion.tr>
                                        );
                                    })}

                                    {/* Summary row: overall pass rate */}
                                    <tr className="bg-slate-50 dark:bg-slate-800/80 font-semibold">
                                        <td className="px-5 py-3.5 text-sm text-slate-700 dark:text-slate-300">Overall Pass Rate</td>
                                        {evalIds.map(id => {
                                            const detail = evalDetails[id];
                                            return (
                                                <td key={id} className="px-5 py-3.5 text-center text-sm text-slate-900 dark:text-white">
                                                    {detail?.pass_rate != null ? `${(detail.pass_rate * 100).toFixed(1)}%` : '—'}
                                                </td>
                                            );
                                        })}
                                        {evalIds.length === 2 && (
                                            <td className="px-5 py-3.5 text-center">
                                                {evalDetails[evalIds[0]]?.pass_rate != null && evalDetails[evalIds[1]]?.pass_rate != null ? (
                                                    <DeltaIndicator value={evalDetails[evalIds[1]].pass_rate - evalDetails[evalIds[0]].pass_rate} />
                                                ) : (
                                                    <Minus size={14} className="text-slate-400 mx-auto" />
                                                )}
                                            </td>
                                        )}
                                    </tr>
                                </tbody>
                            </table>
                        </motion.div>
                    ) : (
                        <Card hover={false} className="text-center py-12">
                            <ClipboardCheck size={32} className="text-slate-400 mx-auto mb-3" />
                            <p className="text-slate-500">No metrics available for comparison</p>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
