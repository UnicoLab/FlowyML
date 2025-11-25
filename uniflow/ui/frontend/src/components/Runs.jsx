import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, Clock, CheckCircle, XCircle, Loader, Calendar, TrendingUp, Activity } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { format } from 'date-fns';
import { motion } from 'framer-motion';

export function Runs() {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, completed, failed, running

    useEffect(() => {
        fetch('/api/runs')
            .then(res => res.json())
            .then(data => {
                setRuns(data.runs || []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const filteredRuns = runs.filter(run => {
        if (filter === 'all') return true;
        return run.status === filter;
    });

    const stats = {
        total: runs.length,
        completed: runs.filter(r => r.status === 'completed').length,
        failed: runs.filter(r => r.status === 'failed').length,
        running: runs.filter(r => r.status === 'running').length,
    };

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.05
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-8"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg">
                        <Activity className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Pipeline Runs</h2>
                </div>
                <p className="text-slate-500 mt-2">Monitor and track all your pipeline executions</p>
            </motion.div>

            {/* Stats Cards */}
            <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatsCard
                    label="Total Runs"
                    value={stats.total}
                    icon={<Activity size={20} />}
                    color="slate"
                    active={filter === 'all'}
                    onClick={() => setFilter('all')}
                />
                <StatsCard
                    label="Completed"
                    value={stats.completed}
                    icon={<CheckCircle size={20} />}
                    color="emerald"
                    active={filter === 'completed'}
                    onClick={() => setFilter('completed')}
                />
                <StatsCard
                    label="Failed"
                    value={stats.failed}
                    icon={<XCircle size={20} />}
                    color="rose"
                    active={filter === 'failed'}
                    onClick={() => setFilter('failed')}
                />
                <StatsCard
                    label="Running"
                    value={stats.running}
                    icon={<Loader size={20} />}
                    color="amber"
                    active={filter === 'running'}
                    onClick={() => setFilter('running')}
                />
            </motion.div>

            {/* Runs List */}
            <motion.div variants={item} className="space-y-3">
                {filteredRuns.length > 0 ? (
                    filteredRuns.map((run, index) => (
                        <RunCard key={run.run_id} run={run} index={index} />
                    ))
                ) : (
                    <Card className="p-16 text-center border-dashed border-2">
                        <div className="mx-auto w-20 h-20 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
                            <Activity className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">No runs found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            {filter === 'all'
                                ? 'Run a pipeline to see it here'
                                : `No ${filter} runs found. Try a different filter.`
                            }
                        </p>
                    </Card>
                )}
            </motion.div>
        </motion.div>
    );
}

function StatsCard({ label, value, icon, color, active, onClick }) {
    const colorClasses = {
        slate: {
            bg: "bg-slate-50",
            text: "text-slate-600",
            border: "border-slate-200",
            activeBg: "bg-slate-100",
            activeBorder: "border-slate-300"
        },
        emerald: {
            bg: "bg-emerald-50",
            text: "text-emerald-600",
            border: "border-emerald-200",
            activeBg: "bg-emerald-100",
            activeBorder: "border-emerald-300"
        },
        rose: {
            bg: "bg-rose-50",
            text: "text-rose-600",
            border: "border-rose-200",
            activeBg: "bg-rose-100",
            activeBorder: "border-rose-300"
        },
        amber: {
            bg: "bg-amber-50",
            text: "text-amber-600",
            border: "border-amber-200",
            activeBg: "bg-amber-100",
            activeBorder: "border-amber-300"
        }
    };

    const colors = colorClasses[color];

    return (
        <Card
            className={`cursor-pointer transition-all duration-200 hover:shadow-md border-2 ${active ? colors.activeBorder : 'border-transparent'
                }`}
            onClick={onClick}
        >
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-slate-500 font-medium mb-1">{label}</p>
                    <p className="text-3xl font-bold text-slate-900">{value}</p>
                </div>
                <div className={`p-3 rounded-xl ${active ? colors.activeBg : colors.bg} ${colors.text}`}>
                    {icon}
                </div>
            </div>
        </Card>
    );
}

function RunCard({ run, index }) {
    const statusConfig = {
        completed: {
            icon: <CheckCircle size={20} />,
            color: 'text-emerald-500',
            bg: 'bg-emerald-50',
            border: 'border-emerald-200',
            badge: 'success'
        },
        failed: {
            icon: <XCircle size={20} />,
            color: 'text-rose-500',
            bg: 'bg-rose-50',
            border: 'border-rose-200',
            badge: 'danger'
        },
        running: {
            icon: <Loader size={20} className="animate-spin" />,
            color: 'text-amber-500',
            bg: 'bg-amber-50',
            border: 'border-amber-200',
            badge: 'warning'
        }
    };

    const config = statusConfig[run.status] || statusConfig.completed;

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
        >
            <Link to={`/runs/${run.run_id}`}>
                <Card className={`group hover:shadow-lg transition-all duration-200 border-l-4 ${config.border} hover:border-l-primary-400`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                            {/* Status Icon */}
                            <div className={`p-3 rounded-xl ${config.bg} ${config.color} group-hover:scale-110 transition-transform`}>
                                {config.icon}
                            </div>

                            {/* Run Info */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-1">
                                    <h3 className="text-lg font-bold text-slate-900 truncate">
                                        {run.pipeline_name}
                                    </h3>
                                    <Badge variant={config.badge} className="text-xs uppercase tracking-wide">
                                        {run.status}
                                    </Badge>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-slate-500">
                                    <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">
                                        {run.run_id.substring(0, 12)}
                                    </span>
                                    {run.start_time && (
                                        <span className="flex items-center gap-1">
                                            <Calendar size={14} />
                                            {format(new Date(run.start_time), 'MMM d, HH:mm:ss')}
                                        </span>
                                    )}
                                    {run.duration && (
                                        <span className="flex items-center gap-1">
                                            <Clock size={14} />
                                            {run.duration.toFixed(2)}s
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Steps Progress */}
                        {run.steps && (
                            <div className="hidden md:flex items-center gap-2 px-4">
                                <div className="text-right">
                                    <p className="text-xs text-slate-500 font-medium">Steps</p>
                                    <p className="text-sm font-bold text-slate-900">
                                        {Object.values(run.steps).filter(s => s.success).length} / {Object.keys(run.steps).length}
                                    </p>
                                </div>
                                <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${config.color.replace('text-', 'bg-')} transition-all duration-300`}
                                        style={{
                                            width: `${(Object.values(run.steps).filter(s => s.success).length / Object.keys(run.steps).length) * 100}%`
                                        }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Arrow */}
                        <div className="ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Play size={20} className="text-primary-400" />
                        </div>
                    </div>
                </Card>
            </Link>
        </motion.div>
    );
}
