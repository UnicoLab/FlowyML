import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import {
    Layers,
    Calendar,
    Activity,
    Clock,
    CheckCircle,
    XCircle,
    PlayCircle,
    ArrowRight,
    MoreHorizontal,
    Download,
    Trash2,
    X,
    TrendingUp,
    Zap
} from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { StatusBadge } from './ui/ExecutionStatus';
import { ProjectSelector } from './ProjectSelector';
import { useToast } from '../contexts/ToastContext';

export function PipelineDetailsPanel({ pipeline, onClose, onProjectUpdate }) {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(false);
    const [currentProject, setCurrentProject] = useState(pipeline?.project);
    const toast = useToast();

    useEffect(() => {
        if (pipeline) {
            fetchRuns();
            setCurrentProject(pipeline.project);
        }
    }, [pipeline]);

    const fetchRuns = async () => {
        setLoading(true);
        try {
            const url = `/api/runs?pipeline=${encodeURIComponent(pipeline.name)}&limit=50`;
            const res = await fetchApi(url);
            const data = await res.json();
            setRuns(data.runs || []);
        } catch (error) {
            console.error('Failed to fetch runs:', error);
            toast.error(`Failed to load pipeline runs: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleProjectUpdate = async (newProject) => {
        try {
            await fetchApi(`/api/pipelines/${pipeline.name}/project`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ project_name: newProject })
            });
            setCurrentProject(newProject);
            toast.success(`Pipeline assigned to project: ${newProject}`);
            // Trigger parent component refresh to update the pipelines list
            if (onProjectUpdate) {
                onProjectUpdate();
            }
        } catch (error) {
            console.error('Failed to update project:', error);
            toast.error(`Failed to update project: ${error.message}`);
        }
    };

    if (!pipeline) return null;

    const stats = {
        total: runs.length,
        success: runs.filter(r => r.status === 'completed').length,
        failed: runs.filter(r => r.status === 'failed').length,
        avgDuration: runs.length > 0
            ? runs.reduce((acc, r) => acc + (r.duration || 0), 0) / runs.length
            : 0
    };

    const successRate = stats.total > 0 ? (stats.success / stats.total) * 100 : 0;

    return (
        <div className="h-full flex flex-col bg-white dark:bg-slate-900">
            {/* Header */}
            <div className="p-6 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
                <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl text-white shadow-lg">
                            <Layers size={24} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                                {pipeline.name}
                            </h2>
                            <div className="flex items-center gap-2 mt-1 text-sm text-slate-500">
                                <ProjectSelector
                                    currentProject={currentProject}
                                    onUpdate={handleProjectUpdate}
                                />
                                {pipeline.version && (
                                    <>
                                        <span>•</span>
                                        <Badge variant="secondary" className="text-xs">v{pipeline.version}</Badge>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X size={20} className="text-slate-400" />
                        </Button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-4 gap-4">
                    <StatCard
                        label="Total Runs"
                        value={stats.total}
                        icon={Activity}
                        color="blue"
                    />
                    <StatCard
                        label="Success Rate"
                        value={`${Math.round(successRate)}%`}
                        icon={CheckCircle}
                        color={successRate >= 80 ? 'emerald' : successRate >= 50 ? 'amber' : 'rose'}
                    />
                    <StatCard
                        label="Avg Duration"
                        value={`${stats.avgDuration.toFixed(1)}s`}
                        icon={Clock}
                        color="purple"
                    />
                    <StatCard
                        label="Failed"
                        value={stats.failed}
                        icon={XCircle}
                        color="rose"
                    />
                </div>
            </div>

            {/* Content - Runs List */}
            <div className="flex-1 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900">
                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <PlayCircle size={18} className="text-slate-400" />
                        Recent Executions
                    </h3>
                    <Link to={`/runs?pipeline=${encodeURIComponent(pipeline.name)}`}>
                        <Button variant="ghost" size="sm" className="text-primary-600">
                            View All Runs <ArrowRight size={16} className="ml-1" />
                        </Button>
                    </Link>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50 dark:bg-slate-900/50">
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                        </div>
                    ) : runs.length === 0 ? (
                        <div className="text-center py-12 text-slate-500">
                            No runs found for this pipeline
                        </div>
                    ) : (
                        runs.map(run => (
                            <Link key={run.run_id} to={`/runs/${run.run_id}`}>
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 transition-all group"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <StatusBadge status={run.status} />
                                            <div>
                                                <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                                    {run.name || `Run ${run.run_id.slice(0, 8)}`}
                                                    <span className="text-xs font-mono text-slate-400">#{run.run_id.slice(0, 6)}</span>
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                                                    <span className="flex items-center gap-1">
                                                        <Calendar size={12} />
                                                        {format(new Date(run.created || run.start_time), 'MMM d, HH:mm')}
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <Clock size={12} />
                                                        {run.duration ? `${run.duration.toFixed(1)}s` : '-'}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <ArrowRight size={16} className="text-slate-300 group-hover:text-primary-500 transition-colors" />
                                    </div>
                                </motion.div>
                            </Link>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value, icon: Icon, color }) {
    const colorClasses = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
        purple: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20',
    };

    return (
        <div className="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-1">
                <div className={`p-1 rounded-lg ${colorClasses[color] || colorClasses.blue}`}>
                    <Icon size={14} />
                </div>
                <span className="text-xs text-slate-500 font-medium">{label}</span>
            </div>
            <div className="text-lg font-bold text-slate-900 dark:text-white pl-1">
                {value}
            </div>
        </div>
    );
}
