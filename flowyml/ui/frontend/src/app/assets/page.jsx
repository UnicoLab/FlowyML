import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { downloadArtifactById } from '../../utils/downloads';
import { Link } from 'react-router-dom';
import { Database, Box, BarChart2, FileText, Search, Filter, Calendar, Package, Download, Eye, X, ArrowRight, Network, Activity, HardDrive } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';
import { EmptyState } from '../../components/ui/EmptyState';
import { KeyValue, KeyValueGrid } from '../../components/ui/KeyValue';
import { AssetStatsDashboard } from '../../components/AssetStatsDashboard';
import { AssetTreeHierarchy } from '../../components/AssetTreeHierarchy';
import { AssetDetailsPanel } from '../../components/AssetDetailsPanel';

export function Assets() {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [typeFilter, setTypeFilter] = useState('all');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [viewMode, setViewMode] = useState('grid'); // Default to grid, hierarchy is always visible in sidebar
    const [stats, setStats] = useState(null); // For compact stats display
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

    // Fetch stats for compact display
    useEffect(() => {
        const fetchStats = async () => {
            try {
                const url = selectedProject
                    ? `/api/assets/stats?project=${encodeURIComponent(selectedProject)}`
                    : '/api/assets/stats';
                const res = await fetchApi(url);
                const data = await res.json();
                setStats(data);
            } catch (err) {
                console.error('Failed to fetch stats:', err);
            }
        };

        fetchStats();
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
            header: 'Pipeline',
            key: 'pipeline',
            sortable: true,
            render: (asset) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                    {asset.pipeline_name || '-'}
                </span>
            )
        },
        {
            header: 'Project',
            key: 'project',
            sortable: true,
            render: (asset) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                    {asset.project || '-'}
                </span>
            )
        },
        {
            header: 'Run ID',
            key: 'run_id',
            render: (asset) => asset.run_id ? (
                <Link
                    to={`/runs/${asset.run_id}`}
                    className="font-mono text-xs bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                >
                    {asset.run_id.substring(0, 8)}...
                </Link>
            ) : (
                <span className="font-mono text-xs text-slate-400">-</span>
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
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setSelectedAsset(asset)}
                        className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
                    >
                        View <Eye size={14} />
                    </button>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            downloadArtifactById(asset.artifact_id);
                        }}
                        className="text-slate-600 hover:text-primary-600 font-medium text-sm flex items-center gap-1 disabled:opacity-50"
                        disabled={!asset.artifact_id}
                    >
                        <Download size={14} /> Download
                    </button>
                </div>
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

        // Count properties
        const propertyCount = asset.properties ? Object.keys(asset.properties).length : 0;

        // Create animated property tags
        const propertyTags = asset.properties
            ? Object.entries(asset.properties).slice(0, 3).map(([key, value], idx) => (
                <motion.span
                    key={key}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded-md text-xs text-slate-600 dark:text-slate-400"
                >
                    <span className="font-medium">{key}:</span>
                    <span className="font-mono">{typeof value === 'number' ? value.toFixed(2) : String(value).substring(0, 20)}</span>
                </motion.span>
            ))
            : [];

        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -5 }}
                transition={{ duration: 0.2 }}
            >
                <Card
                    className="group cursor-pointer hover:shadow-2xl hover:border-primary-300 dark:hover:border-primary-700 transition-all duration-300 overflow-hidden h-full relative"
                    onClick={() => setSelectedAsset(asset)}
                >
                    {/* Gradient background effect */}
                    <div className={`absolute inset-0 bg-gradient-to-br ${colorClasses[config.color]} opacity-0 group-hover:opacity-10 transition-opacity duration-300`}></div>

                    <div className="relative">
                        {/* Icon Header */}
                        <div className="flex items-start justify-between mb-3">
                            <motion.div
                                className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[config.color]} text-white shadow-lg`}
                                whileHover={{ scale: 1.1, rotate: 5 }}
                                transition={{ duration: 0.2 }}
                            >
                                {config.icon}
                            </motion.div>
                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <button
                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedAsset(asset);
                                    }}
                                >
                                    <Eye size={16} className="text-slate-400" />
                                </button>
                                <button
                                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-40"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        downloadArtifactById(asset.artifact_id);
                                    }}
                                    disabled={!asset.artifact_id}
                                >
                                    <Download size={16} className="text-slate-400" />
                                </button>
                            </div>
                        </div>

                        {/* Name */}
                        <h4 className="font-bold text-slate-900 dark:text-white mb-2 truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                            {asset.name}
                        </h4>

                        {/* Type Badge */}
                        <div className="mb-3">
                            <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${colorClasses[config.color]} text-white`}>
                                {asset.type}
                            </span>
                        </div>

                        {/* Metadata */}
                        <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400 mb-3">
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
                            {asset.pipeline_name && (
                                <div className="flex items-center justify-between">
                                    <span>Pipeline:</span>
                                    <span className="text-slate-700 dark:text-slate-300 truncate ml-2">{asset.pipeline_name}</span>
                                </div>
                            )}
                        </div>

                        {/* Animated Property Tags */}
                        {propertyTags.length > 0 && (
                            <div className="pt-3 border-t border-slate-100 dark:border-slate-700">
                                <div className="flex flex-wrap gap-1 mb-2">
                                    {propertyTags}
                                    {propertyCount > 3 && (
                                        <span className="inline-flex items-center px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded-md text-xs text-slate-400">
                                            +{propertyCount - 3} more
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Relationship Indicator (placeholder for now) */}
                        {asset.run_id && (
                            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                                <Link
                                    to={`/runs/${asset.run_id}`}
                                    className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <Activity size={12} />
                                    View in run
                                </Link>
                            </div>
                        )}
                    </div>
                </Card>
            </motion.div>
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
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Compact Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white">Assets</h1>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            {assets.length} artifact{assets.length !== 1 ? 's' : ''} across your pipelines
                        </p>
                    </div>

                    {/* View Mode Switcher - Only when no asset selected */}
                    {!selectedAsset && (
                        <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-700 p-1 rounded-lg">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${viewMode === 'grid'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow'
                                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                                    }`}
                            >
                                Grid
                            </button>
                            <button
                                onClick={() => setViewMode('table')}
                                className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${viewMode === 'table'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow'
                                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                                    }`}
                            >
                                Table
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-[1800px] mx-auto px-6 py-6">
                    <div className="h-full flex gap-6">
                        {/* Left Sidebar - Navigation & Stats */}
                        <div className="w-[380px] shrink-0 flex flex-col gap-4 overflow-y-auto">
                            {/* Quick Stats - Compact */}
                            <div className="grid grid-cols-2 gap-3">
                                <StatCardCompact
                                    icon={Package}
                                    label="Total"
                                    value={stats?.total_assets || 0}
                                    gradient="from-blue-500 to-cyan-500"
                                />
                                <StatCardCompact
                                    icon={Box}
                                    label="Models"
                                    value={stats?.by_type?.model || stats?.by_type?.Model || 0}
                                    gradient="from-purple-500 to-pink-500"
                                />
                                <StatCardCompact
                                    icon={Database}
                                    label="Datasets"
                                    value={stats?.by_type?.dataset || stats?.by_type?.Dataset || 0}
                                    gradient="from-emerald-500 to-teal-500"
                                />
                                <StatCardCompact
                                    icon={HardDrive}
                                    label="Storage"
                                    value={formatBytes(stats?.total_storage_bytes || 0)}
                                    gradient="from-orange-500 to-red-500"
                                />
                            </div>

                            {/* Tree Hierarchy */}
                            <div className="flex-1 min-h-0">
                                <AssetTreeHierarchy
                                    projectId={selectedProject}
                                    onAssetSelect={(asset) => setSelectedAsset(asset)}
                                />
                            </div>
                        </div>

                        {/* Right Content - Details Panel or Grid/Table View */}
                        <div className="flex-1 min-w-0 overflow-hidden">
                            {selectedAsset ? (
                                /* Asset Details Panel */
                                <AssetDetailsPanel
                                    asset={selectedAsset}
                                    onClose={() => setSelectedAsset(null)}
                                />
                            ) : (
                                /* Grid/Table View */
                                <div className="h-full flex flex-col">
                                    {/* Type Filter */}
                                    <div className="flex items-center gap-2 mb-4">
                                        <Filter size={16} className="text-slate-400 shrink-0" />
                                        <div className="flex gap-2 flex-wrap">
                                            {types.map(type => (
                                                <button
                                                    key={type}
                                                    onClick={() => setTypeFilter(type)}
                                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${typeFilter === type
                                                        ? 'bg-primary-500 text-white shadow-md'
                                                        : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
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

                                    {/* Content Area */}
                                    <div className="flex-1 min-h-0 overflow-hidden">
                                        <DataView
                                            title=""
                                            subtitle=""
                                            items={filteredAssets}
                                            loading={loading}
                                            columns={columns}
                                            renderGrid={renderGrid}
                                            initialView={viewMode}
                                            emptyState={
                                                <EmptyState
                                                    icon={Package}
                                                    title="No artifacts found"
                                                    description={typeFilter !== 'all'
                                                        ? 'Try adjusting your filters'
                                                        : 'Run a pipeline to generate artifacts'
                                                    }
                                                />
                                            }
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Compact stat card for sidebar
function StatCardCompact({ icon: Icon, label, value, gradient }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow group">
            <div className="flex items-center gap-2 mb-1">
                <div className={`p-1.5 rounded-lg bg-gradient-to-br ${gradient} text-white group-hover:scale-110 transition-transform`}>
                    <Icon size={14} />
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
            </div>
            <p className="text-lg font-bold text-slate-900 dark:text-white">
                {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
        </div>
    );
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => downloadArtifactById(asset.artifact_id)}
                                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-600 text-white font-medium text-sm hover:bg-primary-500 transition-colors disabled:opacity-50"
                                disabled={!asset.artifact_id}
                            >
                                <Download size={16} /> Download
                            </button>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors"
                            >
                                <X size={20} className="text-slate-400" />
                            </button>
                        </div>
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
                                <KeyValueGrid items={[
                                    { label: "Artifact ID", value: asset.artifact_id, valueClassName: "font-mono text-xs" },
                                    { label: "Type", value: asset.type },
                                    { label: "Step", value: asset.step },
                                    { label: "Run ID", value: asset.run_id, valueClassName: "font-mono text-xs" },
                                    ...(asset.created_at ? [{
                                        label: "Created At",
                                        value: format(new Date(asset.created_at), 'MMM d, yyyy HH:mm:ss')
                                    }] : []),
                                    ...(asset.path ? [{
                                        label: "Path",
                                        value: asset.path,
                                        valueClassName: "font-mono text-xs"
                                    }] : [])
                                ]} columns={2} />
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



function getTypeIcon(type) {
    const icons = {
        Dataset: <Database size={18} className="text-blue-600" />,
        Model: <Box size={18} className="text-purple-600" />,
        Metrics: <BarChart2 size={18} className="text-emerald-600" />
    };
    return icons[type] || <FileText size={18} className="text-slate-600" />;
}
