import React from 'react';
import { Activity, Clock, Database, Folder, GitBranch, Box } from 'lucide-react';
import { formatDate } from '../../../../utils/date';

export function ProjectHeader({ project, stats, loading }) {
    if (loading || !project) {
        return (
            <div className="animate-pulse space-y-4">
                <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
                <div className="grid grid-cols-4 gap-4">
                    <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-4 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20">
                        <Folder className="w-8 h-8 text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-1">{project.name}</h1>
                        <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                            <span>Created {formatDate(project.created_at)}</span>
                            <span>•</span>
                            <span>{project.description || "No description provided"}</span>
                        </div>
                    </div>
                </div>
                <div className="flex gap-2">
                    {/* Actions like Edit/Delete can go here */}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">Pipelines</span>
                        <div className="p-2 rounded-lg bg-blue-500/10">
                            <Activity className="w-4 h-4 text-blue-500" />
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats?.pipelines || 0}</div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">Runs</span>
                        <div className="p-2 rounded-lg bg-green-500/10">
                            <Clock className="w-4 h-4 text-green-500" />
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats?.runs || 0}</div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">Artifacts</span>
                        <div className="p-2 rounded-lg bg-purple-500/10">
                            <Database className="w-4 h-4 text-purple-500" />
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats?.artifacts || 0}</div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">Models</span>
                        <div className="p-2 rounded-lg bg-orange-500/10">
                            <Box className="w-4 h-4 text-orange-500" />
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats?.models || 0}</div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">Experiments</span>
                        <div className="p-2 rounded-lg bg-pink-500/10">
                            <Activity className="w-4 h-4 text-pink-500" />
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{stats?.experiments || 0}</div>
                </div>
            </div>
        </div>
    );
}
