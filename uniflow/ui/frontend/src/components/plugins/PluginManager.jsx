import React, { useState } from 'react';
import { Package, Download, RefreshCw, Server } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { PluginBrowser } from './PluginBrowser';
import { InstalledPlugins } from './InstalledPlugins';
import { ZenMLIntegration } from './ZenMLIntegration';

export function PluginManager() {
    const [activeTab, setActiveTab] = useState('browser');

    const tabs = [
        { id: 'browser', label: 'Plugin Browser', icon: Package },
        { id: 'installed', label: 'Installed', icon: Download },
        { id: 'zenml', label: 'ZenML Integration', icon: Server },
    ];

    return (
        <Card className="overflow-hidden">
            <CardHeader className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 pb-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Package size={20} className="text-primary-500" />
                        <CardTitle>Plugins & Integrations</CardTitle>
                    </div>
                </div>

                <div className="flex gap-6">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`
                                    flex items-center gap-2 pb-3 text-sm font-medium transition-all relative
                                    ${isActive
                                        ? 'text-primary-600 dark:text-primary-400'
                                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                                    }
                                `}
                            >
                                <Icon size={16} />
                                {tab.label}
                                {isActive && (
                                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-500 rounded-t-full" />
                                )}
                            </button>
                        );
                    })}
                </div>
            </CardHeader>
            <CardContent className="p-6">
                {activeTab === 'browser' && <PluginBrowser />}
                {activeTab === 'installed' && <InstalledPlugins />}
                {activeTab === 'zenml' && <ZenMLIntegration />}
            </CardContent>
        </Card>
    );
}
