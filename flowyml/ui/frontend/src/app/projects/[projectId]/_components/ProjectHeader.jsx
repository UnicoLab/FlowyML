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
        <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
                    <Folder className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">{project.name}</h1>
                    <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                        <span>Created {formatDate(project.metadata?.created_at || project.created_at)}</span>
                        {(project.metadata?.description || project.description) && (
                            <>
                                <span>•</span>
                                <span>{project.metadata?.description || project.description}</span>
                            </>
                        )}
                    </div>
                </div>
            </div>
            <div className="flex gap-2">
                {/* Actions like Edit/Delete can go here */}
            </div>
        </div>
    );
}
