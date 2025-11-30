import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import { Folder, ChevronDown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function ProjectSelector({ currentProject, onUpdate, type = 'default' }) {
    const [projects, setProjects] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen && projects.length === 0) {
            fetchProjects();
        }
    }, [isOpen]);

    const fetchProjects = async () => {
        setLoading(true);
        try {
            const res = await fetchApi('/api/projects/');
            const data = await res.json();
            setProjects(data.projects || []);
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = async (projectName) => {
        if (projectName === currentProject) {
            setIsOpen(false);
            return;
        }

        await onUpdate(projectName);
        setIsOpen(false);
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`
                    flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                    ${currentProject
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                    }
                `}
            >
                <Folder size={14} />
                <span>{currentProject || 'Assign Project'}</span>
                <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setIsOpen(false)}
                        />
                        <motion.div
                            initial={{ opacity: 0, y: 5, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 5, scale: 0.95 }}
                            transition={{ duration: 0.1 }}
                            className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden"
                        >
                            <div className="p-2 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2">
                                    Select Project
                                </span>
                            </div>

                            <div className="max-h-64 overflow-y-auto p-1">
                                {loading ? (
                                    <div className="p-4 text-center text-slate-400 text-xs">Loading...</div>
                                ) : (
                                    <>
                                        {projects.map(project => (
                                            <button
                                                key={project.name}
                                                onClick={() => handleSelect(project.name)}
                                                className={`
                                                    w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors
                                                    ${currentProject === project.name
                                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                                                    }
                                                `}
                                            >
                                                <div className="flex items-center gap-2">
                                                    <Folder size={14} />
                                                    <span className="truncate max-w-[140px]">{project.name}</span>
                                                </div>
                                                {currentProject === project.name && <Check size={14} />}
                                            </button>
                                        ))}
                                        {projects.length === 0 && (
                                            <div className="p-3 text-center text-slate-400 text-xs">
                                                No projects found
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
