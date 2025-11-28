import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import { Link } from 'react-router-dom';
import { Play, Clock, CheckCircle, XCircle, Loader, Calendar, TrendingUp, Activity, ArrowRight } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import { DataView } from './ui/DataView';
import { useProject } from '../contexts/ProjectContext';

export function Runs() {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, completed, failed, running
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchRuns = async () => {
            setLoading(true);
            try {
                const url = selectedProject
                    ? `/api/runs?project=${encodeURIComponent(selectedProject)}`
                    : '/api/runs';
                const res = await fetchApi(url);
                const data = await res.json();
                setRuns(data.runs || []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchRuns();
    }, [selectedProject]);

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

    const columns = [
        {
            header: 'Status',
            key: 'status',
            sortable: true,
            render: (run) => {
                const statusConfig = {
                    completed: { icon: <CheckCircle size={16} />, color: 'text-emerald-500', bg: 'bg-emerald-50' },
                    failed: { icon: <XCircle size={16} />, color: 'text-rose-500', bg: 'bg-rose-50' },
                    running: { icon: <Loader size={16} className="animate-spin" />, color: 'text-amber-500', bg: 'bg-amber-50' }
                };
                const config = statusConfig[run.status] || statusConfig.completed;
                return (
                    <div className={`flex items-center gap-2 px-2 py-1 rounded-md w-fit ${config.bg} ${config.color}`}>
                        {config.icon}
                        <span className="capitalize text-xs font-medium">{run.status}</span>
                    </div>
                );
            }
        },
        {
            header: 'Pipeline',
            key: 'pipeline_name',
            sortable: true,
            render: (run) => (
                <span className="font-medium text-slate-900 dark:text-white">{run.pipeline_name}</span>
            )
        },
        {
            header: 'Run ID',
            key: 'run_id',
            render: (run) => (
                <span className="font-mono text-xs bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded text-slate-600 dark:text-slate-300">
                    {run.run_id.substring(0, 8)}...
                </span>
            )
        },
        {
            header: 'Start Time',
            key: 'start_time',
            sortable: true,
            render: (run) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Calendar size={14} />
                    {run.start_time ? format(new Date(run.start_time), 'MMM d, HH:mm:ss') : '-'}
                </div>
            )
        },
        {
            header: 'Duration',
            key: 'duration',
            sortable: true,
            render: (run) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Clock size={14} />
                    {run.duration ? `${run.duration.toFixed(2)}s` : '-'}
                </div>
            )
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (run) => (
                <Link
                    to={`/runs/${run.run_id}`}
                    className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
                >
                    Details <ArrowRight size={14} />
                </Link>
            )
        }
    ];

    const renderGrid = (run) => {
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
            <Link to={`/runs/${run.run_id}`}>
                <Card className={`group hover:shadow-lg transition-all duration-200 border-l-4 ${config.border} hover:border-l-primary-400 h-full`}>
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
                                {config.icon}
                            </div>
                            <div>
                                <h3 className="font-bold text-slate-900 dark:text-white truncate max-w-[150px]" title={run.pipeline_name}>
                                    {run.pipeline_name}
                                </h3>
                                <div className="text-xs text-slate-500 font-mono">
                                    {run.run_id.substring(0, 8)}
                                </div>
                            </div>
                        </div>
                        <Badge variant={config.badge} className="text-xs uppercase tracking-wide">
                            {run.status}
                        </Badge>
                    </div>

                    <div className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
                        <div className="flex items-center justify-between">
                            <span className="flex items-center gap-2"><Calendar size={14} /> Started</span>
                            <span>{run.start_time ? format(new Date(run.start_time), 'MMM d, HH:mm') : '-'}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="flex items-center gap-2"><Clock size={14} /> Duration</span>
                            <span>{run.duration ? `${run.duration.toFixed(2)}s` : '-'}</span>
                        </div>
                    </div>

                    {/* Steps Progress */}
                    {run.steps && (
                        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-slate-500">Progress</span>
                                <span className="font-medium text-slate-900 dark:text-white">
                                    {Object.values(run.steps).filter(s => s.success).length} / {Object.keys(run.steps).length}
                                </span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${config.color.replace('text-', 'bg-')} transition-all duration-300`}
                                    style={{
                                        width: `${(Object.values(run.steps).filter(s => s.success).length / Object.keys(run.steps).length) * 100}%`
                                    }}
                                />
                            </div>
                        </div>
                    )}
                </Card>
            </Link>
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            </div>

            <DataView
                title="Pipeline Runs"
                subtitle="Monitor and track all your pipeline executions"
                items={filteredRuns}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                initialView="table" // Default to table for runs as it's usually more useful
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Activity className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No runs found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            {filter === 'all'
                                ? 'Run a pipeline to see it here'
                                : `No ${filter} runs found. Try a different filter.`
                            }
                        </p>
                    </div>
                }
            />
        </div>
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
                    <p className="text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
                </div>
                <div className={`p-3 rounded-xl ${active ? colors.activeBg : colors.bg} ${colors.text}`}>
                    {icon}
                </div>
            </div>
        </Card>
    );
}
