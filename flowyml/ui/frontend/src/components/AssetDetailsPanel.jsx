import React, { useState } from 'react';
import {
    X,
    Download,
    Box,
    Database,
    BarChart2,
    FileText,
    Calendar,
    Tag,
    FileBox,
    Activity,
    GitBranch,
    Layers,
    HardDrive,
    ExternalLink,
    Info,
    Cpu,
    Zap,
    Settings,
    Table,
    PieChart,
    TrendingUp,
    Hash,
    Gauge,
    LineChart,
    Eye
} from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { downloadArtifactById } from '../utils/downloads';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ProjectSelector } from './ProjectSelector';
import { fetchApi } from '../utils/api';
import { DatasetViewer } from './DatasetViewer';
import { TrainingHistoryChart } from './TrainingHistoryChart';

export function AssetDetailsPanel({ asset, onClose, hideHeader = false }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [currentProject, setCurrentProject] = useState(asset?.project);

    if (!asset) return null;

    const handleProjectUpdate = async (newProject) => {
        try {
            await fetchApi(`/api/assets/${asset.artifact_id}/project`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ project_name: newProject })
            });
            setCurrentProject(newProject);
        } catch (error) {
            console.error('Failed to update project:', error);
        }
    };

    const typeConfig = {
        model: {
            icon: Box,
            color: 'from-purple-500 to-pink-500',
            bgColor: 'bg-purple-50 dark:bg-purple-900/20',
            textColor: 'text-purple-600 dark:text-purple-400',
            borderColor: 'border-purple-200 dark:border-purple-800'
        },
        dataset: {
            icon: Database,
            color: 'from-blue-500 to-cyan-500',
            bgColor: 'bg-blue-50 dark:bg-blue-900/20',
            textColor: 'text-blue-600 dark:text-blue-400',
            borderColor: 'border-blue-200 dark:border-blue-800'
        },
        metrics: {
            icon: BarChart2,
            color: 'from-emerald-500 to-teal-500',
            bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
            textColor: 'text-emerald-600 dark:text-emerald-400',
            borderColor: 'border-emerald-200 dark:border-emerald-800'
        },
        default: {
            icon: FileText,
            color: 'from-slate-500 to-slate-600',
            bgColor: 'bg-slate-50 dark:bg-slate-900/20',
            textColor: 'text-slate-600 dark:text-slate-400',
            borderColor: 'border-slate-200 dark:border-slate-800'
        }
    };

    const config = typeConfig[asset.type?.toLowerCase()] || typeConfig.default;
    const Icon = config.icon;

    const formatBytes = (bytes) => {
        if (!bytes || bytes === 0) return 'N/A';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="h-full flex flex-col"
        >
            <Card className="flex-1 flex flex-col overflow-hidden">
                {/* Header - can be hidden when embedded */}
                {!hideHeader && (
                    <div className={`p-6 ${config.bgColor} border-b ${config.borderColor}`}>
                        <div className="flex items-start justify-between mb-4">
                            <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
                                <Icon size={32} />
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-white/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
                            >
                                <X size={20} className="text-slate-400" />
                            </button>
                        </div>

                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                            {asset.name}
                        </h2>

                        <div className="flex items-center gap-2 flex-wrap">
                            <Badge className={`bg-gradient-to-r ${config.color} text-white border-0`}>
                                {asset.type}
                            </Badge>
                            <ProjectSelector
                                currentProject={currentProject}
                                onUpdate={handleProjectUpdate}
                            />
                        </div>
                    </div>
                )}

                {/* Tabs */}
                <div className="flex items-center gap-1 p-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
                    <TabButton
                        active={activeTab === 'overview'}
                        onClick={() => setActiveTab('overview')}
                        icon={Info}
                        label="Overview"
                    />
                    {/* Show Visualization tab for Datasets and Models */}
                    {(asset.type?.toLowerCase() === 'dataset' || asset.type?.toLowerCase() === 'model') && (
                        <TabButton
                            active={activeTab === 'visualization'}
                            onClick={() => setActiveTab('visualization')}
                            icon={asset.type?.toLowerCase() === 'model' ? LineChart : BarChart2}
                            label={asset.type?.toLowerCase() === 'model' ? 'Training' : 'Statistics'}
                        />
                    )}
                    <TabButton
                        active={activeTab === 'properties'}
                        onClick={() => setActiveTab('properties')}
                        icon={Tag}
                        label="Properties"
                    />
                    <TabButton
                        active={activeTab === 'metadata'}
                        onClick={() => setActiveTab('metadata')}
                        icon={FileBox}
                        label="Metadata"
                    />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Visualization Tab - Rich interactive visualizations */}
                    {activeTab === 'visualization' && (
                        <div className="space-y-6">
                            {/* Dataset Visualization with full DatasetViewer */}
                            {asset.type?.toLowerCase() === 'dataset' && (
                                <DatasetViewer artifact={asset} />
                            )}

                            {/* Model Visualization with Training History */}
                            {asset.type?.toLowerCase() === 'model' && (
                                <ModelVisualization asset={asset} />
                            )}
                        </div>
                    )}

                    {activeTab === 'overview' && (
                        <>
                            {/* Model-specific Auto-extracted Info */}
                            {asset.type?.toLowerCase() === 'model' && asset.properties && (
                                <ModelOverview properties={asset.properties} />
                            )}

                            {/* Dataset-specific Auto-extracted Info */}
                            {asset.type?.toLowerCase() === 'dataset' && asset.properties && (
                                <DatasetOverview properties={asset.properties} />
                            )}

                            {/* Metrics-specific Info */}
                            {asset.type?.toLowerCase() === 'metrics' && asset.properties && (
                                <MetricsOverview properties={asset.properties} />
                            )}

                            {/* Key Information */}
                            <div>
                                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <FileBox size={16} />
                                    Asset Information
                                </h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <InfoCard
                                        icon={Calendar}
                                        label="Created"
                                        value={asset.created_at ? format(new Date(asset.created_at), 'MMM d, yyyy HH:mm') : 'N/A'}
                                    />
                                    <InfoCard
                                        icon={HardDrive}
                                        label="Size"
                                        value={formatBytes(asset.size || asset.storage_bytes)}
                                    />
                                    <InfoCard
                                        icon={Layers}
                                        label="Step"
                                        value={asset.step || 'N/A'}
                                    />
                                    <InfoCard
                                        icon={GitBranch}
                                        label="Version"
                                        value={asset.version || 'N/A'}
                                    />
                                </div>
                            </div>

                            {/* Context Links */}
                            {(asset.run_id || asset.pipeline_name || currentProject) && (
                                <div>
                                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <GitBranch size={16} />
                                        Context
                                    </h3>
                                    <div className="space-y-2">
                                        {currentProject && (
                                            <ContextLink
                                                icon={Box}
                                                label="Project"
                                                value={currentProject}
                                                to={`/assets?project=${encodeURIComponent(currentProject)}`}
                                            />
                                        )}
                                        {asset.pipeline_name && (
                                            <ContextLink
                                                icon={Activity}
                                                label="Pipeline"
                                                value={asset.pipeline_name}
                                                to={`/pipelines?project=${encodeURIComponent(currentProject || '')}`}
                                            />
                                        )}
                                        {asset.run_id && (
                                            <ContextLink
                                                icon={Activity}
                                                label="Run"
                                                value={asset.run_id.slice(0, 12) + '...'}
                                                to={`/runs/${asset.run_id}`}
                                            />
                                        )}
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    {activeTab === 'properties' && (
                        <div>
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Tag size={16} />
                                Properties ({asset.properties ? Object.keys(asset.properties).length : 0})
                            </h3>
                            {asset.properties && Object.keys(asset.properties).length > 0 ? (
                                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 space-y-2">
                                    {Object.entries(asset.properties).map(([key, value]) => (
                                        <PropertyRow key={key} name={key} value={value} />
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-slate-500 italic">
                                    No properties available
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'metadata' && (
                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                    Artifact ID
                                </h3>
                                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                                    <code className="text-xs text-slate-600 dark:text-slate-400 font-mono break-all">
                                        {asset.artifact_id}
                                    </code>
                                </div>
                            </div>

                            {asset.uri && (
                                <div>
                                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                                        Location
                                    </h3>
                                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                                        <code className="text-xs text-slate-600 dark:text-slate-400 break-all">
                                            {asset.uri}
                                        </code>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex gap-2">
                        <Button
                            onClick={() => downloadArtifactById(asset.artifact_id)}
                            disabled={!asset.artifact_id}
                            className="flex-1"
                        >
                            <Download size={16} className="mr-2" />
                            Download Asset
                        </Button>
                        {asset.run_id && (
                            <Link to={`/runs/${asset.run_id}`}>
                                <Button variant="outline">
                                    <ExternalLink size={16} className="mr-2" />
                                    View in Run
                                </Button>
                            </Link>
                        )}
                    </div>
                </div>
            </Card>
        </motion.div>
    );
}

function InfoCard({ icon: Icon, label, value, mono = false }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className="text-slate-400" />
                <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
            </div>
            <p className={`text-sm font-semibold text-slate-900 dark:text-white ${mono ? 'font-mono' : ''}`}>
                {value}
            </p>
        </div>
    );
}

function ContextLink({ icon: Icon, label, value, to }) {
    return (
        <Link
            to={to}
            className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all group"
        >
            <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg group-hover:bg-primary-100 dark:group-hover:bg-primary-900/30 transition-colors">
                <Icon size={16} className="text-slate-600 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
                <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{value}</p>
            </div>
            <ExternalLink size={14} className="text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </Link>
    );
}

function PropertyRow({ name, value }) {
    const displayValue = () => {
        if (typeof value === 'object') {
            return JSON.stringify(value, null, 2);
        }
        if (typeof value === 'boolean') {
            return value ? 'true' : 'false';
        }
        if (typeof value === 'number') {
            return value.toLocaleString();
        }
        return String(value);
    };

    return (
        <div className="flex items-start justify-between gap-4 py-2 border-b border-slate-200 dark:border-slate-700 last:border-0">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300 shrink-0">
                {name}
            </span>
            <span className="text-sm text-slate-600 dark:text-slate-400 text-right font-mono break-all">
                {displayValue()}
            </span>
        </div>
    );
}

function TabButton({ active, onClick, icon: Icon, label }) {
    return (
        <button
            onClick={onClick}
            className={`
                flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                ${active
                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                    : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-700 dark:hover:text-slate-300'
                }
            `}
        >
            <Icon size={16} />
            {label}
        </button>
    );
}

// Model-specific overview with auto-extracted metadata
function ModelOverview({ properties }) {
    const framework = properties.framework;
    const parameters = properties.parameters;
    const trainableParams = properties.trainable_parameters;
    const optimizer = properties.optimizer;
    const learningRate = properties.learning_rate;
    const lossFunction = properties.loss_function;
    const numLayers = properties.num_layers;
    const layerTypes = properties.layer_types;
    const architecture = properties.architecture || properties.model_class;
    const isAutoExtracted = properties._auto_extracted;

    if (!framework && !parameters) return null;

    const formatNumber = (num) => {
        if (!num) return 'N/A';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toLocaleString();
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Cpu size={16} className="text-purple-500" />
                    Model Details
                </h3>
                {isAutoExtracted && (
                    <span className="text-[10px] bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-2 py-0.5 rounded-full">
                        Auto-extracted
                    </span>
                )}
            </div>

            {/* Framework & Architecture */}
            <div className="grid grid-cols-2 gap-3">
                {framework && (
                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg p-3 border border-purple-100 dark:border-purple-800">
                        <div className="flex items-center gap-2 mb-1">
                            <Zap size={12} className="text-purple-500" />
                            <span className="text-[10px] text-purple-600 dark:text-purple-400 font-medium uppercase">Framework</span>
                        </div>
                        <p className="text-lg font-bold text-purple-700 dark:text-purple-300 capitalize">{framework}</p>
                    </div>
                )}
                {architecture && (
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 mb-1">
                            <Settings size={12} className="text-slate-500" />
                            <span className="text-[10px] text-slate-500 font-medium uppercase">Architecture</span>
                        </div>
                        <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{architecture}</p>
                    </div>
                )}
            </div>

            {/* Parameters */}
            {parameters && (
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 mb-1">
                            <Hash size={12} className="text-slate-500" />
                            <span className="text-[10px] text-slate-500 font-medium uppercase">Parameters</span>
                        </div>
                        <p className="text-xl font-bold text-slate-900 dark:text-white">{formatNumber(parameters)}</p>
                    </div>
                    {trainableParams && (
                        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                            <div className="flex items-center gap-2 mb-1">
                                <TrendingUp size={12} className="text-slate-500" />
                                <span className="text-[10px] text-slate-500 font-medium uppercase">Trainable</span>
                            </div>
                            <p className="text-xl font-bold text-slate-900 dark:text-white">{formatNumber(trainableParams)}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Training Config */}
            {(optimizer || lossFunction || learningRate) && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-100 dark:border-blue-800">
                    <h4 className="text-[10px] text-blue-600 dark:text-blue-400 font-medium uppercase mb-2">Training Configuration</h4>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                        {optimizer && (
                            <div>
                                <span className="text-blue-500">Optimizer:</span>
                                <span className="ml-1 font-medium text-blue-700 dark:text-blue-300">{optimizer}</span>
                            </div>
                        )}
                        {learningRate && (
                            <div>
                                <span className="text-blue-500">LR:</span>
                                <span className="ml-1 font-medium text-blue-700 dark:text-blue-300">
                                    {typeof learningRate === 'number' ? learningRate.toExponential(2) : learningRate}
                                </span>
                            </div>
                        )}
                        {lossFunction && (
                            <div>
                                <span className="text-blue-500">Loss:</span>
                                <span className="ml-1 font-medium text-blue-700 dark:text-blue-300">{lossFunction}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Layers */}
            {(numLayers || layerTypes) && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[10px] text-slate-500 font-medium uppercase">Layers</h4>
                        {numLayers && <span className="text-sm font-bold text-slate-900 dark:text-white">{numLayers}</span>}
                    </div>
                    {layerTypes && (
                        <div className="flex flex-wrap gap-1">
                            {(Array.isArray(layerTypes) ? layerTypes : JSON.parse(layerTypes || '[]')).map((type, i) => (
                                <span key={i} className="text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded">
                                    {type}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// Dataset-specific overview with auto-extracted metadata
function DatasetOverview({ properties }) {
    const samples = properties.samples || properties.num_samples;
    const features = properties.num_features;
    const columns = properties.columns || properties.feature_columns;
    const framework = properties.framework;
    const labelColumn = properties.label_column;
    const columnStats = properties.column_stats;
    const isAutoExtracted = properties._auto_extracted;

    if (!samples && !features && !columns) return null;

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Database size={16} className="text-blue-500" />
                    Dataset Details
                </h3>
                {isAutoExtracted && (
                    <span className="text-[10px] bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded-full">
                        Auto-extracted
                    </span>
                )}
            </div>

            {/* Key Stats */}
            <div className="grid grid-cols-3 gap-3">
                {samples && (
                    <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-lg p-3 border border-blue-100 dark:border-blue-800">
                        <div className="flex items-center gap-2 mb-1">
                            <Table size={12} className="text-blue-500" />
                            <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium uppercase">Samples</span>
                        </div>
                        <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{samples.toLocaleString()}</p>
                    </div>
                )}
                {features && (
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 mb-1">
                            <PieChart size={12} className="text-slate-500" />
                            <span className="text-[10px] text-slate-500 font-medium uppercase">Features</span>
                        </div>
                        <p className="text-xl font-bold text-slate-900 dark:text-white">{features}</p>
                    </div>
                )}
                {framework && (
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 mb-1">
                            <Zap size={12} className="text-slate-500" />
                            <span className="text-[10px] text-slate-500 font-medium uppercase">Format</span>
                        </div>
                        <p className="text-sm font-bold text-slate-900 dark:text-white capitalize">{framework}</p>
                    </div>
                )}
            </div>

            {/* Columns */}
            {columns && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[10px] text-slate-500 font-medium uppercase">Columns</h4>
                        <span className="text-xs text-slate-400">{Array.isArray(columns) ? columns.length : 0} total</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                        {(Array.isArray(columns) ? columns : []).slice(0, 10).map((col, i) => (
                            <span
                                key={i}
                                className={`text-[10px] px-2 py-0.5 rounded ${
                                    col === labelColumn
                                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 font-medium'
                                        : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                                }`}
                            >
                                {col}{col === labelColumn && ' (target)'}
                            </span>
                        ))}
                        {Array.isArray(columns) && columns.length > 10 && (
                            <span className="text-[10px] text-slate-400">+{columns.length - 10} more</span>
                        )}
                    </div>
                </div>
            )}

            {/* Column Stats Preview */}
            {columnStats && Object.keys(columnStats).length > 0 && (
                <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 border border-emerald-100 dark:border-emerald-800">
                    <h4 className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium uppercase mb-2">Column Statistics Available</h4>
                    <p className="text-xs text-emerald-700 dark:text-emerald-300">
                        {Object.keys(columnStats).length} columns with statistics (mean, std, min, max, etc.)
                    </p>
                </div>
            )}
        </div>
    );
}

// Metrics-specific overview
function MetricsOverview({ properties }) {
    // Filter out internal properties
    const metricEntries = Object.entries(properties).filter(([key]) =>
        !key.startsWith('_') && !['data', 'samples', 'source'].includes(key)
    );

    if (metricEntries.length === 0) return null;

    const formatValue = (value) => {
        if (typeof value === 'number') {
            if (value < 0.01 && value !== 0) return value.toExponential(3);
            if (value > 1000) return value.toLocaleString();
            return value.toFixed(4);
        }
        return String(value);
    };

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Gauge size={16} className="text-emerald-500" />
                Evaluation Metrics
            </h3>

            <div className="grid grid-cols-2 gap-3">
                {metricEntries.slice(0, 8).map(([key, value]) => (
                    <div
                        key={key}
                        className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-lg p-3 border border-emerald-100 dark:border-emerald-800"
                    >
                        <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium uppercase block mb-1">
                            {key.replace(/_/g, ' ')}
                        </span>
                        <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300 font-mono">
                            {formatValue(value)}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
}

// Model Visualization with Training History
function ModelVisualization({ asset }) {
    // Check for training history in different locations
    const trainingHistory = asset.training_history ||
        asset.properties?.training_history ||
        null;

    const hasTrainingHistory = trainingHistory &&
        trainingHistory.epochs &&
        trainingHistory.epochs.length > 0;

    if (!hasTrainingHistory) {
        return (
            <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                <div className="inline-flex p-4 bg-white dark:bg-slate-800 rounded-full mb-4 shadow-sm">
                    <LineChart size={32} className="text-slate-400" />
                </div>
                <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-2">No Training History Available</h4>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                    This model artifact doesn't have training history data.
                    <br />
                    Use <code className="bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded text-xs">FlowymlKerasCallback</code> during training to capture metrics.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl shadow-lg">
                    <LineChart size={24} className="text-white" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">Training History</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        {trainingHistory.epochs.length} epochs recorded
                    </p>
                </div>
            </div>

            {/* Training History Chart */}
            <TrainingHistoryChart trainingHistory={trainingHistory} compact={false} />
        </div>
    );
}
