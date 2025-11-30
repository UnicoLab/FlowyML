import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
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
    TrendingUp,
    HardDrive,
    Info
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '../../../../utils/date';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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
    switch (type?.toLowerCase()) {
        case 'model':
            return <Box className="w-4 h-4 text-purple-500" />;
        case 'dataset':
        case 'data':
            return <Database className="w-4 h-4 text-emerald-500" />;
        default:
            return <FileBox className="w-4 h-4 text-slate-400" />;
    }
};

const TreeNode = ({ label, icon: Icon, children, defaultExpanded = false, actions, status, level = 0 }) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);
    const hasChildren = children && children.length > 0;

    return (
        <div className="select-none">
            <div
                className={`
                    flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors
                    hover:bg-slate-100 dark:hover:bg-slate-800
                    ${level === 0 ? 'bg-slate-50 dark:bg-slate-800/50 mb-1' : ''}
                `}
                style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
                onClick={() => hasChildren && setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-1 text-slate-400">
                    {hasChildren ? (
                        isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                    ) : (
                        <div className="w-4" />
                    )}
                </div>

                {Icon && <Icon className={`w-4 h-4 ${level === 0 ? 'text-blue-500' : 'text-slate-500'}`} />}

                <div className="flex-1 flex items-center justify-between">
                    <span className={`text-sm ${level === 0 ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-300'}`}>
                        {label}
                    </span>
                    <div className="flex items-center gap-3">
                        {status && <StatusIcon status={status} />}
                        {actions}
                    </div>
                </div>
            </div>

            {isExpanded && hasChildren && (
                <div className="animate-in slide-in-from-top-2 duration-200">
                    {children}
                </div>
            )}
        </div>
    );
};

export function ProjectHierarchy({ projectId }) {
    const [data, setData] = useState({ pipelines: [], runs: [], artifacts: [] });
    const [loading, setLoading] = useState(true);
    const [selectedArtifact, setSelectedArtifact] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch with higher limits to ensure we get the full tree
                const [pipelinesRes, runsRes, artifactsRes] = await Promise.all([
                    fetchApi(`/api/pipelines?project=${projectId}`),
                    fetchApi(`/api/runs?project=${projectId}&limit=100`),
                    fetchApi(`/api/assets?project=${projectId}&limit=100`)
                ]);

                const pipelinesData = await pipelinesRes.json();
                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();

                setData({
                    pipelines: Array.isArray(pipelinesData?.pipelines) ? pipelinesData.pipelines : [],
                    runs: Array.isArray(runsData?.runs) ? runsData.runs : [],
                    artifacts: Array.isArray(artifactsData?.assets) ? artifactsData.assets : (Array.isArray(artifactsData?.artifacts) ? artifactsData.artifacts : [])
                });
            } catch (error) {
                console.error('Failed to fetch hierarchy data:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchData();
        }
    }, [projectId]);

    if (loading) {
        return <div className="h-64 w-full bg-slate-50 dark:bg-slate-800/50 rounded-xl animate-pulse" />;
    }

    // Group runs by pipeline
    const getRunsForPipeline = (pipelineName) => {
        return data.runs.filter(r => r.pipeline_name === pipelineName);
    };

    // Group artifacts by run
    const getArtifactsForRun = (runId) => {
        return data.artifacts.filter(a => a.run_id === runId);
    };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-blue-500" />
                    Project Structure
                </h3>
            </div>

            <div className="p-2 max-h-[600px] overflow-y-auto">
                <TreeNode
                    label="Project Root"
                    icon={Box}
                    defaultExpanded={true}
                    level={0}
                    actions={<span className="text-xs text-slate-400">{data.pipelines.length} pipelines</span>}
                >
                    {data.pipelines.length === 0 && (
                        <div className="p-4 text-center text-sm text-slate-500 italic">
                            No pipelines found. Run a pipeline to see it here.
                        </div>
                    )}

                    {data.pipelines.map(pipeline => {
                        const pipelineRuns = getRunsForPipeline(pipeline.name);

                        return (
                            <TreeNode
                                key={pipeline.name}
                                label={pipeline.name}
                                icon={Activity}
                                level={1}
                                actions={
                                    <Link
                                        to={`/pipelines/${pipeline.name}`}
                                        className="text-xs text-blue-500 hover:underline px-2 py-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        View Details
                                    </Link>
                                }
                            >
                                {pipelineRuns.length === 0 && (
                                    <div className="pl-12 py-2 text-xs text-slate-400 italic">No runs yet</div>
                                )}

                                {pipelineRuns.map(run => {
                                    const runArtifacts = getArtifactsForRun(run.run_id);
                                    const modelCount = runArtifacts.filter(a => a.type === 'model').length;

                                    return (
                                        <TreeNode
                                            key={run.run_id}
                                            label={run.name || `Run ${run.run_id.slice(0, 8)}`}
                                            icon={PlayCircle}
                                            level={2}
                                            status={run.status}
                                            actions={
                                                <div className="flex items-center gap-2">
                                                    {runArtifacts.length > 0 && (
                                                        <div className="flex gap-1">
                                                            {modelCount > 0 && (
                                                                <span className="flex items-center gap-0.5 text-[10px] bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 px-1.5 py-0.5 rounded-full">
                                                                    <Box className="w-3 h-3" /> {modelCount}
                                                                </span>
                                                            )}
                                                            <span className="flex items-center gap-0.5 text-[10px] bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 px-1.5 py-0.5 rounded-full">
                                                                <FileBox className="w-3 h-3" /> {runArtifacts.length}
                                                            </span>
                                                        </div>
                                                    )}
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
                                            {runArtifacts.length === 0 && (
                                                <div className="pl-16 py-1 text-xs text-slate-400 italic">No artifacts</div>
                                            )}

                                            {runArtifacts.map(artifact => (
                                                <div
                                                    key={artifact.artifact_id}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setSelectedArtifact(artifact);
                                                    }}
                                                    className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded transition-colors"
                                                >
                                                    <TreeNode
                                                        label={artifact.name}
                                                        icon={() => <ArtifactIcon type={artifact.type} />}
                                                        level={3}
                                                        actions={
                                                            <div className="flex items-center gap-2">
                                                                <span className={`text-xs px-1.5 py-0.5 rounded ${artifact.type === 'model'
                                                                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                                                                        : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                                                    }`}>
                                                                    {artifact.type}
                                                                </span>
                                                                <Info className="w-3 h-3 text-slate-400" />
                                                            </div>
                                                        }
                                                    />
                                                </div>
                                            ))}
                                        </TreeNode>
                                    );
                                })}
                            </TreeNode>
                        );
                    })}
                </TreeNode>
            </div>

            {/* Artifact Details Modal */}
            <ArtifactDetailsModal
                artifact={selectedArtifact}
                onClose={() => setSelectedArtifact(null)}
            />
        </div>
    );
}

