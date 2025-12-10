import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../utils/api';
import { useParams, Link } from 'react-router-dom';
import { Activity, ChevronRight, FlaskConical, TrendingUp, Calendar, BarChart3 } from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { format } from 'date-fns';
import { motion } from 'framer-motion';

export function ExperimentDetails() {
    const { experimentId } = useParams();
    const [experiment, setExperiment] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchApi(`/api/experiments/${experimentId}`)
            .then(res => res.json())
            .then(data => {
                setExperiment(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [experimentId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (!experiment) {
        return (
            <div className="p-8 text-center">
                <p className="text-slate-500">Experiment not found</p>
            </div>
        );
    }

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-8"
        >
            {/* Header */}
            <motion.div variants={item} className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                    <Link to="/experiments" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
                        Experiments
                    </Link>
                    <ChevronRight size={14} className="text-slate-300" />
                    <span className="text-sm text-slate-900 font-medium">{experiment.name}</span>
                </div>

                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl shadow-lg">
                            <FlaskConical className="text-white" size={28} />
                        </div>
                        <div>
                            <h2 className="text-3xl font-bold text-slate-900 tracking-tight">{experiment.name}</h2>
                            <p className="text-slate-500 mt-1">{experiment.description || 'No description'}</p>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Stats */}
            <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatsCard
                    icon={<Activity size={24} />}
                    label="Total Runs"
                    value={experiment.runs?.length || 0}
                    color="blue"
                />
                <StatsCard
                    icon={<TrendingUp size={24} />}
                    label="Best Performance"
                    value={getBestMetric(experiment.runs)}
                    color="emerald"
                />
                <StatsCard
                    icon={<Calendar size={24} />}
                    label="Last Run"
                    value={getLastRunDate(experiment.runs)}
                    color="purple"
                />
            </motion.div>

            {/* Runs Comparison Table */}
            <motion.div variants={item}>
                <div className="flex items-center gap-2 mb-6">
                    <BarChart3 className="text-primary-500" size={24} />
                    <h3 className="text-xl font-bold text-slate-900">Runs Comparison</h3>
                </div>

                {experiment.runs && experiment.runs.length > 0 ? (
                    <Card className="p-0 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-gradient-to-r from-slate-50 to-slate-100/50 border-b border-slate-200">
                                    <tr>
                                        <th className="px-6 py-4 font-semibold text-xs text-slate-600 uppercase tracking-wider">Run ID</th>
                                        <th className="px-6 py-4 font-semibold text-xs text-slate-600 uppercase tracking-wider">Date</th>
                                        <th className="px-6 py-4 font-semibold text-xs text-slate-600 uppercase tracking-wider">Metrics</th>
                                        <th className="px-6 py-4 font-semibold text-xs text-slate-600 uppercase tracking-wider">Parameters</th>
                                        <th className="px-6 py-4 font-semibold text-xs text-slate-600 uppercase tracking-wider"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {experiment.runs.map((run, index) => (
                                        <motion.tr
                                            key={run.run_id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.05 }}
                                            className="hover:bg-slate-50/70 transition-colors group"
                                        >
                                            <td className="px-6 py-4 font-mono text-sm text-slate-700 font-medium">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 rounded-full bg-primary-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                    {run.run_id?.substring(0, 12) || 'N/A'}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-slate-500">
                                                {run.timestamp ? format(new Date(run.timestamp), 'MMM d, HH:mm:ss') : '-'}
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(run.metrics || {}).map(([k, v]) => (
                                                        <Badge key={k} variant="outline" className="font-mono text-xs bg-blue-50 text-blue-700 border-blue-200">
                                                            {k}: {typeof v === 'number' ? v.toFixed(4) : v}
                                                        </Badge>
                                                    ))}
                                                    {Object.keys(run.metrics || {}).length === 0 && (
                                                        <span className="text-xs text-slate-400 italic">No metrics</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(run.parameters || {}).map(([k, v]) => (
                                                        <span key={k} className="text-xs text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md font-medium">
                                                            {k}={String(v)}
                                                        </span>
                                                    ))}
                                                    {Object.keys(run.parameters || {}).length === 0 && (
                                                        <span className="text-xs text-slate-400 italic">No params</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <Link to={`/runs/${run.run_id}`}>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                                                    >
                                                        View Run
                                                    </Button>
                                                </Link>
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                ) : (
                    <Card className="p-12 text-center border-dashed">
                        <p className="text-slate-500">No runs recorded for this experiment yet.</p>
                    </Card>
                )}
            </motion.div>
        </motion.div>
    );
}

function StatsCard({ icon, label, value, color }) {
    const colorClasses = {
        blue: "bg-blue-50 text-blue-600",
        purple: "bg-purple-50 text-purple-600",
        emerald: "bg-emerald-50 text-emerald-600",
    };

    return (
        <Card className="hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
                    {icon}
                </div>
                <div>
                    <p className="text-sm text-slate-500 font-medium">{label}</p>
                    <p className="text-2xl font-bold text-slate-900">{value}</p>
                </div>
            </div>
        </Card>
    );
}

function getBestMetric(runs) {
    if (!runs || runs.length === 0) return '-';

    // Try to find a common metric like accuracy, f1_score, etc.
    const metricKeys = ['accuracy', 'f1_score', 'precision', 'recall'];

    for (const key of metricKeys) {
        const values = runs
            .map(r => r.metrics?.[key])
            .filter(v => typeof v === 'number');

        if (values.length > 0) {
            const best = Math.max(...values);
            return `${best.toFixed(4)} (${key})`;
        }
    }

    return 'N/A';
}

function getLastRunDate(runs) {
    if (!runs || runs.length === 0) return '-';

    const sorted = [...runs].sort((a, b) => {
        const dateA = a.timestamp ? new Date(a.timestamp) : new Date(0);
        const dateB = b.timestamp ? new Date(b.timestamp) : new Date(0);
        return dateB - dateA;
    });

    return sorted[0]?.timestamp
        ? format(new Date(sorted[0].timestamp), 'MMM d, HH:mm')
        : '-';
}
