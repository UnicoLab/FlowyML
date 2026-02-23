import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
    ClipboardCheck, RefreshCw, Plus, Activity, TrendingUp, TrendingDown,
    CheckCircle2, XCircle, ChevronRight, Filter, Search, Percent,
    BarChart3, Sparkles, ArrowUpDown,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { listEvaluations, runEvaluation, getAvailableScorers } from '../../services/evaluationsApi';

// ─── KPI Card ──────────────────────────────────────────────────────
function KPICard({ icon: Icon, label, value, subtitle, color = 'primary', index = 0 }) {
    const colorMap = {
        primary: 'from-primary-500/10 to-primary-600/5 border-primary-200 dark:border-primary-800',
        emerald: 'from-emerald-500/10 to-emerald-600/5 border-emerald-200 dark:border-emerald-800',
        amber: 'from-amber-500/10 to-amber-600/5 border-amber-200 dark:border-amber-800',
        violet: 'from-violet-500/10 to-violet-600/5 border-violet-200 dark:border-violet-800',
    };
    const iconColorMap = {
        primary: 'text-primary-500',
        emerald: 'text-emerald-500',
        amber: 'text-amber-500',
        violet: 'text-violet-500',
    };
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className={`bg-gradient-to-br ${colorMap[color]} border rounded-xl p-5 flex items-start gap-4`}
        >
            <div className={`p-3 rounded-lg bg-white/80 dark:bg-slate-800/80 shadow-sm ${iconColorMap[color]}`}>
                <Icon size={22} />
            </div>
            <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">{value}</p>
                {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>}
            </div>
        </motion.div>
    );
}

