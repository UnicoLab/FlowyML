import React, { useState, useEffect } from 'react';
import { Folder, Plus, Trash2, Activity, Database, Clock } from 'lucide-react';
import { format } from 'date-fns';

export default function Projects() {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newProjectName, setNewProjectName] = useState('');
    const [newProjectDesc, setNewProjectDesc] = useState('');

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const response = await fetch('/api/projects/');
            const data = await response.json();
            setProjects(data);
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const createProject = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/projects/', {
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
            const response = await fetch(`/api/projects/${name}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                fetchProjects();
            }
        } catch (error) {
            console.error('Failed to delete project:', error);
        }
    };

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">📂 Projects</h1>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    New Project
                </button>
            </div>

            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 p-6 rounded-lg w-full max-w-md border border-gray-700">
                        <h2 className="text-xl font-bold mb-4">Create New Project</h2>
                        <form onSubmit={createProject}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Project Name</label>
                                <input
                                    type="text"
                                    value={newProjectName}
                                    onChange={(e) => setNewProjectName(e.target.value)}
                                    className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    required
                                />
                            </div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <textarea
                                    value={newProjectDesc}
                                    onChange={(e) => setNewProjectDesc(e.target.value)}
                                    className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none"
                                    rows="3"
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
                                >
                                    Create
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
            ) : projects.length === 0 ? (
                <div className="text-center py-12 bg-gray-800/30 rounded-lg border-2 border-dashed border-gray-700">
                    <Folder className="w-12 h-12 mx-auto text-gray-600 mb-4" />
                    <p className="text-gray-400">No projects found</p>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-4 text-blue-400 hover:text-blue-300"
                    >
                        Create your first project
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <div key={project.name} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-6 hover:border-blue-500/50 transition-all">
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-blue-500/10 rounded-lg">
                                        <Folder className="w-6 h-6 text-blue-400" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-lg">{project.name}</h3>
                                        <p className="text-sm text-gray-400">
                                            Created {format(new Date(project.created_at), 'MMM d, yyyy')}
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => deleteProject(project.name)}
                                    className="text-gray-500 hover:text-red-400 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>

                            <p className="text-gray-300 mb-6 h-12 overflow-hidden text-sm">
                                {project.description || "No description provided."}
                            </p>

                            <div className="grid grid-cols-3 gap-4 border-t border-gray-700/50 pt-4">
                                <div className="text-center">
                                    <div className="flex items-center justify-center gap-1 text-gray-400 text-xs mb-1">
                                        <Activity className="w-3 h-3" /> Pipelines
                                    </div>
                                    <span className="font-bold">{project.pipelines?.length || 0}</span>
                                </div>
                                <div className="text-center">
                                    <div className="flex items-center justify-center gap-1 text-gray-400 text-xs mb-1">
                                        <Clock className="w-3 h-3" /> Runs
                                    </div>
                                    <span className="font-bold">0</span>
                                </div>
                                <div className="text-center">
                                    <div className="flex items-center justify-center gap-1 text-gray-400 text-xs mb-1">
                                        <Database className="w-3 h-3" /> Artifacts
                                    </div>
                                    <span className="font-bold">0</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
