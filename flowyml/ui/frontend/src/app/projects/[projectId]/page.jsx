import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchApi } from '../../../utils/api';
import {
    LayoutDashboard,
    GitBranch,
    PlayCircle,
    FlaskConical,
    BarChart2,
    Settings,
    Package,
    HardDrive,
    Activity,
    Box,
    Database,
    Clock
} from 'lucide-react';
import { AssetTreeHierarchy } from '../../../components/AssetTreeHierarchy';
import { AssetDetailsPanel } from '../../../components/AssetDetailsPanel';
import { ProjectHeader } from './_components/ProjectHeader';
import { ProjectMetricsPanel } from './_components/ProjectMetricsPanel';
import { ProjectExperimentsList } from './_components/ProjectExperimentsList';
import { ProjectRunsList } from './_components/ProjectRunsList';
import { ProjectPipelinesList } from './_components/ProjectPipelinesList';
import { ErrorBoundary } from '../../../components/ui/ErrorBoundary';
import { Card } from '../../../components/ui/Card';
import { motion, AnimatePresence } from 'framer-motion';

export function ProjectDetails() {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeView, setActiveView] = useState('overview');
    const [selectedAsset, setSelectedAsset] = useState(null);

    useEffect(() => {
        const fetchProjectDetails = async () => {
            try {
                const response = await fetchApi(`/api/projects/${projectId}`);
                const projectData = await response.json();

                // Ensure pipelines is an array
                if (projectData.pipelines && !Array.isArray(projectData.pipelines)) {
                    projectData.pipelines = [];
                }
                setProject(projectData);

                // Fetch stats
                const [runsRes, artifactsRes, experimentsRes] = await Promise.all([
                    fetchApi(`/api/runs?project=${projectId}&limit=1000`),
                    fetchApi(`/api/assets?project=${projectId}&limit=1000`),
                    fetchApi(`/api/experiments?project=${projectId}`)
                ]);

                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();
                const experimentsData = await experimentsRes.json();

                const runs = Array.isArray(runsData?.runs) ? runsData.runs : [];
                const artifacts = Array.isArray(artifactsData?.assets) ? artifactsData.assets : [];
                const experiments = Array.isArray(experimentsData?.experiments) ? experimentsData.experiments : [];

                const pipelineNames = new Set(runs.map(r => r.pipeline_name).filter(Boolean));
                const models = artifacts.filter(a => a.type === 'Model');

                setStats({
                    runs: runs.length,
                    pipelines: pipelineNames.size,
                    artifacts: artifacts.length,
                    models: models.length,
                    experiments: experiments.length,
                    total_storage_bytes: artifacts.reduce((acc, curr) => acc + (curr.size_bytes || 0), 0)
                });

            } catch (error) {
                console.error('Failed to fetch project details:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchProjectDetails();
        }
    }, [projectId]);

    const handleAssetSelect = (asset) => {
        setSelectedAsset(asset);
        // We don't change activeView, just show the asset details panel overlay or replacement
    };

    const renderContent = () => {
        if (selectedAsset) {
            return (
                <AssetDetailsPanel
                    asset={selectedAsset}
                    onClose={() => setSelectedAsset(null)}
                />
            );
        }

        switch (activeView) {
            case 'overview':
                return (
                    <div className="space-y-6">
                        {/* Quick Stats Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard
                                icon={Activity}
                                label="Total Runs"
                                value={stats?.runs || 0}
                                color="text-blue-500"
                                bg="bg-blue-50 dark:bg-blue-900/20"
                            />
                            <StatCard
                                icon={Box}
                                label="Models"
                                value={stats?.models || 0}
                                color="text-purple-500"
                                bg="bg-purple-50 dark:bg-purple-900/20"
                            />
                            <StatCard
                                icon={FlaskConical}
                                label="Experiments"
                                value={stats?.experiments || 0}
                                color="text-pink-500"
                                bg="bg-pink-50 dark:bg-pink-900/20"
                            />
                            <StatCard
                                icon={HardDrive}
                                label="Storage"
                                value={formatBytes(stats?.total_storage_bytes || 0)}
                                color="text-slate-500"
                                bg="bg-slate-50 dark:bg-slate-800"
                            />
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <Card className="p-0 overflow-hidden border-slate-200 dark:border-slate-800">
                                <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                        <GitBranch size={16} className="text-slate-400" />
                                        Recent Pipelines
                                    </h3>
                                    <button
                                        onClick={() => setActiveView('pipelines')}
                                        className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                                    >
                                        View All
                                    </button>
                                </div>
                                <div className="p-4">
                                    <ProjectPipelinesList projectId={projectId} limit={5} compact />
                                </div>
                            </Card>

                            <Card className="p-0 overflow-hidden border-slate-200 dark:border-slate-800">
                                <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                        <PlayCircle size={16} className="text-slate-400" />
                                        Recent Runs
                                    </h3>
                                    <button
                                        onClick={() => setActiveView('runs')}
                                        className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                                    >
                                        View All
                                    </button>
                                </div>
                                <div className="p-4">
                                    <ProjectRunsList projectId={projectId} limit={5} compact />
                                </div>
                            </Card>
                        </div>

                        <Card className="p-0 overflow-hidden border-slate-200 dark:border-slate-800">
                            <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
                                <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                    <BarChart2 size={16} className="text-slate-400" />
                                    Production Metrics
                                </h3>
                            </div>
                            <div className="p-4">
                                <ProjectMetricsPanel projectId={projectId} />
                            </div>
                        </Card>
                    </div>
                );
            case 'pipelines':
                return <ProjectPipelinesList projectId={projectId} />;
            case 'runs':
                return <ProjectRunsList projectId={projectId} />;
            case 'experiments':
                return <ProjectExperimentsList projectId={projectId} />;
            case 'metrics':
                return <ProjectMetricsPanel projectId={projectId} />;
            default:
                return null;
        }
    };

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <ProjectHeader project={project} stats={stats} loading={loading} />
            </div>

            {/* Main Layout */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-[1800px] mx-auto px-6 py-6">
                    <div className="h-full flex gap-6">
                        {/* Left Sidebar */}
                        <div className="w-[380px] shrink-0 flex flex-col gap-4 overflow-y-auto pb-6">
                            {/* Navigation Menu */}
                            <nav className="space-y-1">
                                <NavButton
                                    active={activeView === 'overview' && !selectedAsset}
                                    onClick={() => { setActiveView('overview'); setSelectedAsset(null); }}
                                    icon={LayoutDashboard}
                                    label="Overview"
                                />
                                <NavButton
                                    active={activeView === 'pipelines' && !selectedAsset}
                                    onClick={() => { setActiveView('pipelines'); setSelectedAsset(null); }}
                                    icon={GitBranch}
                                    label="Pipelines"
                                />
                                <NavButton
                                    active={activeView === 'runs' && !selectedAsset}
                                    onClick={() => { setActiveView('runs'); setSelectedAsset(null); }}
                                    icon={PlayCircle}
                                    label="Runs"
                                />
                                <NavButton
                                    active={activeView === 'experiments' && !selectedAsset}
                                    onClick={() => { setActiveView('experiments'); setSelectedAsset(null); }}
                                    icon={FlaskConical}
                                    label="Experiments"
                                />
                                <NavButton
                                    active={activeView === 'metrics' && !selectedAsset}
                                    onClick={() => { setActiveView('metrics'); setSelectedAsset(null); }}
                                    icon={BarChart2}
                                    label="Metrics"
                                />
                            </nav>

                            {/* Hierarchy Tree */}
                            <div className="flex-1 min-h-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col shadow-sm">
                                <div className="p-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Project Assets</h3>
                                </div>
                                <div className="flex-1 overflow-y-auto p-2">
                                    <AssetTreeHierarchy
                                        projectId={projectId}
                                        onAssetSelect={handleAssetSelect}
                                        compact={true}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Right Content Area */}
                        <div className="flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col shadow-sm">
                            <div className="flex-1 overflow-y-auto p-6">
                                <ErrorBoundary>
                                    <AnimatePresence mode="wait">
                                        <motion.div
                                            key={selectedAsset ? 'asset' : activeView}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                            transition={{ duration: 0.2 }}
                                            className="h-full"
                                        >
                                            {renderContent()}
                                        </motion.div>
                                    </AnimatePresence>
                                </ErrorBoundary>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function NavButton({ active, onClick, icon: Icon, label }) {
    return (
        <button
            onClick={onClick}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${active
                ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
                }`}
        >
            <Icon size={18} className={active ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400'} />
            {label}
        </button>
    );
}

function StatCard({ icon: Icon, label, value, color, bg }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-4">
            <div className={`p-3 rounded-lg ${bg}`}>
                <Icon size={20} className={color} />
            </div>
            <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white">{typeof value === 'number' ? value.toLocaleString() : value}</p>
            </div>
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
