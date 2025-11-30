import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import {
    PlayCircle,
    Calendar,
    Clock,
    CheckCircle,
    XCircle,
    Activity,
    ArrowRight,
    Box,
    FileText,
    Layers,
    X,
    Terminal,
    Cpu
} from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { StatusBadge } from './ui/ExecutionStatus';
import { PipelineGraph } from './PipelineGraph';
import { ProjectSelector } from './ProjectSelector';

export function RunDetailsPanel({ run, onClose }) {
    const [details, setDetails] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('overview'); // overview, steps, artifacts
    const [currentProject, setCurrentProject] = useState(run?.project);

    useEffect(() => {
        if (run) {
            fetchRunDetails();
            setCurrentProject(run.project);
        }
    }, [run]);

    const fetchRunDetails = async () => {
        setLoading(true);
        try {
            const res = await fetchApi(`/api/runs/${run.run_id}`);
            const data = await res.json();
            setDetails(data);
            if (data.project) setCurrentProject(data.project);
        } catch (error) {
            console.error('Failed to fetch run details:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleProjectUpdate = async (newProject) => {
        try {
            await fetchApi(`/api/runs/${run.run_id}/project`, {
                method: 'PUT',
                body: JSON.stringify({ project_name: newProject })
            });
            setCurrentProject(newProject);
        } catch (error) {
            console.error('Failed to update project:', error);
        }
    };

    if (!run) return null;

    const runData = details || run;

    return (
        <div className="h-full flex flex-col bg-white dark:bg-slate-900">
            {/* Header */}
            <div className="p-6 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
                <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl text-blue-600 dark:text-blue-400">
                            <PlayCircle size={24} />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                                    {runData.name || `Run ${runData.run_id?.slice(0, 8)}`}
                                </h2>
                                <StatusBadge status={runData.status} />
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-sm text-slate-500">
                                <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                                    {runData.run_id}
                                </span>
                                <span>•</span>
                                <ProjectSelector
                                    currentProject={currentProject}
                                    onUpdate={handleProjectUpdate}
                                />
                                {runData.pipeline_name && (
                                    <>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <Layers size={12} />
                                            {runData.pipeline_name}
                                        </span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Link to={`/runs/${runData.run_id}`}>
                            <Button variant="outline" size="sm">
                                Full View <ArrowRight size={16} className="ml-1" />
                            </Button>
                        </Link>
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X size={20} className="text-slate-400" />
                        </Button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-4">
                    <StatCard
                        label="Duration"
                        value={runData.duration ? `${runData.duration.toFixed(2)}s` : '-'}
                        icon={Clock}
                        color="blue"
                    />
                    <StatCard
                        label="Started"
                        value={runData.start_time ? format(new Date(runData.start_time), 'MMM d, HH:mm') : '-'}
                        icon={Calendar}
                        color="purple"
                    />
                    <StatCard
                        label="Steps"
                        value={runData.steps ? Object.keys(runData.steps).length : 0}
                        icon={Activity}
                        color="emerald"
                    />
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex flex-col">
                {/* Tabs */}
                <div className="flex items-center gap-1 p-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <TabButton
                        active={activeTab === 'overview'}
                        onClick={() => setActiveTab('overview')}
                        icon={Activity}
                        label="Overview"
                    />
                    <TabButton
                        active={activeTab === 'steps'}
                        onClick={() => setActiveTab('steps')}
                        icon={Layers}
                        label="Steps"
                    />
                    <TabButton
                        active={activeTab === 'artifacts'}
                        onClick={() => setActiveTab('artifacts')}
                        icon={Box}
                        label="Artifacts"
                    />
                </div>

                <div className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-900/50 p-4">
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                        </div>
                    ) : (
                        <>
                            {activeTab === 'overview' && (
                                <div className="space-y-4">
                                    {/* DAG Visualization Preview */}
                                    <Card className="p-0 overflow-hidden h-64 border-slate-200 dark:border-slate-700">
                                        <div className="p-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-center">
                                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Pipeline Graph</h3>
                                        </div>
                                        <div className="h-full bg-slate-50/50">
                                            {runData.dag ? (
                                                <PipelineGraph
                                                    dag={runData.dag}
                                                    steps={runData.steps}
                                                />
                                            ) : (
                                                <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                                                    No graph data available
                                                </div>
                                            )}
                                        </div>
                                    </Card>

                                    {/* Error Display if Failed */}
                                    {runData.status === 'failed' && runData.error && (
                                        <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl p-4">
                                            <h3 className="text-rose-700 dark:text-rose-400 font-semibold flex items-center gap-2 mb-2">
                                                <XCircle size={18} />
                                                Execution Failed
                                            </h3>
                                            <pre className="text-xs font-mono text-rose-600 dark:text-rose-300 whitespace-pre-wrap overflow-x-auto">
                                                {runData.error}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}

                            {activeTab === 'steps' && (
                                <div className="space-y-3">
                                    {runData.steps && Object.entries(runData.steps).map(([stepId, step]) => (
                                        <div key={stepId} className="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700">
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <StatusBadge status={step.success ? 'completed' : step.error ? 'failed' : 'running'} size="sm" />
                                                    <span className="font-medium text-slate-900 dark:text-white">{stepId}</span>
                                                </div>
                                                <span className="text-xs text-slate-500 font-mono">
                                                    {step.duration ? `${step.duration.toFixed(2)}s` : '-'}
                                                </span>
                                            </div>
                                            {step.error && (
                                                <div className="text-xs text-rose-600 bg-rose-50 dark:bg-rose-900/20 p-2 rounded mt-2 font-mono">
                                                    {step.error}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                    {(!runData.steps || Object.keys(runData.steps).length === 0) && (
                                        <div className="text-center py-8 text-slate-500">No steps recorded</div>
                                    )}
                                </div>
                            )}

                            {activeTab === 'artifacts' && (
                                <div className="space-y-3">
                                    {/* This would need actual artifact data structure */}
                                    <div className="text-center py-8 text-slate-500">
                                        <Box size={32} className="mx-auto mb-2 opacity-50" />
                                        <p>Artifacts view not fully implemented in preview</p>
                                        <Link to={`/runs/${runData.run_id}`} className="text-primary-600 hover:underline text-sm mt-2 inline-block">
                                            View in full details page
                                        </Link>
                                    </div>
                                </div>
                            )}
                        </>
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
    };

    return (
        <div className="bg-white dark:bg-slate-800 p-3 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-1">
                <div className={`p-1 rounded-lg ${colorClasses[color]}`}>
                    <Icon size={14} />
                </div>
                <span className="text-xs text-slate-500 font-medium">{label}</span>
            </div>
            <div className="text-sm font-bold text-slate-900 dark:text-white pl-1 truncate" title={value}>
                {value}
            </div>
        </div>
    );
}

function TabButton({ active, onClick, icon: Icon, label }) {
    return (
        <button
            onClick={onClick}
            className={`
                flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                ${active
                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                    : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-700 dark:hover:text-slate-300'
                }
            `}
        >
            <Icon size={16} />
            {label}
        </button>
    );
}