// ─── New Evaluation Modal ──────────────────────────────────────────
function NewEvalModal({ open, onClose, onSubmit, scorers }) {
    const [formData, setFormData] = useState({
        dataJson: '[\n  {\n    "inputs": {"query": "What is ML?"},\n    "outputs": "Machine Learning is a branch of AI.",\n    "context": ["ML is a subset of artificial intelligence."]\n  }\n]',
        selectedScorers: [],
        experiment: '',
        threshold: '0.7',
    });
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const data = JSON.parse(formData.dataJson);
            const result = await onSubmit({
                data,
                scorers: formData.selectedScorers,
                experiment: formData.experiment || undefined,
                threshold: parseFloat(formData.threshold) || undefined,
            });
            onClose(result);
        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setSubmitting(false);
        }
    };

    const toggleScorer = (name) => {
        setFormData(prev => ({
            ...prev,
            selectedScorers: prev.selectedScorers.includes(name)
                ? prev.selectedScorers.filter(s => s !== name)
                : [...prev.selectedScorers, name],
        }));
    };

    if (!open) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
                onClick={() => onClose()}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-2xl w-[700px] max-h-[85vh] overflow-y-auto"
                    onClick={e => e.stopPropagation()}
                >
                    <div className="p-6 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Sparkles className="text-amber-500" size={20} />
                            New Evaluation Run
                        </h2>
                        <p className="text-sm text-slate-500 mt-1">Run scorers against your evaluation data</p>
                    </div>

                    <form onSubmit={handleSubmit} className="p-6 space-y-5">
                        {/* Data */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                Evaluation Data (JSON)
                            </label>
                            <textarea
                                value={formData.dataJson}
                                onChange={e => setFormData(p => ({ ...p, dataJson: e.target.value }))}
                                rows={6}
                                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-sm font-mono p-3 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                            />
                        </div>

                        {/* Scorers */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                Scorers ({formData.selectedScorers.length} selected)
                            </label>
                            <div className="grid grid-cols-2 gap-2 max-h-[200px] overflow-y-auto p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
                                {scorers.map(s => (
                                    <button
                                        key={s.name}
                                        type="button"
                                        onClick={() => toggleScorer(s.name)}
                                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${formData.selectedScorers.includes(s.name)
                                                ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 ring-1 ring-primary-300 dark:ring-primary-700'
                                                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-600'
                                            }`}
                                    >
                                        <span className={`w-2 h-2 rounded-full ${formData.selectedScorers.includes(s.name) ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                                        {s.name}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Experiment & Threshold */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                    Experiment Name
                                </label>
                                <input
                                    type="text"
                                    placeholder="e.g. rag_quality_v2"
                                    value={formData.experiment}
                                    onChange={e => setFormData(p => ({ ...p, experiment: e.target.value }))}
                                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-sm p-2.5 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                    Pass Threshold
                                </label>
                                <input
                                    type="number"
                                    step="0.05"
                                    min="0"
                                    max="1"
                                    value={formData.threshold}
                                    onChange={e => setFormData(p => ({ ...p, threshold: e.target.value }))}
                                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-sm p-2.5 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex justify-end gap-3 pt-2">
                            <Button variant="ghost" size="sm" type="button" onClick={() => onClose()}>Cancel</Button>
                            <Button
                                size="sm"
                                type="submit"
                                disabled={submitting || formData.selectedScorers.length === 0}
                            >
                                {submitting ? (
                                    <><RefreshCw size={14} className="mr-2 animate-spin" />Running...</>
                                ) : (
                                    <><Sparkles size={14} className="mr-2" />Run Evaluation</>
                                )}
                            </Button>
                        </div>
                    </form>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

// ─── Main Evaluations Page ─────────────────────────────────────────
export function Evaluations() {
    const navigate = useNavigate();
    const [evaluations, setEvaluations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [modalOpen, setModalOpen] = useState(false);
    const [scorers, setScorers] = useState([]);
    const [sortField, setSortField] = useState('created_at');
    const [sortDir, setSortDir] = useState('desc');

    // Selection & Comparison
    const [selectionMode, setSelectionMode] = useState('single');
    const [selectedIds, setSelectedIds] = useState([]);

    useEffect(() => {
        fetchData();
        loadScorers();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await listEvaluations({ limit: 50 });
            setEvaluations(data.evaluations || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadScorers = async () => {
        try {
            const data = await getAvailableScorers();
            setScorers(data || []);
        } catch {
            // Scorers will be empty
        }
    };

    const handleNewEval = async (params) => {
        const result = await runEvaluation(params);
        fetchData();
        return result;
    };

    const handleModalClose = (result) => {
        setModalOpen(false);
        if (result?.eval_id) {
            navigate(`/evaluations/${result.eval_id}`);
        }
    };

    const handleCompare = () => {
        if (selectedIds.length >= 2) {
            navigate(`/evaluations/compare?ids=${selectedIds.join(',')}`);
        }
    };

    // KPI calculations
    const kpis = useMemo(() => {
        const total = evaluations.length;
        const passRates = evaluations.map(e => e.pass_rate ?? 1);
        const avgPassRate = total > 0 ? passRates.reduce((a, b) => a + b, 0) / total : 0;
        const totalPassed = evaluations.filter(e => e.passed).length;
        const scorerSet = new Set();
        evaluations.forEach(e => {
            Object.keys(e.summary || {}).forEach(k => scorerSet.add(k));
        });
        return { total, avgPassRate, totalPassed, uniqueScorers: scorerSet.size };
    }, [evaluations]);

    // Filtered & sorted
    const filteredEvals = useMemo(() => {
        let result = evaluations;
        if (search) {
            const q = search.toLowerCase();
            result = result.filter(e =>
                (e.eval_id || '').toLowerCase().includes(q) ||
                (e.experiment || '').toLowerCase().includes(q) ||
                (e.dataset_name || '').toLowerCase().includes(q)
            );
        }
        result.sort((a, b) => {
            const av = a[sortField] ?? '';
            const bv = b[sortField] ?? '';
            const cmp = av < bv ? -1 : av > bv ? 1 : 0;
            return sortDir === 'asc' ? cmp : -cmp;
        });
        return result;
    }, [evaluations, search, sortField, sortDir]);

    const toggleSort = (field) => {
        if (sortField === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir('desc');
        }
    };

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <ClipboardCheck className="text-teal-500" />
                            Evaluations
                        </h1>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Monitor, compare, and run evaluation suites
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        {selectionMode === 'multi' ? (
                            <>
                                <span className="text-sm text-slate-500 mr-1">
                                    {selectedIds.length} selected
                                </span>
                                <Button
                                    size="sm"
                                    variant="primary"
                                    disabled={selectedIds.length < 2}
                                    onClick={handleCompare}
                                >
                                    <Activity size={14} className="mr-2" />
                                    Compare
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => { setSelectionMode('single'); setSelectedIds([]); }}>
                                    Cancel
                                </Button>
                            </>
                        ) : (
                            <>
                                <Button variant="secondary" size="sm" onClick={() => { setSelectionMode('multi'); setSelectedIds([]); }}>
                                    <ArrowUpDown size={14} className="mr-2" />
                                    Compare
                                </Button>
                                <Button size="sm" onClick={() => setModalOpen(true)}>
                                    <Plus size={14} className="mr-2" />
                                    New Evaluation
                                </Button>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-[1800px] mx-auto space-y-6">
                    {/* KPI Row */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <KPICard icon={ClipboardCheck} label="Total Evaluations" value={kpis.total} color="primary" index={0} />
                        <KPICard icon={Percent} label="Avg Pass Rate" value={`${(kpis.avgPassRate * 100).toFixed(1)}%`} subtitle={`${kpis.totalPassed}/${kpis.total} passed`} color="emerald" index={1} />
                        <KPICard icon={BarChart3} label="Unique Scorers" value={kpis.uniqueScorers} subtitle={`${scorers.length} available`} color="violet" index={2} />
                        <KPICard icon={TrendingUp} label="Available Adapters" value="3" subtitle="DeepEval · RAGAS · Phoenix" color="amber" index={3} />
                    </div>

                    {/* Search */}
                    <div className="flex items-center gap-3">
                        <div className="relative flex-1 max-w-sm">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search by ID, experiment, or dataset..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            />
                        </div>
                        <Button variant="ghost" size="sm" onClick={fetchData}>
                            <RefreshCw size={14} />
                        </Button>
                    </div>

                    {/* Table */}
                    {loading ? (
                        <div className="text-center py-16">
                            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
                        </div>
                    ) : error ? (
                        <Card hover={false} className="text-center py-8">
                            <p className="text-rose-500 font-medium">{error}</p>
                            <Button variant="ghost" size="sm" className="mt-3" onClick={fetchData}>
                                <RefreshCw size={14} className="mr-2" /> Retry
                            </Button>
                        </Card>
                    ) : filteredEvals.length === 0 ? (
                        <EmptyState
                            icon={ClipboardCheck}
                            title="No evaluations yet"
                            description="Run your first evaluation to see results here."
                            action={
                                <Button size="sm" onClick={() => setModalOpen(true)}>
                                    <Plus size={14} className="mr-2" /> New Evaluation
                                </Button>
                            }
                        />
                    ) : (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm"
                        >
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                                        {selectionMode === 'multi' && (
                                            <th className="px-4 py-3 w-10" />
                                        )}
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-200" onClick={() => toggleSort('eval_id')}>
                                            Eval ID {sortField === 'eval_id' && <ArrowUpDown size={12} className="inline ml-1" />}
                                        </th>
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700" onClick={() => toggleSort('experiment')}>
                                            Experiment {sortField === 'experiment' && <ArrowUpDown size={12} className="inline ml-1" />}
                                        </th>
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700" onClick={() => toggleSort('pass_rate')}>
                                            Pass Rate {sortField === 'pass_rate' && <ArrowUpDown size={12} className="inline ml-1" />}
                                        </th>
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Scorers</th>
                                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700" onClick={() => toggleSort('created_at')}>
                                            Created {sortField === 'created_at' && <ArrowUpDown size={12} className="inline ml-1" />}
                                        </th>
                                        <th className="px-5 py-3 w-10" />
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    {filteredEvals.map((ev, idx) => (
                                        <motion.tr
                                            key={ev.eval_id || idx}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: idx * 0.03 }}
                                            onClick={() => selectionMode === 'single' && navigate(`/evaluations/${ev.eval_id}`)}
                                            className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer group"
                                        >
                                            {selectionMode === 'multi' && (
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIds.includes(ev.eval_id)}
                                                        onChange={e => {
                                                            if (e.target.checked) setSelectedIds(p => [...p, ev.eval_id]);
                                                            else setSelectedIds(p => p.filter(i => i !== ev.eval_id));
                                                        }}
                                                        onClick={e => e.stopPropagation()}
                                                        className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                                                    />
                                                </td>
                                            )}
                                            <td className="px-5 py-3.5">
                                                <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
                                                    {(ev.eval_id || '').substring(0, 12)}…
                                                </span>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className="text-sm font-medium text-slate-900 dark:text-white">
                                                    {ev.experiment || '—'}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                {ev.passed ? (
                                                    <Badge variant="success" className="gap-1">
                                                        <CheckCircle2 size={12} /> Passed
                                                    </Badge>
                                                ) : (
                                                    <Badge variant="danger" className="gap-1">
                                                        <XCircle size={12} /> Failed
                                                    </Badge>
                                                )}
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-20 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full transition-all ${(ev.pass_rate || 0) >= 0.8 ? 'bg-emerald-500' : (ev.pass_rate || 0) >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                                            style={{ width: `${(ev.pass_rate || 0) * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                                        {((ev.pass_rate || 0) * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className="text-xs text-slate-500">{ev.scorer_count || Object.keys(ev.summary || {}).length}</span>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className="text-xs text-slate-500">{ev.created_at || '—'}</span>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <ChevronRight size={16} className="text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                        </motion.div>
                    )}
                </div>
            </div>

            {/* Modal */}
            <NewEvalModal
                open={modalOpen}
                onClose={handleModalClose}
                onSubmit={handleNewEval}
                scorers={scorers}
            />
        </div>
    );
}
