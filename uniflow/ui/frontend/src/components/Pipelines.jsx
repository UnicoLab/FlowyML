import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, Play, Clock, CheckCircle, XCircle, TrendingUp, Calendar, Activity, ArrowRight, Zap } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { format } from 'date-fns';
import { motion } from 'framer-motion';

export function Pipelines() {
    const [pipelines, setPipelines] = useState([]);
    const [pipelineStats, setPipelineStats] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const pipelinesRes = await fetch('/api/pipelines');
                const pipelinesData = await pipelinesRes.json();

                // Fetch runs to calculate stats per pipeline
                const runsRes = await fetch('/api/runs');
                const runsData = await runsRes.json();

                // Calculate stats for each pipeline
                const stats = {};
                pipelinesData.pipelines.forEach(pipeline => {
                    const pipelineRuns = runsData.runs.filter(r => r.pipeline_name === pipeline);
                    const completedRuns = pipelineRuns.filter(r => r.status === 'completed');
                    const failedRuns = pipelineRuns.filter(r => r.status === 'failed');
                    const avgDuration = pipelineRuns.length > 0
                        ? pipelineRuns.reduce((sum, r) => sum + (r.duration || 0), 0) / pipelineRuns.length
                        : 0;

                    const lastRun = pipelineRuns.length > 0
                        ? pipelineRuns.sort((a, b) => new Date(b.start_time) - new Date(a.start_time))[0]
                        : null;

                    stats[pipeline] = {
                        totalRuns: pipelineRuns.length,
                        completedRuns: completedRuns.length,
                        failedRuns: failedRuns.length,
                        successRate: pipelineRuns.length > 0 ? (completedRuns.length / pipelineRuns.length) * 100 : 0,
                        avgDuration,
                        lastRun
                    };
                });

                setPipelines(pipelinesData.pipelines);
                setPipelineStats(stats);
                setLoading(false);
            } catch (err) {
                console.error(err);
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
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
            className="space-y-6"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-primary-500 to-purple-500 rounded-lg">
                        <Layers className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Pipelines</h2>
                </div>
                <p className="text-slate-500 mt-2">Manage and monitor your ML pipeline definitions</p>
            </motion.div>

            {/* Pipelines Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {pipelines.length > 0 ? (
                    pipelines.map((pipeline, index) => (
                        <PipelineCard
                            key={pipeline}
                            pipeline={pipeline}
                            stats={pipelineStats[pipeline]}
                            index={index}
                        />
                    ))
                ) : (
                    <motion.div variants={item} className="col-span-full">
                        <Card className="p-16 text-center border-dashed border-2">
                            <div className="mx-auto w-20 h-20 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
                                <Layers className="text-slate-400" size={32} />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-2">No pipelines found</h3>
                            <p className="text-slate-500 max-w-md mx-auto">
                                Create your first pipeline by defining steps and running them with Flowy
                            </p>
                        </Card>
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
}

function PipelineCard({ pipeline, stats, index }) {
    const successRate = stats?.successRate || 0;
    const statusColor = successRate >= 80 ? 'emerald' : successRate >= 50 ? 'amber' : 'rose';

    const colorClasses = {
        emerald: {
            bg: 'bg-emerald-50',
            text: 'text-emerald-600',
            border: 'border-emerald-200',
            ring: 'ring-emerald-400'
        },
        amber: {
            bg: 'bg-amber-50',
            text: 'text-amber-600',
            border: 'border-amber-200',
            ring: 'ring-amber-400'
        },
        rose: {
            bg: 'bg-rose-50',
            text: 'text-rose-600',
            border: 'border-rose-200',
            ring: 'ring-rose-400'
        }
    };

    const colors = colorClasses[statusColor];

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
        >
            <Card className="group cursor-pointer hover:shadow-xl hover:border-primary-300 transition-all duration-200 overflow-hidden">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl text-white group-hover:scale-110 transition-transform shadow-lg">
                        <Layers size={24} />
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        {stats?.totalRuns > 0 && (
                            <Badge variant="secondary" className="text-xs bg-slate-100 text-slate-600">
                                {stats.totalRuns} runs
                            </Badge>
                        )}
                        {successRate > 0 && (
                            <div className={`text-xs font-semibold px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                                {successRate.toFixed(0)}% success
                            </div>
                        )}
                    </div>
                </div>

                {/* Pipeline Name */}
                <h3 className="text-lg font-bold text-slate-900 mb-3 group-hover:text-primary-600 transition-colors">
                    {pipeline}
                </h3>

                {/* Stats Grid */}
                {stats && (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <StatItem
                            icon={<Activity size={14} />}
                            label="Total"
                            value={stats.totalRuns}
                            color="blue"
                        />
                        <StatItem
                            icon={<CheckCircle size={14} />}
                            label="Success"
                            value={stats.completedRuns}
                            color="emerald"
                        />
                        <StatItem
                            icon={<Clock size={14} />}
                            label="Avg Time"
                            value={stats.avgDuration > 0 ? `${stats.avgDuration.toFixed(1)}s` : '-'}
                            color="purple"
                        />
                        <StatItem
                            icon={<XCircle size={14} />}
                            label="Failed"
                            value={stats.failedRuns}
                            color="rose"
                        />
                    </div>
                )}

                {/* Last Run */}
                {stats?.lastRun && (
                    <div className="pt-4 border-t border-slate-100">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500 flex items-center gap-1">
                                <Calendar size={12} />
                                Last run
                            </span>
                            <span className="text-slate-700 font-medium">
                                {format(new Date(stats.lastRun.start_time), 'MMM d, HH:mm')}
                            </span>
                        </div>
                    </div>
                )}

                {/* View Runs Link */}
                <Link
                    to={`/runs?pipeline=${encodeURIComponent(pipeline)}`}
                    className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-slate-50 hover:bg-primary-50 text-slate-700 hover:text-primary-600 rounded-lg transition-all group-hover:bg-primary-50"
                >
                    <span className="text-sm font-semibold">View Runs</span>
                    <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </Link>
            </Card>
        </motion.div>
    );
}

function StatItem({ icon, label, value, color }) {
    const colorClasses = {
        blue: 'bg-blue-50 text-blue-600',
        emerald: 'bg-emerald-50 text-emerald-600',
        purple: 'bg-purple-50 text-purple-600',
        rose: 'bg-rose-50 text-rose-600'
    };

    return (
        <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded ${colorClasses[color]}`}>
                {icon}
            </div>
            <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-sm font-bold text-slate-900">{value}</p>
            </div>
        </div>
    );
}
