import React from 'react';
import { Activity, Clock, Database, Box, LayoutDashboard, TrendingUp } from 'lucide-react';

export function ProjectTabs({ activeTab, onTabChange }) {
    return (
        <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
            <div className="flex gap-6 overflow-x-auto">
                <button
                    onClick={() => onTabChange('overview')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'overview'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <LayoutDashboard className="w-4 h-4" />
                    Overview
                </button>
                <button
                    onClick={() => onTabChange('pipelines')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'pipelines'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <Activity className="w-4 h-4" />
                    Pipelines
                </button>
                <button
                    onClick={() => onTabChange('runs')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'runs'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <Clock className="w-4 h-4" />
                    Runs
                </button>
                <button
                    onClick={() => onTabChange('experiments')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'experiments'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <Activity className="w-4 h-4" />
                    Experiments
                </button>
                <button
                    onClick={() => onTabChange('models')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'models'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <Box className="w-4 h-4" />
                    Models
                </button>
                <button
                    onClick={() => onTabChange('artifacts')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'artifacts'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <Database className="w-4 h-4" />
                    Artifacts
                </button>
                <button
                    onClick={() => onTabChange('metrics')}
                    className={`
                        flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                        ${activeTab === 'metrics'
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                    `}
                >
                    <TrendingUp className="w-4 h-4" />
                    Metrics
                </button>
            </div>
        </div>
    );
}
