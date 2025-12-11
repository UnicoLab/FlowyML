'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { fetchApi } from '../../utils/api';
import { downloadArtifactById } from '../../utils/downloads';
import { Link } from 'react-router-dom';
import {
    Database, Box, BarChart2, FileText, Search, Filter, Calendar, Package,
    Download, Eye, X, ArrowRight, Network, Activity, HardDrive, List,
    Grid, ChevronDown, ChevronRight, Folder, FolderOpen, FileBox, Clock,
    Layers, GitBranch, CheckCircle, XCircle, RefreshCw, SlidersHorizontal,
    TrendingUp, Zap, Hash, MoreHorizontal, ExternalLink, Copy, Trash2,
    Star, Bookmark, ArrowUpDown, LayoutGrid, Maximize2, Minimize2, GripVertical
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format, formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { useProject } from '../../contexts/ProjectContext';
import { EmptyState } from '../../components/ui/EmptyState';
import { AssetDetailsPanel } from '../../components/AssetDetailsPanel';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';

// Type configuration with icons and colors
const TYPE_CONFIG = {
    Model: {
        icon: Box,
        color: 'text-purple-500',
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        gradient: 'from-purple-500 to-pink-500',
        borderColor: 'border-purple-200 dark:border-purple-800',
        label: 'Models'
    },
    Dataset: {
        icon: Database,
        color: 'text-blue-500',
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        gradient: 'from-blue-500 to-cyan-500',
        borderColor: 'border-blue-200 dark:border-blue-800',
        label: 'Datasets'
    },
    Metrics: {
        icon: BarChart2,
        color: 'text-emerald-500',
        bg: 'bg-emerald-50 dark:bg-emerald-900/20',
        gradient: 'from-emerald-500 to-teal-500',
        borderColor: 'border-emerald-200 dark:border-emerald-800',
        label: 'Metrics'
    },
    FeatureSet: {
        icon: Layers,
        color: 'text-amber-500',
        bg: 'bg-amber-50 dark:bg-amber-900/20',
        gradient: 'from-amber-500 to-orange-500',
        borderColor: 'border-amber-200 dark:border-amber-800',
        label: 'Features'
    },
    default: {
        icon: FileText,
        color: 'text-slate-500',
        bg: 'bg-slate-50 dark:bg-slate-800',
        gradient: 'from-slate-500 to-slate-600',
        borderColor: 'border-slate-200 dark:border-slate-700',
        label: 'Other'
    }
};

const getTypeConfig = (type) => TYPE_CONFIG[type] || TYPE_CONFIG.default;

export function Assets() {
    const [assets, setAssets] = useState([]);
    const [runs, setRuns] = useState([]);
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [typeFilter, setTypeFilter] = useState('all');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [viewMode, setViewMode] = useState('table');
    const [sortConfig, setSortConfig] = useState({ key: 'created_at', direction: 'desc' });
    const [detailsPanelExpanded, setDetailsPanelExpanded] = useState(false);
    const [stats, setStats] = useState(null);
    const [expandedProjects, setExpandedProjects] = useState({});
    const [expandedPipelines, setExpandedPipelines] = useState({});
    const [expandedRuns, setExpandedRuns] = useState({});
    const [showExplorer, setShowExplorer] = useState(true);
    const [hideListWhenDetails, setHideListWhenDetails] = useState(false);
    const { selectedProject } = useProject();

    // Fetch all data
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const baseUrl = selectedProject ? `&project=${encodeURIComponent(selectedProject)}` : '';
                const [assetsRes, runsRes, pipelinesRes, statsRes] = await Promise.all([
                    fetchApi(`/api/assets/?limit=500${baseUrl.replace('&', '?')}`),
                    fetchApi(`/api/runs?limit=200${baseUrl}`),
                    fetchApi(`/api/pipelines?limit=100${baseUrl}`),
                    fetchApi(`/api/assets/stats${baseUrl.replace('&', '?')}`)
                ]);

                const [assetsData, runsData, pipelinesData, statsData] = await Promise.all([
                    assetsRes.json(),
                    runsRes.json(),
                    pipelinesRes.json(),
                    statsRes.ok ? statsRes.json() : null
                ]);

                setAssets(assetsData.assets || []);
                setRuns(runsData.runs || []);
                setPipelines(pipelinesData.pipelines || []);
                setStats(statsData);

                // Auto-expand first project
                const projects = [...new Set((assetsData.assets || []).map(a => a.project).filter(Boolean))];
                if (projects.length > 0) {
                    setExpandedProjects({ [projects[0]]: true });
                }
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [selectedProject]);

    // Get unique types with counts
    const typeCounts = useMemo(() => {
        const counts = { all: assets.length };
        assets.forEach(a => {
            counts[a.type] = (counts[a.type] || 0) + 1;
        });
        return counts;
    }, [assets]);

    // Filter and sort assets
    const filteredAssets = useMemo(() => {
        let result = assets.filter(asset => {
            const matchesType = typeFilter === 'all' || asset.type === typeFilter;
            const matchesSearch = !searchQuery ||
                asset.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                asset.step?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                asset.pipeline_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                asset.project?.toLowerCase().includes(searchQuery.toLowerCase());
            return matchesType && matchesSearch;
        });

        // Sort
        result.sort((a, b) => {
            let aVal = a[sortConfig.key];
            let bVal = b[sortConfig.key];

            if (sortConfig.key === 'created_at') {
                aVal = new Date(aVal || 0).getTime();
                bVal = new Date(bVal || 0).getTime();
            }

            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });

        return result;
    }, [assets, typeFilter, searchQuery, sortConfig]);

    // Group assets by hierarchy
    const hierarchy = useMemo(() => {
        const projects = {};

        assets.forEach(asset => {
            const projectName = asset.project || 'Unassigned';
            const pipelineName = asset.pipeline_name || 'Direct';
            const runId = asset.run_id || 'unknown';

            if (!projects[projectName]) {
                projects[projectName] = { pipelines: {}, count: 0 };
            }
            if (!projects[projectName].pipelines[pipelineName]) {
                projects[projectName].pipelines[pipelineName] = { runs: {}, count: 0 };
            }
            if (!projects[projectName].pipelines[pipelineName].runs[runId]) {
                projects[projectName].pipelines[pipelineName].runs[runId] = [];
            }

            projects[projectName].pipelines[pipelineName].runs[runId].push(asset);
            projects[projectName].pipelines[pipelineName].count++;
            projects[projectName].count++;
        });

        return projects;
    }, [assets]);

    const handleSort = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
        }));
    };

    const toggleProject = (name) => {
        setExpandedProjects(prev => ({ ...prev, [name]: !prev[name] }));
    };

    const togglePipeline = (projectName, pipelineName) => {
        const key = `${projectName}-${pipelineName}`;
        setExpandedPipelines(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const toggleRun = (projectName, pipelineName, runId) => {
        const key = `${projectName}-${pipelineName}-${runId}`;
        setExpandedRuns(prev => ({ ...prev, [key]: !prev[key] }));
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                    <p className="text-slate-500 dark:text-slate-400">Loading assets...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="text-center p-8 bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-200 dark:border-red-800 max-w-md">
                    <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-red-700 dark:text-red-300 mb-2">Failed to load assets</h3>
                    <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2 mx-auto"
                    >
                        <RefreshCw size={16} /> Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-gradient-to-br from-slate-50 via-slate-50 to-blue-50/30 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
            {/* Header */}
            <header className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-lg border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="flex items-center justify-between gap-6 max-w-[2000px] mx-auto">
                    {/* Title & Stats */}
                    <div className="flex items-center gap-6">
                    <div>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                                <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl text-white">
                                    <Package size={24} />
                                </div>
                                Asset Explorer
                            </h1>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                Browse, search, and manage all pipeline artifacts
                            </p>
                        </div>

                        {/* Quick Stats */}
                        <div className="hidden lg:flex items-center gap-3 pl-6 border-l border-slate-200 dark:border-slate-700">
                            <StatBadge icon={Package} value={stats?.total_assets || assets.length} label="Total" />
                            <StatBadge icon={Box} value={typeCounts.Model || 0} label="Models" color="purple" />
                            <StatBadge icon={Database} value={typeCounts.Dataset || 0} label="Datasets" color="blue" />
                            <StatBadge icon={BarChart2} value={typeCounts.Metrics || 0} label="Metrics" color="emerald" />
                        </div>
                    </div>

                    {/* Search & Controls */}
                    <div className="flex items-center gap-3">
                        {/* Search */}
                        <div className="relative">
                            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search assets..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-64 pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-700 border-0 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                            />
                            {searchQuery && (
                                <button
                                    onClick={() => setSearchQuery('')}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                >
                                    <X size={14} />
                                </button>
                            )}
                        </div>

                        {/* View Mode Toggle */}
                        <div className="flex items-center bg-slate-100 dark:bg-slate-700 rounded-xl p-1">
                            <button
                                onClick={() => setViewMode('table')}
                                className={`p-2 rounded-lg transition-all ${viewMode === 'table'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                }`}
                                title="Table View"
                            >
                                <List size={18} />
                            </button>
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-2 rounded-lg transition-all ${viewMode === 'grid'
                                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                                title="Grid View"
                            >
                                <LayoutGrid size={18} />
                            </button>
                        </div>

                        {/* Explorer Toggle */}
                        <button
                            onClick={() => setShowExplorer(!showExplorer)}
                            className={`p-2 rounded-xl transition-all ${showExplorer
                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-500'
                            }`}
                            title={showExplorer ? 'Hide Explorer' : 'Show Explorer'}
                        >
                            <FolderOpen size={18} />
                        </button>
                    </div>
                </div>
            </header>

            {/* Type Filters */}
            <div className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 px-6 py-3 shrink-0">
                <div className="flex items-center gap-2 max-w-[2000px] mx-auto overflow-x-auto scrollbar-hide">
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0 mr-2">
                        <Filter size={14} className="inline mr-1" />
                        Filter:
                    </span>
                    {Object.entries({ all: 'All', ...Object.fromEntries(Object.keys(typeCounts).filter(k => k !== 'all').map(k => [k, k])) }).map(([key, label]) => {
                        const config = getTypeConfig(key);
                        const isActive = typeFilter === key;
                        const count = typeCounts[key] || 0;
                        const Icon = config.icon;

                        return (
                            <button
                                key={key}
                                onClick={() => setTypeFilter(key)}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap ${isActive
                                    ? `bg-gradient-to-r ${config.gradient} text-white shadow-md`
                                    : `${config.bg} ${config.color} hover:shadow-sm`
                                }`}
                            >
                                {key !== 'all' && <Icon size={14} />}
                                <span>{label}</span>
                                <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${isActive ? 'bg-white/20' : 'bg-black/5 dark:bg-white/10'}`}>
                                    {count}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden flex">
                {/* Explorer Sidebar */}
                <AnimatePresence>
                    {showExplorer && (
                        <motion.aside
                            initial={{ width: 0, opacity: 0 }}
                            animate={{ width: 320, opacity: 1 }}
                            exit={{ width: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="h-full border-r border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm overflow-hidden shrink-0"
                        >
                            <div className="h-full flex flex-col">
                                <div className="p-4 border-b border-slate-100 dark:border-slate-700">
                                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                        <Folder size={16} className="text-blue-500" />
                                        Project Explorer
                                    </h3>
                                </div>

                                <div className="flex-1 overflow-y-auto p-2">
                                    {Object.entries(hierarchy).length === 0 ? (
                                        <div className="text-center py-8 text-slate-500">
                                            <Folder size={32} className="mx-auto mb-2 opacity-50" />
                                            <p className="text-sm">No assets found</p>
                                        </div>
                                    ) : (
                                        Object.entries(hierarchy).map(([projectName, projectData]) => (
                                            <ExplorerProject
                                                key={projectName}
                                                name={projectName}
                                                data={projectData}
                                                expanded={expandedProjects[projectName]}
                                                onToggle={() => toggleProject(projectName)}
                                                expandedPipelines={expandedPipelines}
                                                expandedRuns={expandedRuns}
                                                onTogglePipeline={(p) => togglePipeline(projectName, p)}
                                                onToggleRun={(p, r) => toggleRun(projectName, p, r)}
                                                onAssetSelect={setSelectedAsset}
                                                typeFilter={typeFilter}
                                            />
                                        ))
                                    )}
                                </div>
                            </div>
                        </motion.aside>
                    )}
                </AnimatePresence>

                {/* Content Area with Resizable Panels */}
                <main className="flex-1 min-w-0 overflow-hidden">
                    <PanelGroup direction="horizontal" className="h-full">
                        {/* Asset List Panel - can be hidden when viewing details */}
                        {(!selectedAsset || !hideListWhenDetails) && (
                            <Panel
                                defaultSize={selectedAsset ? (detailsPanelExpanded ? 25 : 35) : 100}
                                minSize={selectedAsset ? 15 : 100}
                                className="overflow-hidden"
                            >
                                <div className="h-full overflow-hidden p-4">
                                    {filteredAssets.length === 0 ? (
                                        <div className="h-full flex items-center justify-center">
                                            <EmptyState
                                                icon={Package}
                                                title="No artifacts found"
                                                description={searchQuery ? `No results for "${searchQuery}"` : "Run a pipeline to generate artifacts"}
                                            />
                                        </div>
                                    ) : viewMode === 'table' ? (
                                        <AssetTable
                                            assets={filteredAssets}
                                            onSelect={setSelectedAsset}
                                            sortConfig={sortConfig}
                                            onSort={handleSort}
                                            selectedAsset={selectedAsset}
                                        />
                                    ) : (
                                        <AssetGrid
                                            assets={filteredAssets}
                                            onSelect={setSelectedAsset}
                                            selectedAsset={selectedAsset}
                                        />
                                    )}
                                </div>
                            </Panel>
                        )}

                        {/* Resizable Handle & Details Panel */}
                        {selectedAsset && (
                            <>
                                {!hideListWhenDetails && (
                                    <PanelResizeHandle className="w-1.5 bg-slate-200 dark:bg-slate-700 hover:bg-blue-400 dark:hover:bg-blue-500 transition-colors flex items-center justify-center group cursor-col-resize">
                                        <div className="w-0.5 h-8 bg-slate-300 dark:bg-slate-600 group-hover:bg-blue-300 dark:group-hover:bg-blue-400 rounded-full" />
                                    </PanelResizeHandle>
                                )}
                                <Panel
                                    defaultSize={hideListWhenDetails ? 100 : (detailsPanelExpanded ? 75 : 65)}
                                    minSize={40}
                                    className="overflow-hidden"
                                >
                                    <div className="h-full overflow-hidden">
                                        <AssetDetailsPanelExpanded
                                            asset={selectedAsset}
                                            onClose={() => setSelectedAsset(null)}
                                            isExpanded={detailsPanelExpanded}
                                            onToggleExpand={() => setDetailsPanelExpanded(!detailsPanelExpanded)}
                                            hideList={hideListWhenDetails}
                                            onToggleHideList={() => setHideListWhenDetails(!hideListWhenDetails)}
                                        />
                                    </div>
                                </Panel>
                            </>
                        )}
                    </PanelGroup>
                </main>
                    </div>
                </div>
    );
}

// Stat Badge Component
function StatBadge({ icon: Icon, value, label, color = 'slate' }) {
    const colors = {
        slate: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
        purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
        blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
        emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
    };

    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${colors[color]}`}>
            <Icon size={14} />
            <span className="font-bold">{typeof value === 'number' ? value.toLocaleString() : value}</span>
            <span className="text-xs opacity-70">{label}</span>
        </div>
    );
}

// Explorer Components
function ExplorerProject({ name, data, expanded, onToggle, expandedPipelines, expandedRuns, onTogglePipeline, onToggleRun, onAssetSelect, typeFilter }) {
    return (
        <div className="mb-1">
            <button
                onClick={onToggle}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
                <motion.div animate={{ rotate: expanded ? 90 : 0 }} transition={{ duration: 0.15 }}>
                    <ChevronRight size={14} className="text-slate-400" />
                </motion.div>
                {expanded ? <FolderOpen size={16} className="text-blue-500" /> : <Folder size={16} className="text-blue-500" />}
                <span className="flex-1 text-left text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                    {name}
                </span>
                <span className="text-xs text-slate-400 bg-slate-100 dark:bg-slate-600 px-2 py-0.5 rounded-full">
                    {data.count}
                </span>
            </button>

            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden pl-4"
                    >
                        {Object.entries(data.pipelines).map(([pipelineName, pipelineData]) => (
                            <ExplorerPipeline
                                key={pipelineName}
                                name={pipelineName}
                                data={pipelineData}
                                projectName={name}
                                expanded={expandedPipelines[`${name}-${pipelineName}`]}
                                expandedRuns={expandedRuns}
                                onToggle={() => onTogglePipeline(pipelineName)}
                                onToggleRun={(r) => onToggleRun(pipelineName, r)}
                                onAssetSelect={onAssetSelect}
                                typeFilter={typeFilter}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function ExplorerPipeline({ name, data, projectName, expanded, expandedRuns, onToggle, onToggleRun, onAssetSelect, typeFilter }) {
    return (
        <div className="mb-0.5">
            <button
                onClick={onToggle}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
                <motion.div animate={{ rotate: expanded ? 90 : 0 }} transition={{ duration: 0.15 }}>
                    <ChevronRight size={12} className="text-slate-400" />
                </motion.div>
                <Activity size={14} className="text-emerald-500" />
                <span className="flex-1 text-left text-xs text-slate-600 dark:text-slate-400 truncate">
                    {name}
                </span>
                <span className="text-[10px] text-slate-400">
                    {data.count}
                </span>
            </button>

            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden pl-4"
                    >
                        {Object.entries(data.runs).map(([runId, assets]) => (
                            <ExplorerRun
                                key={runId}
                                runId={runId}
                                assets={assets}
                                projectName={projectName}
                                pipelineName={name}
                                expanded={expandedRuns[`${projectName}-${name}-${runId}`]}
                                onToggle={() => onToggleRun(runId)}
                                onAssetSelect={onAssetSelect}
                                typeFilter={typeFilter}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function ExplorerRun({ runId, assets, expanded, onToggle, onAssetSelect, typeFilter }) {
    const filteredAssets = typeFilter === 'all' ? assets : assets.filter(a => a.type === typeFilter);

    return (
        <div className="mb-0.5">
            <button
                onClick={onToggle}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
                <motion.div animate={{ rotate: expanded ? 90 : 0 }} transition={{ duration: 0.15 }}>
                    <ChevronRight size={10} className="text-slate-400" />
                </motion.div>
                <GitBranch size={12} className="text-slate-400" />
                <span className="flex-1 text-left text-[10px] font-mono text-slate-500 truncate">
                    {runId?.substring(0, 12) || 'unknown'}
                </span>
                <span className="text-[10px] text-slate-400">
                    {filteredAssets.length}
                </span>
            </button>

            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden pl-4"
                    >
                        {filteredAssets.map(asset => {
                            const config = getTypeConfig(asset.type);
                            const Icon = config.icon;
                            return (
                                <button
                                    key={asset.artifact_id}
                                    onClick={() => onAssetSelect(asset)}
                                    className="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group"
                                >
                                    <Icon size={12} className={config.color} />
                                    <span className="flex-1 text-left text-[11px] text-slate-600 dark:text-slate-400 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                        {asset.name}
                                    </span>
                                </button>
                            );
                        })}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// Table Component
function AssetTable({ assets, onSelect, sortConfig, onSort, selectedAsset }) {
    return (
        <div className="h-full flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
            {/* Table Header */}
            <div className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 px-4 py-3 grid grid-cols-[80px,1fr,120px,200px,140px,140px,100px,50px] gap-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <div>Type</div>
                <SortableHeader label="Name" sortKey="name" sortConfig={sortConfig} onSort={onSort} />
                <div>Step</div>
                <div>Details</div>
                <SortableHeader label="Pipeline" sortKey="pipeline_name" sortConfig={sortConfig} onSort={onSort} />
                <div>Run</div>
                <SortableHeader label="Created" sortKey="created_at" sortConfig={sortConfig} onSort={onSort} />
                <div></div>
            </div>

            {/* Table Body */}
            <div className="flex-1 overflow-y-auto">
                {assets.map((asset, index) => (
                    <AssetRow
                        key={asset.artifact_id || index}
                        asset={asset}
                        onSelect={onSelect}
                        isEven={index % 2 === 0}
                        isSelected={selectedAsset?.artifact_id === asset.artifact_id}
                    />
                ))}
            </div>
        </div>
    );
}

function SortableHeader({ label, sortKey, sortConfig, onSort }) {
    const isActive = sortConfig.key === sortKey;
    return (
        <button
            onClick={() => onSort(sortKey)}
            className="flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
        >
            {label}
            <ArrowUpDown size={12} className={isActive ? 'text-blue-500' : 'opacity-30'} />
        </button>
    );
}

function AssetRow({ asset, onSelect, isEven, isSelected }) {
    const config = getTypeConfig(asset.type);
    const Icon = config.icon;
    const props = asset.properties || {};

    const getQuickInfo = () => {
        if (asset.type === 'Model') {
            const parts = [];
            if (props.framework) parts.push(props.framework);
            if (props.parameters) {
                const p = props.parameters;
                parts.push(p >= 1000000 ? `${(p/1000000).toFixed(1)}M params` : p >= 1000 ? `${(p/1000).toFixed(0)}K params` : `${p} params`);
            }
            return parts.join(' • ') || '-';
        }
        if (asset.type === 'Dataset') {
            const parts = [];
            const samples = props.samples || props.num_samples;
            if (samples) parts.push(`${samples.toLocaleString()} rows`);
            if (props.num_features) parts.push(`${props.num_features} cols`);
            return parts.join(' • ') || '-';
        }
        if (asset.type === 'Metrics') {
            const metricKeys = Object.keys(props).filter(k => !k.startsWith('_') && typeof props[k] === 'number').slice(0, 2);
            return metricKeys.map(k => `${k}: ${props[k] < 0.01 ? props[k].toExponential(1) : props[k].toFixed(3)}`).join(' • ') || '-';
        }
        return '-';
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={() => onSelect(asset)}
            className={`px-4 py-3 grid grid-cols-[80px,1fr,120px,200px,140px,140px,100px,50px] gap-4 items-center cursor-pointer transition-colors border-b border-slate-100 dark:border-slate-700/50 group ${
                isSelected
                    ? 'bg-blue-100 dark:bg-blue-900/40 border-l-4 border-l-blue-500'
                    : `hover:bg-blue-50 dark:hover:bg-blue-900/20 ${isEven ? '' : 'bg-slate-50/50 dark:bg-slate-800/30'}`
            }`}
        >
            {/* Type */}
            <div className={`flex items-center gap-2 px-2 py-1 rounded-lg w-fit ${config.bg}`}>
                <Icon size={14} className={config.color} />
                <span className={`text-xs font-medium ${config.color}`}>{asset.type}</span>
            </div>

            {/* Name */}
            <div className="truncate">
                <span className="font-medium text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {asset.name}
                </span>
            </div>

            {/* Step */}
            <span className="text-xs font-mono text-slate-500 truncate">
                {asset.step || '-'}
            </span>

            {/* Details */}
            <span className="text-xs text-slate-500 truncate">
                {getQuickInfo()}
            </span>

            {/* Pipeline */}
            <span className="text-xs text-slate-600 dark:text-slate-400 truncate">
                {asset.pipeline_name || '-'}
            </span>

            {/* Run */}
            {asset.run_id ? (
                <Link
                    to={`/runs/${asset.run_id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs font-mono text-blue-600 hover:underline truncate"
                >
                    {asset.run_id?.substring(0, 12)}
                </Link>
            ) : (
                <span className="text-xs text-slate-400">-</span>
            )}

            {/* Created */}
            <span className="text-xs text-slate-500">
                {asset.created_at ? formatDistanceToNow(new Date(asset.created_at), { addSuffix: true }).replace('about ', '') : '-'}
            </span>

            {/* Actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                    onClick={(e) => { e.stopPropagation(); onSelect(asset); }}
                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
                    title="View Details"
                >
                    <Eye size={14} className="text-slate-500" />
                </button>
                <button
                    onClick={(e) => { e.stopPropagation(); downloadArtifactById(asset.artifact_id); }}
                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded"
                    title="Download"
                >
                    <Download size={14} className="text-slate-500" />
                </button>
            </div>
        </motion.div>
    );
}

// Grid Component
function AssetGrid({ assets, onSelect, selectedAsset }) {
    return (
        <div className="h-full overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 p-1">
                {assets.map((asset, index) => (
                    <AssetCard
                        key={asset.artifact_id || index}
                        asset={asset}
                        onSelect={onSelect}
                        isSelected={selectedAsset?.artifact_id === asset.artifact_id}
                    />
                ))}
            </div>
        </div>
    );
}

function AssetCard({ asset, onSelect, isSelected }) {
    const config = getTypeConfig(asset.type);
    const Icon = config.icon;
    const props = asset.properties || {};

    const getQuickStats = () => {
        if (asset.type === 'Model') {
            return {
                primary: props.framework || 'Unknown',
                secondary: props.parameters ? (props.parameters >= 1000000 ? `${(props.parameters/1000000).toFixed(1)}M` : `${(props.parameters/1000).toFixed(0)}K`) : null,
                label: 'params'
            };
        }
        if (asset.type === 'Dataset') {
            return {
                primary: (props.samples || props.num_samples)?.toLocaleString() || '?',
                secondary: props.num_features,
                label: props.num_features ? 'cols' : 'rows'
            };
        }
        if (asset.type === 'Metrics') {
            const metricKey = Object.keys(props).find(k => !k.startsWith('_') && typeof props[k] === 'number');
            return metricKey ? {
                primary: props[metricKey] < 0.01 ? props[metricKey].toExponential(1) : props[metricKey].toFixed(3),
                secondary: null,
                label: metricKey
            } : { primary: '-', secondary: null, label: '' };
        }
        return { primary: '-', secondary: null, label: '' };
    };

    const stats = getQuickStats();

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ y: -4, scale: 1.02 }}
            transition={{ duration: 0.2 }}
        >
            <Card
                onClick={() => onSelect(asset)}
                className={`cursor-pointer group relative overflow-hidden bg-white dark:bg-slate-800 transition-all ${
                    isSelected
                        ? 'border-2 border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800 shadow-xl'
                        : 'border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg'
                }`}
            >
                {/* Gradient Background */}
                <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-5 group-hover:opacity-10 transition-opacity`} />

                <div className="relative p-4">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                        <div className={`p-2.5 rounded-xl bg-gradient-to-br ${config.gradient} text-white shadow-lg group-hover:shadow-xl transition-shadow`}>
                            <Icon size={20} />
                        </div>
                        <Badge variant="outline" className={`text-[10px] px-2 py-0.5 ${config.borderColor} ${config.color}`}>
                            {asset.type}
                        </Badge>
                    </div>

                    {/* Name */}
                    <h4 className="font-semibold text-slate-900 dark:text-white mb-2 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {asset.name}
                    </h4>

                    {/* Quick Stats */}
                    <div className={`${config.bg} rounded-lg p-2 mb-3`}>
                        <div className="flex items-baseline gap-1.5">
                            <span className={`text-lg font-bold ${config.color}`}>
                                {stats.primary}
                            </span>
                            {stats.secondary && (
                                <span className="text-xs text-slate-500">
                                    × {stats.secondary}
                                </span>
                            )}
                            <span className="text-[10px] text-slate-500 ml-auto">
                                {stats.label}
                            </span>
                        </div>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span className="truncate max-w-[100px]">{asset.step || 'N/A'}</span>
                        <span>{asset.created_at ? format(new Date(asset.created_at), 'MMM d') : '-'}</span>
                    </div>

                    {/* Run ID */}
                    {asset.run_id && (
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                            <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
                                {asset.run_id?.substring(0, 10)}
                            </span>
                        </div>
                    )}
                </div>
            </Card>
        </motion.div>
    );
}

// Expanded Details Panel Wrapper with controls
function AssetDetailsPanelExpanded({ asset, onClose, isExpanded, onToggleExpand, hideList, onToggleHideList }) {
    const config = getTypeConfig(asset.type);
    const Icon = config.icon;

    return (
        <div className="h-full flex flex-col bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700">
            {/* Custom Header with expand controls */}
            <div className={`bg-gradient-to-r ${config.gradient} p-4`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-white/20 backdrop-blur-sm rounded-xl">
                            <Icon size={24} className="text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white truncate max-w-[400px]">
                                {asset.name}
                            </h2>
                            <p className="text-white/80 text-sm">
                                {asset.type} • {asset.step || 'No step'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Toggle hide list button */}
                        <button
                            onClick={onToggleHideList}
                            className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                            title={hideList ? "Show list" : "Hide list for full view"}
                        >
                            {hideList ? <Minimize2 size={18} className="text-white" /> : <Maximize2 size={18} className="text-white" />}
                        </button>
                        <Button
                            onClick={onToggleExpand}
                            variant="ghost"
                            size="sm"
                            className="text-white/80 hover:text-white hover:bg-white/20"
                            title={isExpanded ? "Collapse panel" : "Expand panel"}
                        >
                            {isExpanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                        </Button>
                        <Button
                            onClick={onClose}
                            variant="ghost"
                            size="sm"
                            className="text-white/80 hover:text-white hover:bg-white/20"
                        >
                            <X size={18} />
                        </Button>
                    </div>
                </div>
            </div>

            {/* Content - use the existing AssetDetailsPanel but without header */}
            <div className="flex-1 overflow-hidden">
                <AssetDetailsPanel
                    asset={asset}
                    onClose={onClose}
                    hideHeader={true}
                />
            </div>
        </div>
    );
}
