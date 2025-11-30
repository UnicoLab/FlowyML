import React from 'react';
import { Activity, Clock, Database, Folder, GitBranch, Box } from 'lucide-react';
import { format } from 'date-fns';

export function ProjectHeader({ project, stats, loading }) {
    if (loading || !project) {
        return (
            <div className="animate-pulse space-y-4">
                <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
                <div className="grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    ))}
                </div>
            </div>
        );
    }

    const statItems = [
        { label: 'Pipelines', value: stats?.pipelines || 0, icon: Activity, color: 'text-blue-500', bg: 'bg-blue-500/10' },
        { label: 'Runs', value: stats?.runs || 0, icon: Clock, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'Artifacts', value: stats?.artifacts || 0, icon: Database, color: 'text-purple-500', bg: 'bg-purple-500/10' },
        { label: 'Models', value: stats?.models || 0, icon: Box, color: 'text-orange-500', bg: 'bg-orange-500/10' },
    ];

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
                            <span>Created {format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                            <span>•</span>
                            <span>{project.description || "No description provided"}</span>
                        </div>
                    </div>
                </div>
                <div className="flex gap-2">
                    {/* Actions like Edit/Delete can go here */}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {statItems.map((item, index) => (
                    <div key={index} className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">{item.label}</span>
                            <div className={`p-2 rounded-lg ${item.bg}`}>
                                <item.icon className={`w-4 h-4 ${item.color}`} />
                            </div>
                        </div>
                        <div className="text-2xl font-bold text-slate-900 dark:text-white">{item.value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
