import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import {
    ChevronRight,
    ChevronDown,
    Box,
    Activity,
    PlayCircle,
    FileBox,
    CheckCircle,
    XCircle,
    Clock,
    Database,
    Layers,
    X,
    Download,
    Info,
    BarChart2,
    FileText,
    Eye,
    Folder,
    GitBranch
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '../utils/date';
import { downloadArtifactById } from '../utils/downloads';
import { motion, AnimatePresence } from 'framer-motion';

const StatusIcon = ({ status }) => {
    switch (status?.toLowerCase()) {
        case 'completed':
        case 'success':
            return <CheckCircle className="w-4 h-4 text-green-500" />;
        case 'failed':
            return <XCircle className="w-4 h-4 text-red-500" />;
        case 'running':
            return <Activity className="w-4 h-4 text-blue-500 animate-spin" />;
        default:
            return <Clock className="w-4 h-4 text-slate-400" />;
    }
};

const ArtifactIcon = ({ type }) => {
    const iconProps = { className: "w-4 h-4" };

    switch (type?.toLowerCase()) {
        case 'model':
            return <Box {...iconProps} className="w-4 h-4 text-purple-500" />;
        case 'dataset':
        case 'data':
            return <Database {...iconProps} className="w-4 h-4 text-blue-500" />;
        case 'metrics':
            return <BarChart2 {...iconProps} className="w-4 h-4 text-emerald-500" />;
        default:
            return <FileBox {...iconProps} className="w-4 h-4 text-slate-400" />;
    }
};

const TreeNode = ({
    label,
    icon: Icon,
    children,
    defaultExpanded = false,
    actions,
    status,
    level = 0,
    badge,
    onClick
}) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);
    const hasChildren = children && children.length > 0;

    return (
        <div className="select-none">
            <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={`
                    flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all
                    hover:bg-slate-100 dark:hover:bg-slate-800
                    ${level === 0 ? 'bg-slate-50 dark:bg-slate-800/50 mb-1 font-semibold' : ''}
                `}
                style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
                onClick={() => {
                    if (hasChildren) {
                        setIsExpanded(!isExpanded);
                    }
                    onClick?.();
                }}
            >
                <div className="flex items-center gap-1 text-slate-400">
                    {hasChildren ? (
                        <motion.div
                            animate={{ rotate: isExpanded ? 90 : 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <ChevronRight className="w-4 h-4" />
                        </motion.div>
                    ) : (
                        <div className="w-4" />
                    )}
                </div>

                {Icon && <Icon className={`w-4 h-4 ${level === 0 ? 'text-blue-500' : 'text-slate-500 dark:text-slate-400'}`} />}

                <div className="flex-1 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                        <span className={`text-sm truncate ${level === 0
                            ? 'font-semibold text-slate-900 dark:text-white'
                            : 'text-slate-700 dark:text-slate-300'
                            }`}>
                            {label}
                        </span>
                        {badge}
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                        {status && <StatusIcon status={status} />}
                        {actions}
                    </div>
                </div>
            </motion.div>

            <AnimatePresence>
                {isExpanded && hasChildren && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export function AssetTreeHierarchy({ projectId, onAssetSelect }) {
    const [data, setData] = useState({ projects: [], pipelines: [], runs: [], artifacts: [] });
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [assetTypeFilter, setAssetTypeFilter] = useState('all'); // 'all', 'model', 'dataset'

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Determine what to fetch based on projectId
                const endpoints = projectId
                    ? [
                        fetchApi(`/api/pipelines?project=${projectId}`),
                        fetchApi(`/api/runs?project=${projectId}&limit=200`),
                        fetchApi(`/api/assets?project=${projectId}&limit=500`)
                    ]
                    : [
                        fetchApi('/api/pipelines?limit=100'),
                        fetchApi('/api/runs?limit=200'),
                        fetchApi('/api/assets?limit=500')
                    ];

                const [pipelinesRes, runsRes, artifactsRes] = await Promise.all(endpoints);

                const pipelinesData = await pipelinesRes.json();
                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();

                // If no projectId, group by projects
                let projects = [];
                if (!projectId) {
                    const artifactProjects = new Set(
                        (artifactsData?.assets || []).map(a => a.project).filter(Boolean)
                    );
                    const runProjects = new Set(
                        (runsData?.runs || []).map(r => r.project).filter(Boolean)
                    );
                    projects = [...new Set([...artifactProjects, ...runProjects])].map(name => ({ name }));
                }

                setData({
                    projects,
                    pipelines: Array.isArray(pipelinesData?.pipelines) ? pipelinesData.pipelines : [],
                    runs: Array.isArray(runsData?.runs) ? runsData.runs : [],
                    artifacts: Array.isArray(artifactsData?.assets) ? artifactsData.assets : []
                });
            } catch (error) {
                console.error('Failed to fetch hierarchy data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [projectId]);

    if (loading) {
        return (
            <div className="h-[600px] w-full bg-slate-50 dark:bg-slate-800/50 rounded-xl animate-pulse flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                    <p className="text-slate-600 dark:text-slate-400">Loading assets hierarchy...</p>
                </div>
            </div>
        );
    }

    // Filter functions
    const getRunsForPipeline = (pipelineName, projectName = null) => {
        return data.runs.filter(r =>
            r.pipeline_name === pipelineName &&
            (!projectName || r.project === projectName)
        );
    };

    const getArtifactsForRun = (runId) => {
        let artifacts = data.artifacts.filter(a => a.run_id === runId);

        // Apply asset type filter
        if (assetTypeFilter !== 'all') {
            artifacts = artifacts.filter(a => a.type?.toLowerCase() === assetTypeFilter);
        }

        return artifacts;
    };

    const getPipelinesForProject = (projectName) => {
        const projectRuns = data.runs.filter(r => r.project === projectName);
        const pipelineNames = [...new Set(projectRuns.map(r => r.pipeline_name))];
        return data.pipelines.filter(p => pipelineNames.includes(p.name));
    };

    // Build hierarchy based on whether we have a single project or multiple
    const renderContent = () => {
        if (projectId || data.projects.length === 0) {
            // Single project view or no projects - show pipelines directly
            return data.pipelines.map((pipeline, idx) => {
                const runs = getRunsForPipeline(pipeline.name, projectId);
                return renderPipeline(pipeline, runs, 0, idx < 3); // Expand first 3 pipelines
            });
        } else {
            // Multiple projects - group by project
            return data.projects.map((project, projIdx) => {
                const pipelines = getPipelinesForProject(project.name);

                return (
                    <TreeNode
                        key={project.name}
                        label={project.name}
                        icon={Folder}
                        level={0}
                        defaultExpanded={projIdx === 0} // Expand first project
                        badge={
                            <span className="text-xs text-slate-400">
                                {pipelines.length} pipeline{pipelines.length !== 1 ? 's' : ''}
                            </span>
                        }
                    >
                        {pipelines.map((pipeline, idx) => {
                            const runs = getRunsForPipeline(pipeline.name, project.name);
                            return renderPipeline(pipeline, runs, 1, projIdx === 0 && idx < 2); // Expand first 2 pipelines of first project
                        })}
                    </TreeNode>
                );
            });
        }
    };

    const renderPipeline = (pipeline, runs, baseLevel, defaultExpanded = false) => {
        const totalArtifacts = runs.reduce((sum, run) => {
            return sum + getArtifactsForRun(run.run_id).length;
        }, 0);

        return (
            <TreeNode
                key={pipeline.name}
                label={pipeline.name}
                icon={Activity}
                level={baseLevel}
                defaultExpanded={defaultExpanded} // Use the parameter
                badge={
                    <div className="flex gap-1">
                        {totalArtifacts > 0 && (
                            <span className="flex items-center gap-0.5 text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-1.5 py-0.5 rounded-full">
                                <FileBox className="w-3 h-3" /> {totalArtifacts}
                            </span>
                        )}
                    </div>
                }
                actions={
                    <Link
                        to={`/pipelines/${pipeline.name}`}
                        className="text-xs text-blue-500 hover:underline px-2 py-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                        onClick={(e) => e.stopPropagation()}
                    >
                        View
                    </Link>
                }
            >
                {runs.length === 0 && (
                    <div className="pl-12 py-2 text-xs text-slate-400 italic">No runs yet</div>
                )}
                {runs.map(run => renderRun(run, baseLevel + 1))}
            </TreeNode>
        );
    };

    const renderRun = (run, baseLevel) => {
        const artifacts = getArtifactsForRun(run.run_id);
        const modelCount = artifacts.filter(a => a.type?.toLowerCase() === 'model').length;

        return (
            <TreeNode
                key={run.run_id}
                label={run.name || `Run ${run.run_id.slice(0, 8)}`}
                icon={PlayCircle}
                level={baseLevel}
                status={run.status}
                defaultExpanded={artifacts.length > 0 && artifacts.length <= 5}
                badge={
                    artifacts.length > 0 && (
                        <div className="flex gap-1">
                            {modelCount > 0 && (
                                <span className="flex items-center gap-0.5 text-[10px] bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 px-1.5 py-0.5 rounded-full">
                                    <Box className="w-3 h-3" /> {modelCount}
                                </span>
                            )}
                            <span className="flex items-center gap-0.5 text-[10px] bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 px-1.5 py-0.5 rounded-full">
                                <FileBox className="w-3 h-3" /> {artifacts.length}
                            </span>
                        </div>
                    )
                }
                actions={
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400">{formatDate(run.created)}</span>
                        <Link
                            to={`/runs/${run.run_id}`}
                            className="text-xs text-blue-500 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                        >
                            Details
                        </Link>
                    </div>
                }
            >
                {artifacts.length === 0 && (
                    <div className="pl-16 py-1 text-xs text-slate-400 italic">No artifacts</div>
                )}
                {artifacts.map(artifact => renderArtifact(artifact, baseLevel + 1))}
            </TreeNode>
        );
    };

    const renderArtifact = (artifact, baseLevel) => {
        const typeConfig = {
            model: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
            dataset: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
            metrics: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
            default: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
        };

        const bgClass = typeConfig[artifact.type?.toLowerCase()] || typeConfig.default;

        return (
            <TreeNode
                key={artifact.artifact_id}
                label={artifact.name}
                icon={() => <ArtifactIcon type={artifact.type} />}
                level={baseLevel}
                onClick={() => onAssetSelect?.(artifact)}
                badge={
                    <span className={`text-xs px-1.5 py-0.5 rounded ${bgClass}`}>
                        {artifact.type}
                    </span>
                }
                actions={
                    <div className="flex items-center gap-2">
                        {artifact.properties && Object.keys(artifact.properties).length > 0 && (
                            <span className="text-xs text-slate-400">
                                {Object.keys(artifact.properties).length} props
                            </span>
                        )}
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onAssetSelect?.(artifact);
                            }}
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            <Eye className="w-3 h-3 text-slate-400" />
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                downloadArtifactById(artifact.artifact_id);
                            }}
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-40"
                            disabled={!artifact.artifact_id}
                        >
                            <Download className="w-3 h-3 text-slate-400" />
                        </button>
                    </div>
                }
            />
        );
    };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-slate-800 dark:to-slate-800">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-blue-500" />
                        Asset Hierarchy
                    </h3>
                    <span className="text-xs text-slate-500">
                        {data.artifacts.length} asset{data.artifacts.length !== 1 ? 's' : ''}
                    </span>
                </div>

                {/* Asset Type Filters */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setAssetTypeFilter('all')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${assetTypeFilter === 'all'
                                ? 'bg-primary-500 text-white shadow-md'
                                : 'bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600'
                            }`}
                    >
                        <FileBox className="w-3.5 h-3.5" />
                        All Assets
                        <span className="text-xs opacity-75">({data.artifacts.length})</span>
                    </button>
                    <button
                        onClick={() => setAssetTypeFilter('model')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${assetTypeFilter === 'model'
                                ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-md'
                                : 'bg-white dark:bg-slate-700 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                            }`}
                    >
                        <Box className="w-3.5 h-3.5" />
                        Models
                        <span className="text-xs opacity-75">
                            ({data.artifacts.filter(a => a.type?.toLowerCase() === 'model').length})
                        </span>
                    </button>
                    <button
                        onClick={() => setAssetTypeFilter('dataset')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${assetTypeFilter === 'dataset'
                                ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md'
                                : 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                            }`}
                    >
                        <Database className="w-3.5 h-3.5" />
                        Datasets
                        <span className="text-xs opacity-75">
                            ({data.artifacts.filter(a => a.type?.toLowerCase() === 'dataset').length})
                        </span>
                    </button>
                </div>
            </div>

            <div className="p-3 max-h-[700px] overflow-y-auto">
                {data.pipelines.length === 0 && data.projects.length === 0 ? (
                    <div className="p-8 text-center">
                        <Database className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                        <p className="text-slate-600 dark:text-slate-400 font-medium mb-1">No assets found</p>
                        <p className="text-slate-500 text-sm">Run a pipeline to generate artifacts</p>
                    </div>
                ) : (
                    renderContent()
                )}
            </div>
        </div>
    );
}
