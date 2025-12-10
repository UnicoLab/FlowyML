import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { downloadArtifactById } from '../../utils/downloads';
import { Link } from 'react-router-dom';
import { Database, Box, BarChart2, FileText, Search, Filter, Calendar, Package, Download, Eye, X, ArrowRight, Network, Activity, HardDrive, List, Grid } from 'lucide-react';
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
import { ProjectSelector } from '../../components/ProjectSelector';

export function Assets() {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [typeFilter, setTypeFilter] = useState('all');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [viewMode, setViewMode] = useState('table'); // Default to table for better density
    const [stats, setStats] = useState(null);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchAssets = async () => {
            setLoading(true);
            setError(null);
            try {
                const url = selectedProject
                    ? `/api/assets/?limit=50&project=${encodeURIComponent(selectedProject)}`
                    : '/api/assets/?limit=50';
                const res = await fetchApi(url);
                if (!res.ok) throw new Error(`Failed to fetch assets: ${res.statusText}`);

                const data = await res.json();
                setAssets(data.assets || []);
            } catch (err) {
                console.error(err);
                setError(err.message);
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
                if (res.ok) {
                    const data = await res.json();
                    setStats(data);
                }
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
                    Dataset: { icon: <Database size={14} />, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                    Model: { icon: <Box size={14} />, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/20' },
                    Metrics: { icon: <BarChart2 size={14} />, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
                    default: { icon: <FileText size={14} />, color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-800' }
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
                    className="font-mono text-xs text-primary-600 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                >
                    {asset.run_id?.substring(0, 8) || 'N/A'}
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
                <span className="text-sm text-slate-500">
                    {asset.created_at ? format(new Date(asset.created_at), 'MMM d, HH:mm') : '-'}
                </span>
            )
        },
        {
            header: '',
            key: 'actions',
            render: (asset) => (
                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                        onClick={() => setSelectedAsset(asset)}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-500 hover:text-primary-600"
                        title="View Details"
                    >
                        <Eye size={16} />
                    </button>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            downloadArtifactById(asset.artifact_id);
                        }}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-500 hover:text-primary-600"
                        disabled={!asset.artifact_id}
                        title="Download"
                    >
                        <Download size={16} />
                    </button>
                </div>
            )
        }
    ];

    const renderGrid = (asset) => {
        const typeConfig = {
            Dataset: { icon: <Database size={18} />, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
            Model: { icon: <Box size={18} />, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/20' },
            Metrics: { icon: <BarChart2 size={18} />, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
            default: { icon: <FileText size={18} />, color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-800' }
        };

        const config = typeConfig[asset.type] || typeConfig.default;

        return (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -2 }}
                transition={{ duration: 0.2 }}
            >
                <Card
                    className="group cursor-pointer hover:shadow-md hover:border-primary-200 dark:hover:border-primary-800 transition-all duration-200 h-full border border-slate-200 dark:border-slate-800"
                    onClick={() => setSelectedAsset(asset)}
                >
                    <div className="p-4">
                        <div className="flex items-start justify-between mb-3">
                            <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
                                {config.icon}
                            </div>
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 border-slate-200 dark:border-slate-700 text-slate-500">
                                {asset.type}
                            </Badge>
                        </div>

                        <h4 className="font-medium text-slate-900 dark:text-white mb-1 truncate group-hover:text-primary-600 transition-colors">
                            {asset.name}
                        </h4>

                        <div className="flex items-center gap-2 mb-4 text-xs text-slate-500">
                            <span className="truncate max-w-[120px]">{asset.step}</span>
                            {asset.project && (
                                <>
                                    <span>•</span>
                                    <span className="truncate max-w-[80px]">{asset.project}</span>
                                </>
                            )}
                        </div>

                        <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-400">
                            <span>
                                {asset.created_at ? format(new Date(asset.created_at), 'MMM d') : '-'}
                            </span>
                            {asset.run_id && (
                                <span className="font-mono bg-slate-50 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                                    {asset.run_id.slice(0, 6)}
                                </span>
                            )}
                        </div>
                    </div>
                </Card>
            </motion.div>
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="text-center p-8 bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-100 dark:border-red-800 max-w-md">
                    <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-red-700 dark:text-red-300 mb-2">Failed to load assets</h3>
                    <p className="text-red-600 dark:text-red-400 mb-6">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300 font-medium"
                    >
                        Retry Connection
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white">Assets</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                            Manage and track your pipeline artifacts
                        </p>
                    </div>

                    {!selectedAsset && (
                        <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-700 p-1 rounded-lg">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-1.5 rounded transition-all ${viewMode === 'grid'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                    }`}
                                title="Grid View"
                            >
                                <Grid size={16} />
                            </button>
                            <button
                                onClick={() => setViewMode('table')}
                                className={`p-1.5 rounded transition-all ${viewMode === 'table'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                    }`}
                                title="Table View"
                            >
                                <List size={16} />
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-[1800px] mx-auto px-6 py-6">
                    <div className="h-full flex gap-6">
                        {/* Sidebar */}
                        <div className="w-[380px] shrink-0 flex flex-col gap-4 overflow-y-auto pb-6">
                            {/* Stats */}
                            <div className="grid grid-cols-2 gap-3">
                                <StatCardCompact
                                    icon={Package}
                                    label="Total"
                                    value={stats?.total_assets || 0}
                                />
                                <StatCardCompact
                                    icon={HardDrive}
                                    label="Size"
                                    value={formatBytes(stats?.total_storage_bytes || 0)}
                                />
                            </div>

                            {/* Tree */}
                            <div className="flex-1 min-h-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
                                <div className="p-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Explorer</h3>
                                </div>
                                <div className="flex-1 overflow-y-auto p-2">
                                    <AssetTreeHierarchy
                                        projectId={selectedProject}
                                        onAssetSelect={(asset) => setSelectedAsset(asset)}
                                        compact={true}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Content Area */}
                        <div className="flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col shadow-sm">
                            {selectedAsset ? (
                                <AssetDetailsPanel
                                    asset={selectedAsset}
                                    onClose={() => setSelectedAsset(null)}
                                />
                            ) : (
                                <div className="h-full flex flex-col">
                                    {/* Filters */}
                                    <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-4 overflow-x-auto">
                                        <Filter size={16} className="text-slate-400 shrink-0" />
                                        <div className="flex gap-2">
                                            {types.map(type => (
                                                <button
                                                    key={type}
                                                    onClick={() => setTypeFilter(type)}
                                                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap border ${typeFilter === type
                                                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white'
                                                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 dark:hover:border-slate-600'
                                                        }`}
                                                >
                                                    {type === 'all' ? 'All' : type}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Data View */}
                                    <div className="flex-1 min-h-0 overflow-hidden">
                                        <DataView
                                            items={filteredAssets}
                                            loading={loading}
                                            columns={columns}
                                            renderGrid={renderGrid}
                                            initialView={viewMode}
                                            emptyState={
                                                <EmptyState
                                                    icon={Package}
                                                    title="No artifacts found"
                                                    description="Try adjusting your filters or run a pipeline to generate artifacts."
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

function StatCardCompact({ icon: Icon, label, value }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-3 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className="text-slate-400" />
                <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
            </div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">
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
