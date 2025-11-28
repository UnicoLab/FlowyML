import React, { useEffect, useState } from 'react';
import { fetchApi } from '../utils/api';
import { Database, Box, BarChart2, FileText, Search, Filter, Calendar, Package, Download, Eye, X, ArrowRight } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { DataView } from './ui/DataView';
import { useProject } from '../contexts/ProjectContext';

export function Assets() {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [typeFilter, setTypeFilter] = useState('all');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchAssets = async () => {
            setLoading(true);
            try {
                const url = selectedProject
                    ? `/api/assets?limit=50&project=${encodeURIComponent(selectedProject)}`
                    : '/api/assets?limit=50';
                const res = await fetchApi(url);
                const data = await res.json();
                setAssets(data.assets || []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchAssets();
    }, [selectedProject]);

    // Get unique types
    const types = ['all', ...new Set(assets.map(a => a.type))];

    // Filter assets
    const filteredAssets = assets.filter(asset => {
        return typeFilter === 'all' || asset.type === typeFilter;
    });

    const columns = [
        {
            header: 'Type',
            key: 'type',
            sortable: true,
            render: (asset) => {
                const typeConfig = {
                    Dataset: { icon: <Database size={16} />, color: 'text-blue-600', bg: 'bg-blue-50' },
                    Model: { icon: <Box size={16} />, color: 'text-purple-600', bg: 'bg-purple-50' },
                    Metrics: { icon: <BarChart2 size={16} />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                    default: { icon: <FileText size={16} />, color: 'text-slate-600', bg: 'bg-slate-50' }
                };
                const config = typeConfig[asset.type] || typeConfig.default;
                return (
                    <div className={`flex items-center gap-2 px-2 py-1 rounded-md w-fit ${config.bg} ${config.color}`}>
                        {config.icon}
                        <span className="text-xs font-medium">{asset.type}</span>
                    </div>
                );
            }
        },
        {
            header: 'Name',
            key: 'name',
            sortable: true,
            render: (asset) => (
                <span className="font-medium text-slate-900 dark:text-white">{asset.name}</span>
            )
        },
        {
            header: 'Step',
            key: 'step',
            sortable: true,
            render: (asset) => (
                <span className="font-mono text-xs text-slate-500">{asset.step}</span>
            )
        },
        {
            header: 'Run ID',
            key: 'run_id',
            render: (asset) => (
                <span className="font-mono text-xs bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded text-slate-600 dark:text-slate-300">
                    {asset.run_id.substring(0, 8)}...
                </span>
            )
        },
        {
            header: 'Created',
            key: 'created_at',
            sortable: true,
            render: (asset) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Calendar size={14} />
                    {asset.created_at ? format(new Date(asset.created_at), 'MMM d, HH:mm') : '-'}
                </div>
            )
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (asset) => (
                <button
                    onClick={() => setSelectedAsset(asset)}
                    className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
                >
                    View <Eye size={14} />
                </button>
            )
        }
    ];

    const renderGrid = (asset) => {
        const typeConfig = {
            Dataset: { icon: <Database size={20} />, color: 'blue' },
            Model: { icon: <Box size={20} />, color: 'purple' },
            Metrics: { icon: <BarChart2 size={20} />, color: 'emerald' },
            default: { icon: <FileText size={20} />, color: 'slate' }
        };

        const config = typeConfig[asset.type] || typeConfig.default;

        const colorClasses = {
            blue: 'from-blue-500 to-cyan-500',
            purple: 'from-purple-500 to-pink-500',
            emerald: 'from-emerald-500 to-teal-500',
            slate: 'from-slate-500 to-slate-600'
        };

        return (
            <Card
                className="group cursor-pointer hover:shadow-xl hover:border-primary-300 transition-all duration-200 overflow-hidden h-full"
                onClick={() => setSelectedAsset(asset)}
            >
                {/* Icon Header */}
                <div className="flex items-start justify-between mb-3">
                    <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[config.color]} text-white shadow-lg group-hover:scale-110 transition-transform`}>
                        {config.icon}
                    </div>
                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                        <Eye size={16} className="text-slate-400" />
                    </button>
                </div>

                {/* Name */}
                <h4 className="font-bold text-slate-900 dark:text-white mb-1 truncate group-hover:text-primary-600 transition-colors">
                    {asset.name}
                </h4>

                {/* Metadata */}
                <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center justify-between">
                        <span>Step:</span>
                        <span className="font-mono text-slate-700 dark:text-slate-300 truncate ml-2">{asset.step}</span>
                    </div>
                    {asset.created_at && (
                        <div className="flex items-center justify-between">
                            <span>Created:</span>
                            <span className="text-slate-700 dark:text-slate-300">{format(new Date(asset.created_at), 'MMM d, HH:mm')}</span>
                        </div>
                    )}
                </div>

                {/* Properties Count */}
                {asset.properties && Object.keys(asset.properties).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                        <span className="text-xs text-slate-500">
                            {Object.keys(asset.properties).length} properties
                        </span>
                    </div>
                )}
            </Card>
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Type Filter */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
                <Filter size={16} className="text-slate-400 shrink-0" />
                <div className="flex gap-2">
                    {types.map(type => (
                        <button
                            key={type}
                            onClick={() => setTypeFilter(type)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${typeFilter === type
                                ? 'bg-primary-500 text-white shadow-md'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                }`}
                        >
                            {type === 'all' ? 'All Types' : type}
                            {type !== 'all' && (
                                <span className="ml-1.5 text-xs opacity-75">
                                    ({assets.filter(a => a.type === type).length})
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            <DataView
                title="Artifacts"
                subtitle="Browse and manage pipeline artifacts and outputs"
                items={filteredAssets}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Package className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No artifacts found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            {typeFilter !== 'all'
                                ? 'Try adjusting your filters'
                                : 'Run a pipeline to generate artifacts'
                            }
                        </p>
                    </div>
                }
            />

            {/* Asset Detail Modal */}
            <AssetDetailModal
                asset={selectedAsset}
                onClose={() => setSelectedAsset(null)}
            />
        </div>
    );
}

function AssetDetailModal({ asset, onClose }) {
    if (!asset) return null;

    const typeConfig = {
        Dataset: { icon: <Database size={24} />, color: 'text-blue-600', bg: 'bg-blue-50' },
        Model: { icon: <Box size={24} />, color: 'text-purple-600', bg: 'bg-purple-50' },
        Metrics: { icon: <BarChart2 size={24} />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
        default: { icon: <FileText size={24} />, color: 'text-slate-600', bg: 'bg-slate-50' }
    };

    const config = typeConfig[asset.type] || typeConfig.default;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden border border-slate-200 dark:border-slate-700"
                >
                    {/* Header */}
                    <div className={`flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-700 ${config.bg} dark:bg-slate-800`}>
                        <div className="flex items-center gap-4">
                            <div className={`p-3 bg-white dark:bg-slate-700 rounded-xl shadow-sm ${config.color}`}>
                                {config.icon}
                            </div>
                            <div>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{asset.name}</h3>
                                <p className="text-sm text-slate-500 mt-1">{asset.type} • {asset.step}</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            <X size={20} className="text-slate-400" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[calc(85vh-200px)]">
                        <div className="space-y-6">
                            {/* Properties */}
                            {asset.properties && Object.keys(asset.properties).length > 0 && (
                                <div>
                                    <h4 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Properties</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {Object.entries(asset.properties).map(([key, value]) => (
                                            <div key={key} className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-100 dark:border-slate-700">
                                                <span className="text-sm text-slate-500 dark:text-slate-400 block mb-2 font-medium">{key}</span>
                                                <span className="text-base font-mono font-semibold text-slate-900 dark:text-white break-all">
                                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Value Preview */}
                            {asset.value && (
                                <div>
                                    <h4 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Value Preview</h4>
                                    <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm font-mono overflow-x-auto leading-relaxed">
                                        {asset.value}
                                    </pre>
                                </div>
                            )}

                            {/* Metadata */}
                            <div>
                                <h4 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Metadata</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <MetadataItem label="Artifact ID" value={asset.artifact_id} mono />
                                    <MetadataItem label="Type" value={asset.type} />
                                    <MetadataItem label="Step" value={asset.step} />
                                    <MetadataItem label="Run ID" value={asset.run_id} mono />
                                    {asset.created_at && (
                                        <MetadataItem
                                            label="Created At"
                                            value={format(new Date(asset.created_at), 'MMM d, yyyy HH:mm:ss')}
                                        />
                                    )}
                                    {asset.path && (
                                        <MetadataItem label="Path" value={asset.path} mono />
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-4 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 flex justify-between items-center">
                        <span className="text-sm text-slate-500">
                            {asset.created_at && `Created ${format(new Date(asset.created_at), 'MMM d, yyyy')}`}
                        </span>
                        <div className="flex gap-2">
                            <Button variant="ghost" onClick={onClose}>Close</Button>
                            <Button variant="primary" className="flex items-center gap-2">
                                <Download size={16} />
                                Download
                            </Button>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

function MetadataItem({ label, value, mono = false }) {
    return (
        <div className="p-3 bg-white dark:bg-slate-700/50 rounded-lg border border-slate-100 dark:border-slate-700">
            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">{label}</span>
            <span className={`text-sm text-slate-900 dark:text-white font-semibold ${mono ? 'font-mono text-xs' : ''} break-all`}>
                {value}
            </span>
        </div>
    );
}

function getTypeIcon(type) {
    const icons = {
        Dataset: <Database size={18} className="text-blue-600" />,
        Model: <Box size={18} className="text-purple-600" />,
        Metrics: <BarChart2 size={18} className="text-emerald-600" />
    };
    return icons[type] || <FileText size={18} className="text-slate-600" />;
}