function ArtifactDetailsModal({ artifact, onClose }) {
    if (!artifact) return null;

    const hasTrainingHistory = artifact.training_history &&
        artifact.training_history.epochs &&
        artifact.training_history.epochs.length > 0;

    // Prepare data for charts
    const chartData = hasTrainingHistory ? artifact.training_history.epochs.map((epoch, idx) => ({
        epoch,
        'Train Loss': artifact.training_history.train_loss[idx],
        'Val Loss': artifact.training_history.val_loss[idx],
        'Train Accuracy': artifact.training_history.train_accuracy[idx],
        'Val Accuracy': artifact.training_history.val_accuracy[idx]
    })) : [];

    return (
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <div
                className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-slate-800 dark:to-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-white dark:bg-slate-700 rounded-xl shadow-sm">
                            <ArtifactIcon type={artifact.type} />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white">{artifact.name}</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400 capitalize">{artifact.type}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/50 dark:hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <X size={20} className="text-slate-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(85vh-140px)]">
                    <div className="space-y-6">
                        {/* Properties Grid */}
                        {artifact.properties && Object.keys(artifact.properties).length > 0 && (
                            <div>
                                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                                    <Info className="w-4 h-4" />
                                    Properties
                                </h4>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {Object.entries(artifact.properties).map(([key, value]) => (
                                        <div key={key} className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
                                            <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1 capitalize">
                                                {key.replace(/_/g, ' ')}
                                            </span>
                                            <span className="text-sm font-mono font-semibold text-slate-900 dark:text-white">
                                                {typeof value === 'number' ? value.toLocaleString() : String(value)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Training History Charts */}
                        {hasTrainingHistory && (
                            <div>
                                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4" />
                                    Training History
                                </h4>

                                {/* Loss Chart */}
                                <div className="mb-6 bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                                    <h5 className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-3">Loss over Epochs</h5>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <LineChart data={chartData}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                            <XAxis
                                                dataKey="epoch"
                                                label={{ value: 'Epoch', position: 'insideBottom', offset: -5 }}
                                                stroke="#94a3b8"
                                            />
                                            <YAxis stroke="#94a3b8" />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: '#fff',
                                                    border: '1px solid #e2e8f0',
                                                    borderRadius: '8px'
                                                }}
                                            />
                                            <Legend />
                                            <Line type="monotone" dataKey="Train Loss" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                            <Line type="monotone" dataKey="Val Loss" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Accuracy Chart */}
                                <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                                    <h5 className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-3">Accuracy over Epochs</h5>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <LineChart data={chartData}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                            <XAxis
                                                dataKey="epoch"
                                                label={{ value: 'Epoch', position: 'insideBottom', offset: -5 }}
                                                stroke="#94a3b8"
                                            />
                                            <YAxis stroke="#94a3b8" domain={[0, 1]} />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: '#fff',
                                                    border: '1px solid #e2e8f0',
                                                    borderRadius: '8px'
                                                }}
                                            />
                                            <Legend />
                                            <Line type="monotone" dataKey="Train Accuracy" stroke="#10b981" strokeWidth={2} dot={false} />
                                            <Line type="monotone" dataKey="Val Accuracy" stroke="#f59e0b" strokeWidth={2} dot={false} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}

                        {/* Metadata */}
                        <div>
                            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                                <HardDrive className="w-4 h-4" />
                                Metadata
                            </h4>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                                    <span className="text-slate-500 dark:text-slate-400">Artifact ID:</span>
                                    <span className="font-mono text-xs text-slate-700 dark:text-slate-300">{artifact.artifact_id}</span>
                                </div>
                                {artifact.step && (
                                    <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                                        <span className="text-slate-500 dark:text-slate-400">Pipeline Step:</span>
                                        <span className="font-medium text-slate-700 dark:text-slate-300">{artifact.step}</span>
                                    </div>
                                )}
                                {artifact.path && (
                                    <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                                        <span className="text-slate-500 dark:text-slate-400">Path:</span>
                                        <span className="font-mono text-xs text-slate-700 dark:text-slate-300">{artifact.path}</span>
                                    </div>
                                )}
                                {artifact.size_bytes && (
                                    <div className="flex justify-between py-2 border-b border-slate-100 dark:border-slate-800">
                                        <span className="text-slate-500 dark:text-slate-400">Size:</span>
                                        <span className="text-slate-700 dark:text-slate-300">
                                            {(artifact.size_bytes / 1024 / 1024).toFixed(2)} MB
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
