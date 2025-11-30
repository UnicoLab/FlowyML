import React from 'react';
import { Activity, Clock, Database, Box, GitBranch, LayoutDashboard } from 'lucide-react';

export function ProjectTabs({ activeTab, onTabChange }) {
    const tabs = [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'pipelines', label: 'Pipelines', icon: Activity },
        { id: 'runs', label: 'Runs', icon: Clock },
        { id: 'models', label: 'Models', icon: Box },
        { id: 'artifacts', label: 'Artifacts', icon: Database },
    ];

    return (
        <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
            <div className="flex gap-6 overflow-x-auto">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        className={`
                            flex items-center gap-2 py-4 px-1 border-b-2 transition-colors whitespace-nowrap
                            ${activeTab === tab.id
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium'
                                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                        `}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
