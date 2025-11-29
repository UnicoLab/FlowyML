import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FlaskConical, ArrowRight, Sparkles, Calendar, Activity, FolderPlus } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';
import { EmptyState } from '../../components/ui/EmptyState';

export function Experiments() {
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedExperiments, setSelectedExperiments] = useState([]);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchExperiments = async () => {
            setLoading(true);
            try {
                const url = selectedProject
                    ? `/api/experiments?project=${encodeURIComponent(selectedProject)}`
                    : '/api/experiments';
                const res = await fetch(url);
                const data = await res.json();
                setExperiments(data.experiments || []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchExperiments();
    }, [selectedProject]);

    const columns = [
        {
            header: (
                <input
                    type="checkbox"
                    checked={selectedExperiments.length === experiments.length && experiments.length > 0}
                    onChange={(e) => {
                        if (e.target.checked) {
                            setSelectedExperiments(experiments.map(e => e.name));
                        } else {
                            setSelectedExperiments([]);
                        }
                    }}
                    className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
            ),
            key: 'select',
            render: (exp) => (
                <input
                    type="checkbox"
                    checked={selectedExperiments.includes(exp.name)}
                    onChange={(e) => {
                        if (e.target.checked) {
                            setSelectedExperiments([...selectedExperiments, exp.name]);
                        } else {
                            setSelectedExperiments(selectedExperiments.filter(n => n !== exp.name));
                        }
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                />
            )
        },
        {
            header: 'Experiment',
            key: 'name',
            sortable: true,
            render: (exp) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
                        <FlaskConical size={16} />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{exp.name}</div>
                        {exp.description && (
                            <div className="text-xs text-slate-500 truncate max-w-[200px]">{exp.description}</div>
                        )}
                    </div>
                </div>
            )
        },
        {
            header: 'Project',
            key: 'project',
            sortable: true,
            render: (exp) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                    {exp.project || '-'}
                </span>
            )
        },
        {
            header: 'Pipeline',
            key: 'pipeline',
            sortable: true,
            render: (exp) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                    {exp.pipeline_name || '-'}
                </span>
            )
        },
        {
            header: 'Runs',
            key: 'run_count',
            sortable: true,
            render: (exp) => (
                <Badge variant="secondary" className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {exp.run_count || 0} runs
                </Badge>
            )
        },
        {
            header: 'Created',
            key: 'created_at',
            sortable: true,
            render: (exp) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Calendar size={14} />
                    {exp.created_at ? format(new Date(exp.created_at), 'MMM d, HH:mm') : '-'}
                </div>
            )
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (exp) => (
                <Link to={`/experiments/${exp.experiment_id}`}>
                    <Button variant="ghost" size="sm" className="text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20">
                        View Details <ArrowRight size={14} className="ml-1" />
                    </Button>
                </Link>
            )
        }
    ];

    const renderGrid = (exp) => (
        <Link to={`/experiments/${exp.experiment_id}`}>
            <Card className="group cursor-pointer hover:border-primary-300 hover:shadow-lg h-full transition-all duration-200 overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-50/50 to-pink-50/50 dark:from-purple-900/10 dark:to-pink-900/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />

                <div className="relative">
                    <div className="flex items-start justify-between mb-4">
                        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl text-purple-600 dark:text-purple-400 group-hover:bg-purple-600 group-hover:text-white transition-all duration-200 group-hover:scale-110">
                            <FlaskConical size={24} />
                        </div>
                        <Badge variant="default" className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30 group-hover:text-purple-700 dark:group-hover:text-purple-300 transition-colors">
                            {exp.run_count || 0} runs
                        </Badge>
                    </div>

                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2 group-hover:text-purple-700 dark:group-hover:text-purple-400 transition-colors">
                        {exp.name}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 line-clamp-2 min-h-[2.5rem]">
                        {exp.description || "No description provided"}
                    </p>

                    <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-700">
                        <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                            <Calendar size={12} />
                            {exp.created_at ? format(new Date(exp.created_at), 'MMM d, yyyy') : '-'}
                        </span>
                        <span className="text-sm font-semibold text-primary-600 group-hover:text-primary-700 dark:text-primary-400 dark:group-hover:text-primary-300 flex items-center gap-1 group-hover:gap-2 transition-all">
                            View <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                        </span>
                    </div>
                </div>
            </Card>
        </Link>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <DataView
                title="Experiments"
                subtitle="Track and compare your ML experiments with detailed metrics and parameters"
                items={experiments}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                actions={
                    <ExperimentProjectSelector
                        selectedExperiments={selectedExperiments}
                        onComplete={() => {
                            window.location.reload();
                        }}
                    />
                }
                emptyState={
                    <EmptyState
                        icon={FlaskConical}
                        title="No experiments yet"
                        description="Start tracking your ML experiments using the Experiment API to compare runs and optimize your models."
                        action={
                            <div className="inline-block px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-mono text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                                <code>from flowy.tracking import Experiment</code>
                            </div>
                        }
                    />
                }
            />
        </div>
    );
}

function ExperimentProjectSelector({ selectedExperiments, onComplete }) {
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
            const updates = selectedExperiments.map(expName =>
                fetch(`/api/experiments/${expName}/project`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_name: projectName })
                })
            );

            await Promise.all(updates);

            const toast = document.createElement('div');
            toast.className = 'fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 bg-green-500 text-white';
            toast.textContent = `Added ${selectedExperiments.length} experiment(s) to project ${projectName}`;
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
                disabled={updating || selectedExperiments.length === 0}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <FolderPlus size={16} />
                {updating ? 'Updating...' : `Add to Project (${selectedExperiments.length})`}
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
