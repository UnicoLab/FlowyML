import React, { useState, useEffect } from 'react';
import { Trash2, Settings, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { pluginService } from '../../services/pluginService';

export function InstalledPlugins() {
    const [plugins, setPlugins] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uninstalling, setUninstalling] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        loadPlugins();
    }, []);

    const loadPlugins = async () => {
        try {
            setLoading(true);
            const data = await pluginService.getInstalledPlugins();
            setPlugins(data);
        } catch (error) {
            console.error('Failed to load installed plugins:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await loadPlugins();
    };

    const handleUninstall = async (id) => {
        if (!confirm('Are you sure you want to uninstall this plugin?')) return;

        setUninstalling(id);
        try {
            await pluginService.uninstallPlugin(id);
            setPlugins(prev => prev.filter(p => p.id !== id));
        } catch (error) {
            console.error('Uninstall failed:', error);
            alert(`Uninstall failed: ${error.message}`);
        } finally {
            setUninstalling(null);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <Loader2 className="animate-spin text-primary-500" size={32} />
            </div>
        );
    }

    if (plugins.length === 0) {
        return (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                <p>No plugins installed yet.</p>
                <p className="text-sm mt-2">Install plugins from the Browser tab</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Refresh Button */}
            <div className="flex justify-end">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center gap-2"
                >
                    <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                    Refresh
                </Button>
            </div>

            {plugins.map((plugin) => (
                <div
                    key={plugin.id}
                    className="flex items-center justify-between p-4 bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl"
                >
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
                            <Settings className="text-primary-500" size={24} />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-semibold text-slate-900 dark:text-white">{plugin.name}</h3>
                                <Badge variant="outline" className="text-xs">v{plugin.version}</Badge>
                                <Badge variant="success" className="text-xs">Active</Badge>
                            </div>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                {plugin.description}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                            title="Uninstall"
                            onClick={() => handleUninstall(plugin.id)}
                            disabled={uninstalling === plugin.id}
                        >
                            {uninstalling === plugin.id ? (
                                <Loader2 size={16} className="animate-spin" />
                            ) : (
                                <Trash2 size={16} />
                            )}
                        </Button>
                    </div>
                </div>
            ))}
        </div>
    );
}
