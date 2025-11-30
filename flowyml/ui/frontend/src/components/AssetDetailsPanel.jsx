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
    Info
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

export function AssetDetailsPanel({ asset, onClose }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [currentProject, setCurrentProject] = useState(asset?.project);

    if (!asset) return null;

    const handleProjectUpdate = async (newProject) => {
        try {
            await fetchApi(`/api/assets/${asset.artifact_id}/project`, {
                method: 'PUT',
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
                {/* Header */}
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

                {/* Tabs */}
                <div className="flex items-center gap-1 p-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <TabButton
                        active={activeTab === 'overview'}
                        onClick={() => setActiveTab('overview')}
                        icon={Info}
                        label="Overview"
                    />
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
                    {activeTab === 'overview' && (
                        <>
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
