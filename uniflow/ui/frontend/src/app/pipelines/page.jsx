import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { Link } from 'react-router-dom';
import { Layers, Play, Clock, CheckCircle, XCircle, TrendingUp, Calendar, Activity, ArrowRight, Zap, FolderPlus } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { format } from 'date-fns';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';

export function Pipelines() {
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPipelines, setSelectedPipelines] = useState([]);
    const { selectedProject } = useProject();

    const fetchData = async () => {
        setLoading(true);
        try {
            const pipelinesUrl = selectedProject
                ? `/api/pipelines?project=${encodeURIComponent(selectedProject)}`
                : '/api/pipelines';
            const runsUrl = selectedProject
                ? `/api/runs?project=${encodeURIComponent(selectedProject)}`
                : '/api/runs';

            const pipelinesRes = await fetchApi(pipelinesUrl);
            const pipelinesData = await pipelinesRes.json();

            // Fetch runs to calculate stats per pipeline
            const runsRes = await fetchApi(runsUrl);
            const runsData = await runsRes.json();

            // Calculate stats for each pipeline
            const pipelinesWithStats = pipelinesData.pipelines.map(pipeline => {
                const pipelineRuns = runsData.runs.filter(r => r.pipeline_name === pipeline);
                const completedRuns = pipelineRuns.filter(r => r.status === 'completed');
                const failedRuns = pipelineRuns.filter(r => r.status === 'failed');
                const avgDuration = pipelineRuns.length > 0
                    ? pipelineRuns.reduce((sum, r) => sum + (r.duration || 0), 0) / pipelineRuns.length
                    : 0;

                const lastRun = pipelineRuns.length > 0
                    ? pipelineRuns.sort((a, b) => new Date(b.start_time) - new Date(a.start_time))[0]
                    : null;

                // Get most common project from runs
                const projects = pipelineRuns.map(r => r.project).filter(Boolean);
                const projectCounts = {};
                projects.forEach(p => projectCounts[p] = (projectCounts[p] || 0) + 1);
                const mostCommonProject = Object.keys(projectCounts).sort((a, b) => projectCounts[b] - projectCounts[a])[0] || null;

                return {
                    name: pipeline,
                    totalRuns: pipelineRuns.length,
                    completedRuns: completedRuns.length,
                    failedRuns: failedRuns.length,
                    successRate: pipelineRuns.length > 0 ? (completedRuns.length / pipelineRuns.length) * 100 : 0,
                    avgDuration,
                    lastRun,
                    project: mostCommonProject
                };
            });

            setPipelines(pipelinesWithStats);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedProject]);

    const columns = [
        {
            header: (
                <input
                    type="checkbox"
                    checked={selectedPipelines.length === pipelines.length && pipelines.length > 0}
                    onChange={(e) => {
                        if (e.target.checked) {
                            setSelectedPipelines(pipelines.map(p => p.name));
                        } else {
                            setSelectedPipelines([]);
                        }
                    }}
                    className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
            ),
            key: 'select',
            render: (item) => (
                <input
                    type="checkbox"
                    checked={selectedPipelines.includes(item.name)}
                    onChange={(e) => {
                        if (e.target.checked) {
                            setSelectedPipelines([...selectedPipelines, item.name]);
                        } else {
                            setSelectedPipelines(selectedPipelines.filter(n => n !== item.name));
                        }
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
            )
        },
        {
            header: 'Pipeline',
            key: 'name',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-primary-500 to-purple-500 rounded-lg text-white">
                        <Layers size={16} />
                    </div>
                    <span className="font-medium text-slate-900 dark:text-white">{item.name}</span>
                </div>
            )
        },
        {
            header: 'Project',
            key: 'project',
            render: (item) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                    {item.project || '-'}
                </span>
            )
        },
        {
            header: 'Success Rate',
            key: 'successRate',
            sortable: true,
            render: (item) => {
                const rate = item.successRate;
                const color = rate >= 80 ? 'text-emerald-600 bg-emerald-50' : rate >= 50 ? 'text-amber-600 bg-amber-50' : 'text-rose-600 bg-rose-50';
                return (
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${color}`}>
                        {rate.toFixed(0)}%
                    </span>
                );
            }
        },
        {
            header: 'Total Runs',
            key: 'totalRuns',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Activity size={14} />
                    {item.totalRuns}
                </div>
            )
        },
        {
            header: 'Avg Duration',
            key: 'avgDuration',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Clock size={14} />
                    {item.avgDuration > 0 ? `${item.avgDuration.toFixed(1)}s` : '-'}
                </div>
            )
        },
        {
            header: 'Last Run',
            key: 'lastRun',
            render: (item) => item.lastRun ? (
                <div className="text-sm text-slate-500">
                    {format(new Date(item.lastRun.start_time), 'MMM d, HH:mm')}
                </div>
            ) : '-'
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (item) => (
                <Link
                    to={`/runs?pipeline=${encodeURIComponent(item.name)}`}
                    className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
                >
                    View Runs <ArrowRight size={14} />
                </Link>
            )
        }
    ];

    const renderGrid = (item) => {
        const successRate = item.successRate || 0;
        const statusColor = successRate >= 80 ? 'emerald' : successRate >= 50 ? 'amber' : 'rose';

        const colorClasses = {
            emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
            amber: { bg: 'bg-amber-50', text: 'text-amber-600' },
            rose: { bg: 'bg-rose-50', text: 'text-rose-600' }
        };
        const colors = colorClasses[statusColor];

        return (
            <Card className="group cursor-pointer hover:shadow-xl hover:border-primary-300 transition-all duration-200 overflow-hidden h-full">
                <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl text-white group-hover:scale-110 transition-transform shadow-lg">
                        <Layers size={24} />
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        {item.totalRuns > 0 && (
                            <Badge variant="secondary" className="text-xs bg-slate-100 text-slate-600">
                                {item.totalRuns} runs
                            </Badge>
                        )}
                        {successRate > 0 && (
                            <div className={`text-xs font-semibold px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                                {successRate.toFixed(0)}% success
                            </div>
                        )}
                    </div>
                </div>

                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-3 group-hover:text-primary-600 transition-colors">
                    {item.name}
                </h3>

                <div className="grid grid-cols-2 gap-3 mb-4">
                    <StatItem icon={<Activity size={14} />} label="Total" value={item.totalRuns} color="blue" />
                    <StatItem icon={<CheckCircle size={14} />} label="Success" value={item.completedRuns} color="emerald" />
                    <StatItem icon={<Clock size={14} />} label="Avg Time" value={item.avgDuration > 0 ? `${item.avgDuration.toFixed(1)}s` : '-'} color="purple" />
                    <StatItem icon={<XCircle size={14} />} label="Failed" value={item.failedRuns} color="rose" />
                </div>

                {item.lastRun && (
                    <div className="pt-4 border-t border-slate-100 dark:border-slate-700">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500 flex items-center gap-1">
                                <Calendar size={12} />
                                Last run
                            </span>
                            <span className="text-slate-700 dark:text-slate-300 font-medium">
                                {format(new Date(item.lastRun.start_time), 'MMM d, HH:mm')}
                            </span>
                        </div>
                    </div>
                )}

                <Link
                    to={`/runs?pipeline=${encodeURIComponent(item.name)}`}
                    className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-slate-50 dark:bg-slate-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-slate-700 dark:text-slate-200 hover:text-primary-600 rounded-lg transition-all group-hover:bg-primary-50"
                >
                    <span className="text-sm font-semibold">View Runs</span>
                    <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </Link>
            </Card>
        );
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <DataView
                title="Pipelines"
                subtitle="View and manage your ML pipelines"
                items={pipelines}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                actions={
                    <PipelineProjectSelector
                        selectedPipelines={selectedPipelines}
                        onComplete={() => {
                            fetchData();
                            setSelectedPipelines([]);
                        }}
                    />
                }
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Layers className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No pipelines found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            Create your first pipeline by defining steps and running them with UniFlow
                        </p>
                    </div >
                }
            />
        </div >
    );
}



