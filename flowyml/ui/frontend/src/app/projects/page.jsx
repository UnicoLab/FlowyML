import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import { Link } from 'react-router-dom';
import { Folder, Plus, Trash2, Activity, Database, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { DataView } from '../../components/ui/DataView';
import { Button } from '../../components/ui/Button';
import { useProject } from '../../contexts/ProjectContext';

export function Projects() {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newProjectName, setNewProjectName] = useState('');
    const [newProjectDesc, setNewProjectDesc] = useState('');
    const [projectStats, setProjectStats] = useState({});
    const { setSelectedProject } = useProject();

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const response = await fetchApi('/api/projects/');
            const data = await response.json();
            // setProjects(data); // This line will be replaced/modified

            // Fetch stats for each project
            const projectsList = Array.isArray(data) ? data : (data.projects || []);
            const projectsWithStats = await Promise.all(projectsList.map(async (project) => {
                try {
                    // Fetch runs for this project
                    const runsRes = await fetch(`/api/runs?project=${encodeURIComponent(project.name)}`);
                    const runsData = await runsRes.json();

                    // Fetch pipelines - we need to count unique pipelines from runs
                    const pipelineNames = new Set((runsData.runs || []).map(r => r.pipeline_name));

                    // Fetch artifacts for this project
                    const artifactsRes = await fetch(`/api/assets?project=${encodeURIComponent(project.name)}`);
                    const artifactsData = await artifactsRes.json();

                    return {
                        ...project,
                        runs: (runsData.runs || []).length,
                        pipelines: pipelineNames.size,
                        artifacts: (artifactsData.artifacts || []).length
                    };
                } catch (err) {
                    console.error(`Failed to fetch stats for project ${project.name}:`, err);
                    return {
                        ...project,
                        runs: 0,
                        pipelines: 0,
                        artifacts: 0
                    };
                }
            }));

            setProjects(projectsWithStats);
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const createProject = async (e) => {
        e.preventDefault();
        try {
            const response = await fetchApi('/api/projects/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newProjectName,
                    description: newProjectDesc
                })
            });

            if (response.ok) {
                setShowCreateModal(false);
                setNewProjectName('');
                setNewProjectDesc('');
                fetchProjects();
            }
        } catch (error) {
            console.error('Failed to create project:', error);
        }
    };

    const deleteProject = async (name) => {
        if (!confirm(`Are you sure you want to delete project "${name}"?`)) return;

        try {
            const response = await fetchApi(`/api/projects/${name}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                fetchProjects();
            }
        } catch (error) {
            console.error('Failed to delete project:', error);
        }
    };

    const columns = [
        {
            header: 'Project Name',
            key: 'name',
            sortable: true,
            render: (project) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Folder className="w-5 h-5 text-blue-500" />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{project.name}</div>
                        <div className="text-xs text-slate-500">Created {format(new Date(project.created_at), 'MMM d, yyyy')}</div>
                    </div>
                </div>
            )
        },
        {
            header: 'Description',
            key: 'description',
            render: (project) => (
                <span className="text-slate-500 dark:text-slate-400 truncate max-w-xs block">
                    {project.description || "No description"}
                </span>
            )
        },
        {
            header: 'Stats',
            key: 'stats',
            render: (project) => {
                const stats = {
                    runs: project.runs || 0,
                    pipelines: project.pipelines || 0,
                    artifacts: project.artifacts || 0
                };
                return (
                    <div className="flex gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1"><Activity size={14} /> {stats.pipelines || 0}</span>
                        <span className="flex items-center gap-1"><Clock size={14} /> {stats.runs || 0}</span>
                        <span className="flex items-center gap-1"><Database size={14} /> {stats.artifacts || 0}</span>
                    </div>
                );
            }
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (project) => (
                <button
                    onClick={(e) => { e.stopPropagation(); deleteProject(project.name); }}
                    className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                >
                    <Trash2 size={16} />
                </button>
            )
        }
    ];

    const renderGrid = (project) => {
        // Stats are already attached to the project object
        const stats = {
            runs: project.runs || 0,
            pipelines: project.pipelines || 0,
            artifacts: project.artifacts || 0
        };

        return (
            <Link
                to={`/projects/${encodeURIComponent(project.name)}`}
                onClick={() => setSelectedProject(project.name)}
                className="block"
            >
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 hover:border-blue-500/50 hover:shadow-md transition-all group cursor-pointer">
                    <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-colors">
                                <Folder className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">{project.name}</h3>
                                <p className="text-xs text-slate-500">
                                    Created {format(new Date(project.created_at), 'MMM d, yyyy')}
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); deleteProject(project.name); }}
                            className="text-slate-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>

                    <p className="text-slate-500 dark:text-slate-400 mb-6 h-10 overflow-hidden text-sm line-clamp-2">
                        {project.description || "No description provided."}
                    </p>

                    <div className="grid grid-cols-3 gap-4 border-t border-slate-100 dark:border-slate-700 pt-4">
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
                                <Activity className="w-3 h-3" /> Pipelines
                            </div>
                            <span className="font-bold text-slate-700 dark:text-slate-200">{stats.pipelines || 0}</span>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
                                <Clock className="w-3 h-3" /> Runs
                            </div>
                            <span className="font-bold text-slate-700 dark:text-slate-200">{stats.runs || 0}</span>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
                                <Database className="w-3 h-3" /> Artifacts
                            </div>
                            <span className="font-bold text-slate-700 dark:text-slate-200">{stats.artifacts || 0}</span>
                        </div>
                    </div>
                </div>
            </Link>
        );
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <DataView
                title="Projects"
                subtitle="Manage your ML projects and workspaces"
                items={projects}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                actions={
                    <Button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2">
                        <Plus size={18} />
                        New Project
                    </Button>
                }
                emptyState={
                    <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <Folder className="w-12 h-12 mx-auto text-slate-400 mb-4" />
                        <h3 className="text-lg font-medium text-slate-900 dark:text-white">No projects found</h3>
                        <p className="text-slate-500 mb-6">Get started by creating your first project.</p>
                        <Button onClick={() => setShowCreateModal(true)}>
                            Create Project
                        </Button>
                    </div>
                }
            />

            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
                    <div className="bg-white dark:bg-slate-800 p-6 rounded-xl w-full max-w-md border border-slate-200 dark:border-slate-700 shadow-xl">
                        <h2 className="text-xl font-bold mb-4 text-slate-900 dark:text-white">Create New Project</h2>
                        <form onSubmit={createProject}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Project Name</label>
                                <input
                                    type="text"
                                    value={newProjectName}
                                    onChange={(e) => setNewProjectName(e.target.value)}
                                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus:border-blue-500 outline-none text-slate-900 dark:text-white"
                                    required
                                    placeholder="e.g., recommendation-system"
                                />
                            </div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Description</label>
                                <textarea
                                    value={newProjectDesc}
                                    onChange={(e) => setNewProjectDesc(e.target.value)}
                                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus:border-blue-500 outline-none text-slate-900 dark:text-white"
                                    rows="3"
                                    placeholder="Brief description of the project..."
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <Button type="submit">
                                    Create Project
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
