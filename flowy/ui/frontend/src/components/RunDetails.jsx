import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, Calendar, Package, ArrowRight, BarChart2, FileText, Database, Box, ChevronRight, Activity, Layers, Code2, Terminal, Info, X, Maximize2, TrendingUp, Download } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { PipelineGraph } from './PipelineGraph';

export function RunDetails() {
    const { runId } = useParams();
    const [run, setRun] = useState(null);
    const [artifacts, setArtifacts] = useState([]);
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedStep, setSelectedStep] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [selectedArtifact, setSelectedArtifact] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [runRes, assetsRes] = await Promise.all([
                    fetch(`/api/runs/${runId}`),
                    fetch(`/api/assets?run_id=${runId}`)
                ]);

                const runData = await runRes.json();
                const assetsData = await assetsRes.json();

                let metricsData = [];
                try {
                    const mRes = await fetch(`/api/runs/${runId}/metrics`);
                    if (mRes.ok) {
                        const mJson = await mRes.json();
                        metricsData = mJson.metrics || [];
                    }
                } catch (e) {
                    console.warn("Failed to fetch metrics", e);
                }

                setRun(runData);
                setArtifacts(assetsData.assets || []);
                setMetrics(metricsData);

                // Auto-select first step
                if (runData.steps && Object.keys(runData.steps).length > 0) {
                    setSelectedStep(Object.keys(runData.steps)[0]);
                }

                setLoading(false);
            } catch (err) {
                console.error(err);
                setLoading(false);
            }
        };

        fetchData();
    }, [runId]);

    if (loading) return (
        <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
    );

    if (!run) return <div className="p-8 text-center text-slate-500">Run not found</div>;

    const statusVariant =
        run.status === 'completed' ? 'success' :
            run.status === 'failed' ? 'danger' : 'warning';

    const selectedStepData = selectedStep ? run.steps?.[selectedStep] : null;
    const selectedStepArtifacts = artifacts.filter(a => a.step === selectedStep);
    const selectedStepMetrics = metrics.filter(m => m.step === selectedStep || m.name.startsWith(selectedStep));

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Link to="/runs" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">Runs</Link>
                        <ChevronRight size={14} className="text-slate-300" />
                        <span className="text-sm text-slate-900 font-medium">{run.run_id}</span>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${run.status === 'completed' ? 'bg-emerald-500' : run.status === 'failed' ? 'bg-rose-500' : 'bg-amber-500'}`} />
                        Run: <span className="font-mono text-slate-500">{run.run_id.substring(0, 8)}</span>
                    </h2>
                    <p className="text-slate-500 mt-1 flex items-center gap-2">
                        <Layers size={16} />
                        Pipeline: <span className="font-medium text-slate-700">{run.pipeline_name}</span>
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <Badge variant={statusVariant} className="text-sm px-4 py-1.5 uppercase tracking-wide shadow-sm">
                        {run.status}
                    </Badge>
                    <span className="text-xs text-slate-400 font-mono">ID: {run.run_id}</span>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatsCard
                    icon={<Clock size={24} />}
                    label="Duration"
                    value={run.duration ? `${run.duration.toFixed(2)}s` : '-'}
                    color="blue"
                />
                <StatsCard
                    icon={<Calendar size={24} />}
                    label="Started At"
                    value={run.start_time ? format(new Date(run.start_time), 'MMM d, HH:mm:ss') : '-'}
                    color="purple"
                />
                <StatsCard
                    icon={<CheckCircle size={24} />}
                    label="Steps Completed"
                    value={`${run.steps ? Object.values(run.steps).filter(s => s.success).length : 0} / ${run.steps ? Object.keys(run.steps).length : 0}`}
                    color="emerald"
                />
            </div>

            {/* Main Content - Split View */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* DAG Visualization - 2 columns */}
                <div className="lg:col-span-2">
                    <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                        <Activity className="text-primary-500" /> Pipeline Execution Graph
                    </h3>
                    <div className="h-[600px]">
                        {run.dag ? (
                            <PipelineGraph
                                dag={run.dag}
                                steps={run.steps}
                                selectedStep={selectedStep}
                                onStepSelect={setSelectedStep}
                            />
                        ) : (
                            <Card className="h-full flex items-center justify-center">
                                <p className="text-slate-500">DAG visualization not available</p>
                            </Card>
                        )}
                    </div>
                </div>

                {/* Step Details Panel - 1 column */}
                <div>
                    <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                        <Info className="text-primary-500" /> Step Details
                    </h3>

                    {selectedStepData ? (
                        <Card className="overflow-hidden">
                            {/* Step Header */}
                            <div className="pb-4 border-b border-slate-100">
                                <h4 className="text-lg font-bold text-slate-900 mb-2">{selectedStep}</h4>
                                <div className="flex items-center gap-2">
                                    <Badge variant={selectedStepData.success ? 'success' : 'danger'} className="text-xs">
                                        {selectedStepData.success ? 'Success' : 'Failed'}
                                    </Badge>
                                    {selectedStepData.cached && (
                                        <Badge variant="secondary" className="text-xs bg-blue-50 text-blue-700">
                                            Cached
                                        </Badge>
                                    )}
                                    <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                                        {selectedStepData.duration?.toFixed(2)}s
                                    </span>
                                </div>
                            </div>

                            {/* Tabs */}
                            <div className="flex gap-2 border-b border-slate-100 mt-4">
                                <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
                                    <Info size={16} /> Overview
                                </TabButton>
                                <TabButton active={activeTab === 'code'} onClick={() => setActiveTab('code')}>
                                    <Code2 size={16} /> Code
                                </TabButton>
                                <TabButton active={activeTab === 'artifacts'} onClick={() => setActiveTab('artifacts')}>
                                    <Package size={16} /> Artifacts
                                </TabButton>
                            </div>

                            {/* Tab Content */}
                            <div className="mt-4 max-h-[450px] overflow-y-auto">
                                {activeTab === 'overview' && (
                                    <OverviewTab stepData={selectedStepData} metrics={selectedStepMetrics} />
                                )}
                                {activeTab === 'code' && (
                                    <CodeTab sourceCode={selectedStepData.source_code} />
                                )}
                                {activeTab === 'artifacts' && (
                                    <ArtifactsTab
                                        artifacts={selectedStepArtifacts}
                                        onArtifactClick={setSelectedArtifact}
                                    />
                                )}
                            </div>
                        </Card>
                    ) : (
                        <Card className="p-12 text-center">
                            <p className="text-slate-500">Select a step to view details</p>
                        </Card>
                    )}
                </div>
            </div>

            {/* Artifact Detail Modal */}
            <ArtifactModal
                artifact={selectedArtifact}
                onClose={() => setSelectedArtifact(null)}
            />
        </div>
    );
}

function StatsCard({ icon, label, value, color }) {
    const colorClasses = {
        blue: "bg-blue-50 text-blue-600",
        purple: "bg-purple-50 text-purple-600",
        emerald: "bg-emerald-50 text-emerald-600",
    };

    return (
        <Card className="hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
                    {icon}
                </div>
                <div>
                    <p className="text-sm text-slate-500 font-medium">{label}</p>
                    <p className="text-xl font-bold text-slate-900">{value}</p>
                </div>
            </div>
        </Card>
    );
}

function TabButton({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            className={`
                flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors
                ${active
                    ? 'text-primary-600 border-b-2 border-primary-600'
                    : 'text-slate-500 hover:text-slate-700'
                }
            `}
        >
            {children}
        </button>
    );
}

function OverviewTab({ stepData, metrics }) {
    return (
        <div className="space-y-4">
            {/* Metadata */}
            <div>
                <h5 className="text-sm font-semibold text-slate-700 mb-2">Metadata</h5>
                <div className="space-y-2 text-sm">
                    {stepData.inputs?.length > 0 && (
                        <div>
                            <span className="text-slate-500">Inputs:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                                {stepData.inputs.map(input => (
                                    <span key={input} className="bg-slate-100 px-2 py-0.5 rounded text-xs font-mono">
                                        {input}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                    {stepData.outputs?.length > 0 && (
                        <div>
                            <span className="text-slate-500">Outputs:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                                {stepData.outputs.map(output => (
                                    <span key={output} className="bg-slate-100 px-2 py-0.5 rounded text-xs font-mono">
                                        {output}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                    {stepData.tags && Object.keys(stepData.tags).length > 0 && (
                        <div>
                            <span className="text-slate-500">Tags:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                                {Object.entries(stepData.tags).map(([key, value]) => (
                                    <span key={key} className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs">
                                        {key}: {value}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Error */}
            {stepData.error && (
                <div>
                    <h5 className="text-sm font-semibold text-rose-700 mb-2">Error</h5>
                    <pre className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs font-mono whitespace-pre-wrap overflow-x-auto">
                        {stepData.error}
                    </pre>
                </div>
            )}

            {/* Metrics with Visualization */}
            {metrics?.length > 0 && (
                <div>
                    <h5 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                        <TrendingUp size={16} /> Metrics
                    </h5>
                    <div className="grid grid-cols-2 gap-2">
                        {metrics.map((metric, idx) => (
                            <MetricCard key={idx} metric={metric} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function MetricCard({ metric }) {
    const isNumeric = typeof metric.value === 'number';
    const displayValue = isNumeric ? metric.value.toFixed(4) : metric.value;

    return (
        <div className="p-3 bg-gradient-to-br from-slate-50 to-white rounded-lg border border-slate-200 hover:border-primary-300 transition-all group">
            <span className="text-xs text-slate-500 block truncate mb-1" title={metric.name}>
                {metric.name}
            </span>
            <div className="flex items-baseline gap-2">
                <span className="text-xl font-mono font-bold text-slate-900 group-hover:text-primary-600 transition-colors">
                    {displayValue}
                </span>
                {isNumeric && metric.value > 0 && (
                    <TrendingUp size={14} className="text-emerald-500" />
                )}
            </div>
        </div>
    );
}

function CodeTab({ sourceCode }) {
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <Code2 size={16} /> Source Code
                </h5>
                <button
                    className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
                    onClick={() => navigator.clipboard.writeText(sourceCode || '')}
                >
                    <Download size={12} /> Copy
                </button>
            </div>
            <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono overflow-x-auto leading-relaxed">
                {sourceCode || '# Source code not available'}
            </pre>
        </div>
    );
}

function ArtifactsTab({ artifacts, onArtifactClick }) {
    return (
        <div>
            <h5 className="text-sm font-semibold text-slate-700 mb-3">Produced Artifacts</h5>
            {artifacts?.length > 0 ? (
                <div className="space-y-2">
                    {artifacts.map(art => (
                        <motion.div
                            key={art.artifact_id}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => onArtifactClick(art)}
                            className="group flex items-center gap-3 p-3 bg-slate-50 hover:bg-white rounded-lg border border-slate-100 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
                        >
                            <div className="p-2 bg-white rounded-md text-slate-500 shadow-sm group-hover:text-primary-600 group-hover:scale-110 transition-all">
                                {art.type === 'Dataset' ? <Database size={18} /> :
                                    art.type === 'Model' ? <Box size={18} /> :
                                        art.type === 'Metrics' ? <BarChart2 size={18} /> :
                                            <FileText size={18} />}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold text-slate-900 truncate group-hover:text-primary-600 transition-colors">
                                    {art.name}
                                </p>
                                <p className="text-xs text-slate-500 truncate">{art.type}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Maximize2 size={14} className="text-slate-300 group-hover:text-primary-400 transition-colors" />
                                <ArrowRight size={14} className="text-slate-300 group-hover:text-primary-400 opacity-0 group-hover:opacity-100 transition-all" />
                            </div>
                        </motion.div>
                    ))}
                </div>
            ) : (
                <p className="text-sm text-slate-500 italic">No artifacts produced by this step</p>
            )}
        </div>
    );
}

function ArtifactModal({ artifact, onClose }) {
    if (!artifact) return null;

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
                    className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-gradient-to-r from-primary-50 to-purple-50">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-white rounded-xl shadow-sm">
                                {artifact.type === 'Dataset' ? <Database size={24} className="text-blue-600" /> :
                                    artifact.type === 'Model' ? <Box size={24} className="text-purple-600" /> :
                                        artifact.type === 'Metrics' ? <BarChart2 size={24} className="text-emerald-600" /> :
                                            <FileText size={24} className="text-slate-600" />}
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-slate-900">{artifact.name}</h3>
                                <p className="text-sm text-slate-500">{artifact.type}</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-white rounded-lg transition-colors"
                        >
                            <X size={20} className="text-slate-400" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[60vh]">
                        <div className="space-y-4">
                            {/* Properties */}
                            {artifact.properties && Object.keys(artifact.properties).length > 0 && (
                                <div>
                                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Properties</h4>
                                    <div className="grid grid-cols-2 gap-3">
                                        {Object.entries(artifact.properties).map(([key, value]) => (
                                            <div key={key} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                                                <span className="text-xs text-slate-500 block mb-1">{key}</span>
                                                <span className="text-sm font-mono font-semibold text-slate-900">
                                                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Value Preview */}
                            {artifact.value && (
                                <div>
                                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Value Preview</h4>
                                    <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono overflow-x-auto">
                                        {artifact.value}
                                    </pre>
                                </div>
                            )}

                            {/* Metadata */}
                            <div>
                                <h4 className="text-sm font-semibold text-slate-700 mb-3">Metadata</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Artifact ID:</span>
                                        <span className="font-mono text-xs text-slate-700">{artifact.artifact_id}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500">Step:</span>
                                        <span className="font-medium text-slate-700">{artifact.step}</span>
                                    </div>
                                    {artifact.created_at && (
                                        <div className="flex justify-between">
                                            <span className="text-slate-500">Created:</span>
                                            <span className="text-slate-700">{format(new Date(artifact.created_at), 'MMM d, yyyy HH:mm:ss')}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-2">
                        <Button variant="ghost" onClick={onClose}>Close</Button>
                        <Button variant="primary">Download</Button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
