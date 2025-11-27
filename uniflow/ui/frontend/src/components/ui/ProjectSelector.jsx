import React from 'react';
import { ChevronDown, FolderOpen, Globe } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';
import { motion, AnimatePresence } from 'framer-motion';

export function ProjectSelector() {
    const { selectedProject, projects, loading, selectProject, clearProject } = useProject();
    const [isOpen, setIsOpen] = React.useState(false);

    const currentProject = projects.find(p => p.name === selectedProject);

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors min-w-[200px]"
            >
                {selectedProject ? (
                    <>
                        <FolderOpen size={18} className="text-primary-600 dark:text-primary-400" />
                        <div className="flex-1 text-left">
                            <div className="text-sm font-medium text-slate-900 dark:text-white">
                                {currentProject?.name || selectedProject}
                            </div>
                            {currentProject?.description && (
                                <div className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[150px]">
                                    {currentProject.description}
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <>
                        <Globe size={18} className="text-slate-400" />
                        <span className="flex-1 text-left text-sm font-medium text-slate-700 dark:text-slate-300">
                            All Projects
                        </span>
                    </>
                )}
                <ChevronDown
                    size={16}
                    className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        {/* Backdrop */}
                        <div
                            className="fixed inset-0 z-10"
                            onClick={() => setIsOpen(false)}
                        />

                        {/* Dropdown */}
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.15 }}
                            className="absolute top-full mt-2 left-0 w-full min-w-[280px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl z-20 max-h-[400px] overflow-y-auto"
                        >
                            {/* All Projects Option */}
                            <button
                                onClick={() => {
                                    clearProject();
                                    setIsOpen(false);
                                }}
                                className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${!selectedProject ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                                    }`}
                            >
                                <Globe size={18} className="text-slate-400" />
                                <div className="flex-1 text-left">
                                    <div className="text-sm font-medium text-slate-900 dark:text-white">
                                        All Projects
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400">
                                        View data from all projects
                                    </div>
                                </div>
                                {!selectedProject && (
                                    <div className="w-2 h-2 rounded-full bg-primary-600" />
                                )}
                            </button>

                            <div className="border-t border-slate-200 dark:border-slate-700" />

                            {/* Project List */}
                            {loading ? (
                                <div className="px-4 py-8 text-center text-slate-500 dark:text-slate-400 text-sm">
                                    Loading projects...
                                </div>
                            ) : projects.length === 0 ? (
                                <div className="px-4 py-8 text-center text-slate-500 dark:text-slate-400 text-sm">
                                    No projects yet
                                </div>
                            ) : (
                                projects.map(project => (
                                    <button
                                        key={project.name}
                                        onClick={() => {
                                            selectProject(project.name);
                                            setIsOpen(false);
                                        }}
                                        className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${selectedProject === project.name ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                                            }`}
                                    >
                                        <FolderOpen
                                            size={18}
                                            className={selectedProject === project.name ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400'}
                                        />
                                        <div className="flex-1 text-left">
                                            <div className="text-sm font-medium text-slate-900 dark:text-white">
                                                {project.name}
                                            </div>
                                            {project.description && (
                                                <div className="text-xs text-slate-500 dark:text-slate-400">
                                                    {project.description}
                                                </div>
                                            )}
                                        </div>
                                        {selectedProject === project.name && (
                                            <div className="w-2 h-2 rounded-full bg-primary-600" />
                                        )}
                                    </button>
                                ))
                            )}
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