function ProjectSelector({ onSelect }) {
    const [isOpen, setIsOpen] = useState(false);
    const [projects, setProjects] = useState([]);

    useEffect(() => {
        if (isOpen) {
            fetch('/api/projects/')
                .then(res => res.json())
                .then(data => setProjects(data))
                .catch(err => console.error('Failed to load projects:', err));
        }
    }, [isOpen]);

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
                <FolderPlus size={16} />
                Add to Project
            </button>

            {isOpen && (
                <>
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-20 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
                        <div className="p-2 border-b border-slate-100 dark:border-slate-700">
                            <span className="text-xs font-semibold text-slate-500 px-2">Select Project</span>
                        </div>
                        <div className="max-h-64 overflow-y-auto p-1">
                            {projects.length > 0 ? (
                                projects.map(p => (
                                    <button
                                        key={p.name}
                                        onClick={() => {
                                            onSelect(p.name);
                                            setIsOpen(false);
                                        }}
                                        className="w-full text-left px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                    >
                                        {p.name}
                                    </button>
                                ))
                            ) : (
                                <div className="px-3 py-2 text-sm text-slate-400 italic">No projects found</div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
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
                <p className="text-sm font-bold text-slate-900 dark:text-white">{value}</p>
            </div>
        </div>
    );
}

function PipelineProjectSelector({ selectedPipelines, onComplete }) {
    const [isOpen, setIsOpen] = useState(false);
    const [projects, setProjects] = useState([]);
    const [updating, setUpdating] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetch('/api/projects/')
                .then(res => res.json())
                .then(data => setProjects(data))
                .catch(err => console.error('Failed to load projects:', err));
        }
    }, [isOpen]);

    const handleSelectProject = async (projectName) => {
        setUpdating(true);
        try {
            const updates = selectedPipelines.map(pipelineName =>
                fetch(`/api/pipelines/${pipelineName}/project`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_name: projectName })
                })
            );

            await Promise.all(updates);

            const toast = document.createElement('div');
            toast.className = 'fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 bg-green-500 text-white';
            toast.textContent = `Added ${selectedPipelines.length} pipeline(s) to project ${projectName}`;
            document.body.appendChild(toast);
            setTimeout(() => document.body.removeChild(toast), 3000);

            setIsOpen(false);
            if (onComplete) onComplete();
        } catch (error) {
            console.error('Failed to update projects:', error);
        } finally {
            setUpdating(false);
        }
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={updating || selectedPipelines.length === 0}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <FolderPlus size={16} />
                {updating ? 'Updating...' : `Add to Project (${selectedPipelines.length})`}
            </button>

            {isOpen && (
                <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
                    <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-20">
                        <div className="p-2 border-b border-slate-100 dark:border-slate-700">
                            <span className="text-xs font-semibold text-slate-500 px-2">Select Project</span>
                        </div>
                        <div className="max-h-64 overflow-y-auto p-1">
                            {projects.length > 0 ? (
                                projects.map(p => (
                                    <button
                                        key={p.name}
                                        onClick={() => handleSelectProject(p.name)}
                                        disabled={updating}
                                        className="w-full text-left px-3 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        {p.name}
                                    </button>
                                ))
                            ) : (
                                <div className="px-3 py-2 text-sm text-slate-400 italic">No projects found</div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
