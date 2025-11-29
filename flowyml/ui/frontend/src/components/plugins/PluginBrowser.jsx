import React, { useState, useEffect } from 'react';
import { Search, Download, Star, CheckCircle, Loader2, Plus } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { pluginService } from '../../services/pluginService';
import { AddPluginDialog } from './AddPluginDialog';

export function PluginBrowser() {
    const [search, setSearch] = useState('');
    const [plugins, setPlugins] = useState([]);
    const [loading, setLoading] = useState(true);
    const [installing, setInstalling] = useState(null);
    const [showAddDialog, setShowAddDialog] = useState(false);

    useEffect(() => {
        loadPlugins();
    }, []);

    const loadPlugins = async () => {
        try {
            setLoading(true);
            const data = await pluginService.getAvailablePlugins();
            setPlugins(data);
        } catch (error) {
            console.error('Failed to load plugins:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredPlugins = plugins.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.description.toLowerCase().includes(search.toLowerCase())
    );

    const handleInstall = async (id) => {
        setInstalling(id);
        try {
            await pluginService.installPlugin(id);
            // Update local state to show installed
            setPlugins(prev => prev.map(p =>
                p.id === id ? { ...p, installed: true } : p
            ));
        } catch (error) {
            console.error('Install failed:', error);
            alert(`Installation failed: ${error.message}`);
        } finally {
            setInstalling(null);
        }
    };

    const handleManualAdd = async ({ type, value }) => {
        setInstalling('manual');
        try {
            await pluginService.installPlugin(value);
            // Reload the list to show the new plugin
            await loadPlugins();
            alert(`Successfully installed ${value}`);
        } catch (error) {
            console.error('Install failed:', error);
            alert(`Installation failed: ${error.message}`);
        } finally {
            setInstalling(null);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <Loader2 className="animate-spin text-primary-500" size={32} />
            </div>
        );
    }

    return (
        <>
            <div className="space-y-6">
                <div className="flex gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search plugins..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                    </div>
                    <Button
                        onClick={() => setShowAddDialog(true)}
                        className="flex items-center gap-2"
                    >
                        <Plus size={18} />
                        Add Plugin
                    </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredPlugins.map((plugin) => (
                        <div
                            key={plugin.id}
                            className="p-4 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-primary-500/50 dark:hover:border-primary-500/50 transition-colors bg-white dark:bg-slate-800/50"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <h3 className="font-semibold text-slate-900 dark:text-white">{plugin.name}</h3>
                                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-1">
                                        <span>v{plugin.version}</span>
                                        <span>•</span>
                                        <span>by {plugin.author}</span>
                                    </div>
                                </div>
                                {plugin.installed ? (
                                    <Badge variant="success" className="flex items-center gap-1">
                                        <CheckCircle size={12} /> Installed
                                    </Badge>
                                ) : (
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleInstall(plugin.id)}
                                        disabled={installing === plugin.id || installing === 'manual'}
                                    >
                                        {installing === plugin.id ? (
                                            <>
                                                <Loader2 size={12} className="animate-spin mr-1" />
                                                Installing...
                                            </>
                                        ) : 'Install'}
                                    </Button>
                                )}
                            </div>

                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-4 line-clamp-2">
                                {plugin.description}
                            </p>

                            <div className="flex items-center justify-between mt-auto">
                                <div className="flex gap-2">
                                    {plugin.tags.map(tag => (
                                        <span key={tag} className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded-full">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                    <div className="flex items-center gap-1">
                                        <Download size={12} /> {plugin.downloads}
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Star size={12} /> {plugin.stars}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <AddPluginDialog
                isOpen={showAddDialog}
                onClose={() => setShowAddDialog(false)}
                onAdd={handleManualAdd}
            />
        </>
    );
}
