import React, { useEffect, useState, useMemo } from 'react';
import { fetchApi } from '../../../utils/api';
import { downloadArtifactById } from '../../../utils/downloads';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, Calendar, Package, ArrowRight, BarChart2, FileText, Database, Box, ChevronRight, Activity, Layers, Code2, Terminal, Info, X, Maximize2, TrendingUp, Download, ArrowDownCircle, ArrowUpCircle, Tag, Zap, AlertCircle, FolderPlus, Cloud, Server, LineChart, Minimize2 } from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { ArtifactViewer } from '../../../components/ArtifactViewer';
import { PipelineGraph } from '../../../components/PipelineGraph';
import { ProjectSelector } from '../../../components/ProjectSelector';
import { CodeSnippet } from '../../../components/ui/CodeSnippet';
import { TrainingMetricsPanel } from '../../../components/TrainingMetricsPanel';

export function RunDetails() {
    const { runId } = useParams();
    const [run, setRun] = useState(null);
    const [artifacts, setArtifacts] = useState([]);
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedStep, setSelectedStep] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [selectedArtifact, setSelectedArtifact] = useState(null);
    const [cloudStatus, setCloudStatus] = useState(null);
    const [isPolling, setIsPolling] = useState(false);
    const [stopping, setStopping] = useState(false);
    const [stepLogs, setStepLogs] = useState({});
    const [stepPanelExpanded, setStepPanelExpanded] = useState(false);
    const [hasTrainingHistory, setHasTrainingHistory] = useState(false);

    const handleStopRun = async () => {
        if (!confirm('Are you sure you want to stop this run?')) return;

        setStopping(true);
        try {
            await fetchApi(`/api/runs/${runId}/stop`, {
                method: 'POST'
            });
            // Refresh run data
            const res = await fetchApi(`/api/runs/${runId}`);
            const data = await res.json();
            setRun(data);
        } catch (error) {
            console.error('Failed to stop run:', error);
            alert('Failed to stop run');
        } finally {
            setStopping(false);
        }
    };

    const handleProjectUpdate = async (newProject) => {
        try {
            await fetchApi(`/api/runs/${runId}/project`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: newProject })
            });
            setRun(prev => ({ ...prev, project: newProject }));
        } catch (error) {
            console.error('Failed to update project:', error);
        }
    };

    // Fetch cloud status for remote runs
    useEffect(() => {
        if (!run) return;

        const fetchCloudStatus = async () => {
            try {
                const res = await fetchApi(`/api/runs/${runId}/cloud-status`);
                const data = await res.json();
                setCloudStatus(data);

                // Continue polling if run is remote and not finished
                if (data.is_remote && data.cloud_status && !data.cloud_status.is_finished) {
                    setIsPolling(true);
                } else {
                    setIsPolling(false);
                }
            } catch (error) {
                console.error('Failed to fetch cloud status:', error);
                setIsPolling(false);
            }
        };

        fetchCloudStatus();

        // Poll every 5 seconds if remote and not finished
        let interval;
        if (isPolling) {
            interval = setInterval(fetchCloudStatus, 5000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [runId, run, isPolling]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [runRes, assetsRes] = await Promise.all([
                    fetchApi(`/api/runs/${runId}`),
                    fetchApi(`/api/assets?run_id=${runId}`)
                ]);

                const runData = await runRes.json();
                const assetsData = await assetsRes.json();

                let metricsData = [];
                try {
                    const mRes = await fetchApi(`/api/runs/${runId}/metrics`);
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
            <div className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-100 dark:border-slate-700 shadow-sm">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Link to="/runs" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">Runs</Link>
                        <ChevronRight size={14} className="text-slate-300" />
                        <span className="text-sm text-slate-900 dark:text-white font-medium">{run.run_id}</span>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${run.status === 'completed' ? 'bg-emerald-500' : run.status === 'failed' ? 'bg-rose-500' : 'bg-amber-500'}`} />
                        Run: <span className="font-mono text-slate-500">{run.run_id?.substring(0, 8) || runId?.substring(0, 8) || 'N/A'}</span>
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-2">
                        <Layers size={16} />
                        Pipeline: <span className="font-medium text-slate-700 dark:text-slate-200">{run.pipeline_name}</span>
                        {cloudStatus?.is_remote && (
                            <Badge variant="secondary" className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center gap-1">
                                <Cloud size={12} />
                                {cloudStatus.orchestrator_type}
                            </Badge>
                        )}
                        {cloudStatus?.is_remote && isPolling && (
                            <span className="text-xs text-amber-600 flex items-center gap-1 animate-pulse">
                                <Activity size={12} />
                                Live
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <div className="flex items-center gap-2">
                        <ProjectSelector currentProject={run.project} onUpdate={handleProjectUpdate} />
                        <Badge variant={statusVariant} className="text-sm px-4 py-1.5 uppercase tracking-wide shadow-sm">
                            {cloudStatus?.cloud_status?.status || run.status}
                        </Badge>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">ID: {run.run_id}</span>
                    {run.status === 'running' && (
                        <Button
                            variant="danger"
                            size="sm"
                            onClick={handleStopRun}
                            disabled={stopping}
                            className="mt-2"
                        >
                            {stopping ? 'Stopping...' : 'Stop Run'}
                        </Button>
                    )}
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

            {/* Main Content - Dynamic Split View */}
            <div className={`grid gap-6 transition-all duration-300 ${
                stepPanelExpanded
                    ? 'grid-cols-1 lg:grid-cols-2'
                    : 'grid-cols-1 lg:grid-cols-3'
            }`}>
                {/* DAG Visualization */}
                <div className={stepPanelExpanded ? 'lg:col-span-1' : 'lg:col-span-2'}>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Activity className="text-primary-500" /> Pipeline Execution Graph
                    </h3>
                    <div className={`min-h-[500px] ${stepPanelExpanded ? 'h-[500px]' : 'h-[calc(100vh-240px)]'}`}>
                        {run.dag ? (
                            <PipelineGraph
                                dag={run.dag}
                                steps={run.steps}
                                selectedStep={selectedStep}
                                onStepSelect={setSelectedStep}
                                onArtifactSelect={(name) => {
                                    const found = artifacts.find(a => a.name === name);
                                    if (found) {
                                        setSelectedArtifact(found);
                                    } else {
                                        console.warn(`Artifact ${name} not found in assets list`);
                                    }
                                }}
                            />
                        ) : (
                            <Card className="h-full flex items-center justify-center">
                                <p className="text-slate-500">DAG visualization not available</p>
                            </Card>
                        )}
                    </div>
                </div>

                {/* Step Details Panel - Expandable */}
                <div className={stepPanelExpanded ? 'lg:col-span-1' : ''}>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Info className="text-primary-500" /> Step Details
                        </h3>
                        <button
                            onClick={() => setStepPanelExpanded(!stepPanelExpanded)}
                            className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                            title={stepPanelExpanded ? 'Collapse panel' : 'Expand panel'}
                        >
                            <Maximize2 size={16} className="text-slate-600 dark:text-slate-300" />
                        </button>
                    </div>

                    {selectedStepData ? (
                        <Card className={`overflow-hidden transition-all duration-300 ${
                            stepPanelExpanded ? 'h-auto' : ''
                        }`}>
                            {/* Step Header */}
                            <div className="pb-4 border-b border-slate-100 dark:border-slate-700">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-lg font-bold text-slate-900 dark:text-white">{selectedStep}</h4>
                                </div>
                                <div className="flex items-center gap-2 mt-2">
                                    <Badge variant={selectedStepData.success ? 'success' : 'danger'} className="text-xs">
                                        {selectedStepData.success ? 'Success' : 'Failed'}
                                    </Badge>
                                    {selectedStepData.cached && (
                                        <Badge variant="secondary" className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                                            Cached
                                        </Badge>
                                    )}
                                    <span className="text-xs font-mono text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                        {selectedStepData.duration?.toFixed(2)}s
                                    </span>
                                </div>
                            </div>

                            {/* Live Heartbeat Indicator */}
                            {selectedStepData.status === 'running' && (
                                <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800 flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300">
                                        <Activity size={14} className="animate-pulse" />
                                        <span>Step is running</span>
                                    </div>
                                    {selectedStepData.last_heartbeat && (
                                        <span className="text-xs text-blue-600 dark:text-blue-400 font-mono">
                                            Last heartbeat: {((Date.now() / 1000) - selectedStepData.last_heartbeat).toFixed(1)}s ago
                                        </span>
                                    )}
                                </div>
                            )}
                            {selectedStepData.status === 'dead' && (
                                <div className="px-4 py-2 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-100 dark:border-rose-800 flex items-center gap-2">
                                    <AlertCircle size={14} className="text-rose-600 dark:text-rose-400" />
                                    <span className="text-sm font-medium text-rose-700 dark:text-rose-300">
                                        Step detected as DEAD (missed heartbeats)
                                    </span>
                                </div>
                            )}

                            {/* Tabs */}
                            <div className="flex gap-1 border-b border-slate-100 dark:border-slate-700 mt-4 overflow-x-auto">
                                <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
                                    <Info size={14} /> Overview
                                </TabButton>
                                <TabButton active={activeTab === 'code'} onClick={() => setActiveTab('code')}>
                                    <Code2 size={14} /> Code
                                </TabButton>
                                <TabButton active={activeTab === 'artifacts'} onClick={() => setActiveTab('artifacts')}>
                                    <Package size={14} /> Artifacts
                                </TabButton>
                                <TabButton active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} data-tab="logs">
                                    <Terminal size={14} /> Logs
                                </TabButton>
                            </div>

                            {/* Tab Content - Larger when expanded */}
                            <div className={`mt-4 overflow-y-auto transition-all duration-300 ${
                                stepPanelExpanded ? 'max-h-[600px]' : 'max-h-[450px]'
                            }`}>
                                {activeTab === 'overview' && (
                                    <OverviewTab
                                        stepData={selectedStepData}
                                        metrics={selectedStepMetrics}
                                        runId={runId}
                                        stepName={selectedStep}
                                    />
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
                                {activeTab === 'logs' && (
                                    <LogsViewer
                                        runId={runId}
                                        stepName={selectedStep}
                                        isRunning={run.status === 'running'}
                                        maxHeight={stepPanelExpanded ? 'max-h-[500px]' : 'max-h-96'}
                                    />
                                )}
                            </div>
                        </Card>
                    ) : (
                        <Card className="p-12 text-center border-2 border-dashed border-slate-200 dark:border-slate-700">
                            <Info size={32} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                            <p className="text-slate-500 dark:text-slate-400 font-medium">Select a step to view details</p>
                            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Click on any step in the graph</p>
                        </Card>
                    )}
                </div>
            </div>

            {/* Training Metrics Section - Only shown if there's training data */}
            <TrainingMetricsSectionWrapper
                runId={runId}
                isRunning={run.status === 'running'}
            />

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
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{label}</p>
                    <p className="text-xl font-bold text-slate-900 dark:text-white">{value}</p>
                </div>
            </div>
        </Card>
    );
}

function TabButton({ active, onClick, children, ...props }) {
    return (
        <button
            onClick={onClick}
            {...props}
            className={`
                flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2
                ${active
                    ? 'text-primary-600 dark:text-primary-400 border-primary-600 dark:border-primary-400'
                    : 'text-slate-500 dark:text-slate-400 border-transparent hover:text-slate-700 dark:hover:text-slate-200'
                }
            `}
        >
            {children}
        </button>
    );
}

function OverviewTab({ stepData, metrics, runId, stepName }) {
    const formatDuration = (seconds) => {
        if (!seconds) return 'N/A';
        if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
        if (seconds < 60) return `${seconds.toFixed(2)}s`;
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(0);
        return `${mins}m ${secs}s`;
    };

    return (
        <div className="space-y-6">
            {/* Status & Execution Info */}
            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gradient-to-br from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2 mb-2">
                        <Clock size={14} className="text-slate-400" />
                        <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Duration</span>
                    </div>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                        {formatDuration(stepData.duration)}
                    </p>
                </div>
                <div className="p-4 bg-gradient-to-br from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2 mb-2">
                        <Activity size={14} className="text-slate-400" />
                        <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {stepData.status === 'dead' ? (
                            <>
                                <AlertCircle size={20} className="text-rose-500" />
                                <span className="text-lg font-bold text-rose-700 dark:text-rose-400">Dead</span>
                            </>
                        ) : stepData.success ? (
                            <>
                                <CheckCircle size={20} className="text-emerald-500" />
                                <span className="text-lg font-bold text-emerald-700">Success</span>
                            </>
                        ) : stepData.error ? (
                            <>
                                <XCircle size={20} className="text-rose-500" />
                                <span className="text-lg font-bold text-rose-700">Failed</span>
                            </>
                        ) : (
                            <>
                                <Clock size={20} className="text-amber-500" />
                                <span className="text-lg font-bold text-amber-700 dark:text-amber-500">Pending</span>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Heartbeat Card */}
            {
                stepData.last_heartbeat && (
                    <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <h5 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-2 flex items-center gap-2">
                            <Activity size={16} className="text-blue-500" />
                            System Heartbeat
                        </h5>
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-slate-500 dark:text-slate-400">Last received:</span>
                            <span className="font-mono font-medium text-slate-900 dark:text-white">
                                {new Date(stepData.last_heartbeat * 1000).toLocaleTimeString()}
                                <span className="text-xs text-slate-400 ml-2">
                                    ({((Date.now() / 1000) - stepData.last_heartbeat).toFixed(1)}s ago)
                                </span>
                            </span>
                        </div>
                    </div>
                )
            }

            {/* Logs Preview (All Statuses) */}
            <div className="mt-6">
                <h5 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <Terminal size={16} />
                    Logs Preview
                </h5>
                <LogsViewer
                    runId={runId}
                    stepName={stepName}
                    isRunning={stepData.status === 'running'}
                    maxHeight="max-h-48"
                    minimal={true}
                />
                <div className="mt-2 text-right">
                    <button
                        onClick={() => document.querySelector('[data-tab="logs"]')?.click()}
                        className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
                    >
                        View Full Logs →
                    </button>
                </div>
            </div>

            {/* Inputs & Outputs */}
            {
                (stepData.inputs?.length > 0 || stepData.outputs?.length > 0) && (
                    <div className="space-y-4">
                        <h5 className="text-sm font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                            <Database size={16} />
                            Data Flow
                        </h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {stepData.inputs?.length > 0 && (
                                <div className="p-4 bg-blue-50/50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800">
                                    <div className="flex items-center gap-2 mb-3">
                                        <ArrowDownCircle size={16} className="text-blue-600" />
                                        <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">Inputs</span>
                                        <Badge variant="secondary" className="ml-auto text-xs">{stepData.inputs.length}</Badge>
                                    </div>
                                    <div className="space-y-1.5">
                                        {stepData.inputs.map((input, idx) => (
                                            <div key={idx} className="flex items-center gap-2 p-2 bg-white dark:bg-slate-800 rounded-lg border border-blue-100 dark:border-blue-800/50">
                                                <Database size={12} className="text-blue-500 flex-shrink-0" />
                                                <span className="text-sm font-mono text-slate-700 dark:text-slate-200 truncate">{input}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {stepData.outputs?.length > 0 && (
                                <div className="p-4 bg-purple-50/50 dark:bg-purple-900/10 rounded-xl border border-purple-100 dark:border-purple-800">
                                    <div className="flex items-center gap-2 mb-3">
                                        <ArrowUpCircle size={16} className="text-purple-600" />
                                        <span className="text-sm font-semibold text-purple-900 dark:text-purple-100">Outputs</span>
                                        <Badge variant="secondary" className="ml-auto text-xs">{stepData.outputs.length}</Badge>
                                    </div>
                                    <div className="space-y-1.5">
                                        {stepData.outputs.map((output, idx) => (
                                            <div key={idx} className="flex items-center gap-2 p-2 bg-white dark:bg-slate-800 rounded-lg border border-purple-100 dark:border-purple-800/50">
                                                <Box size={12} className="text-purple-500 flex-shrink-0" />
                                                <span className="text-sm font-mono text-slate-700 dark:text-slate-200 truncate">{output}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )
            }

            {/* Tags/Metadata */}
            {
                stepData.tags && Object.keys(stepData.tags).length > 0 && (
                    <div>
                        <h5 className="text-sm font-bold text-slate-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <Tag size={16} />
                            Metadata
                        </h5>
                        <div className="grid grid-cols-2 gap-3">
                            {Object.entries(stepData.tags).map(([key, value]) => (
                                <div key={key} className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
                                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">{key}</div>
                                    <div className="text-sm font-mono font-medium text-slate-900 dark:text-white truncate">{String(value)}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )
            }

            {/* Cached Badge */}
            {
                stepData.cached && (
                    <div className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-xl border-2 border-blue-200 dark:border-blue-800">
                        <div className="flex items-center gap-3">
                            <Zap size={24} className="text-blue-600" />
                            <div>
                                <h6 className="font-bold text-blue-900 dark:text-blue-100">Cached Result</h6>
                                <p className="text-sm text-blue-700 dark:text-blue-300">This step used cached results from a previous run</p>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Error */}
            {
                stepData.error && (
                    <div>
                        <h5 className="text-sm font-bold text-rose-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <AlertCircle size={16} />
                            Error Details
                        </h5>
                        <div className="p-4 bg-rose-50 dark:bg-rose-900/20 rounded-xl border-2 border-rose-200 dark:border-rose-800">
                            <pre className="text-sm font-mono text-rose-700 dark:text-rose-300 whitespace-pre-wrap overflow-x-auto">
                                {stepData.error}
                            </pre>
                        </div>
                    </div>
                )
            }

            {/* Metrics with Visualization */}
            {
                metrics?.length > 0 && (
                    <div>
                        <h5 className="text-sm font-bold text-slate-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <TrendingUp size={16} />
                            Performance Metrics
                        </h5>
                        <div className="grid grid-cols-2 gap-3">
                            {metrics.map((metric, idx) => (
                                <MetricCard key={idx} metric={metric} />
                            ))}
                        </div>
                    </div>
                )
            }
        </div >
    );
}

function MetricCard({ metric }) {
    const isNumeric = typeof metric.value === 'number';
    const displayValue = isNumeric ? metric.value.toFixed(4) : metric.value;

    return (
        <div className="p-3 bg-gradient-to-br from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 transition-all group">
            <span className="text-xs text-slate-500 dark:text-slate-400 block truncate mb-1" title={metric.name}>
                {metric.name}
            </span>
            <div className="flex items-baseline gap-2">
                <span className="text-xl font-mono font-bold text-slate-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
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
        <CodeSnippet
            code={sourceCode || '# Source code not available'}
            language="python"
            title="Step Source Code"
        />
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
                                <button
                                    className="p-2 rounded-lg hover:bg-white transition-colors text-slate-400 hover:text-primary-600 disabled:opacity-40"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        downloadArtifactById(art.artifact_id);
                                    }}
                                    disabled={!art.artifact_id}
                                >
                                    <Download size={14} />
                                </button>
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
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => downloadArtifactById(artifact.artifact_id)}
                                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-600 text-white text-sm font-semibold hover:bg-primary-500 transition-colors disabled:opacity-50"
                                disabled={!artifact.artifact_id}
                            >
                                <Download size={16} /> Download
                            </button>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-white rounded-lg transition-colors"
                            >
                                <X size={20} className="text-slate-400" />
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[60vh]">
                        <div className="space-y-4">
                            {/* Rich Viewer */}
                            <ArtifactViewer artifact={artifact} />

                            {/* Properties (collapsible or below) */}
                            {artifact.properties && Object.keys(artifact.properties).length > 0 && (
                                <div className="mt-6 pt-6 border-t border-slate-100">
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

                            {/* Metadata */}
                            <div className="mt-6">
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

function LogsViewer({ runId, stepName, isRunning, maxHeight = "max-h-96", minimal = false }) {
    const [logs, setLogs] = useState('');
    const [loading, setLoading] = useState(true);
    const [useWebSocket, setUseWebSocket] = useState(true);
    const wsRef = React.useRef(null);
    const logsEndRef = React.useRef(null);

    // Auto-scroll to bottom when new logs arrive (only if not viewing history?)
    // Actually always auto-scroll for now unless user scrolled up (advanced)
    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    // ... (rest of logic same) ...

    // Reset logs when step changes
    useEffect(() => {
        setLogs('');
        setLoading(true);

        // Close existing WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, [stepName]);

    // Fetch initial logs and set up WebSocket
    useEffect(() => {
        let isMounted = true;

        // Fetch initial logs
        const fetchInitialLogs = async () => {
            try {
                const res = await fetchApi(`/api/runs/${runId}/steps/${stepName}/logs`);
                const data = await res.json();
                if (isMounted && data.logs) {
                    setLogs(data.logs);
                }
            } catch (error) {
                console.error('Failed to fetch logs:', error);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchInitialLogs();

        // Set up WebSocket for live updates if running
        if (isRunning && useWebSocket) {
            try {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/ws/runs/${runId}/steps/${stepName}/logs`;
                const ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    console.log('WebSocket connected for logs');
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'log' && isMounted) {
                            setLogs(prev => prev + data.content + '\n');
                        }
                    } catch (e) {
                        // Plain text message
                        if (isMounted && event.data !== 'pong') {
                            setLogs(prev => prev + event.data + '\n');
                        }
                    }
                };

                ws.onerror = () => {
                    console.log('WebSocket error, falling back to polling');
                    setUseWebSocket(false);
                };

                ws.onclose = () => {
                    console.log('WebSocket closed');
                };

                wsRef.current = ws;
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                setUseWebSocket(false);
            }
        }

        // Fallback to polling if WebSocket not available
        let interval;
        if (isRunning && !useWebSocket) {
            let currentOffset = 0;
            interval = setInterval(async () => {
                try {
                    const res = await fetchApi(`/api/runs/${runId}/steps/${stepName}/logs?offset=${currentOffset}`);
                    const data = await res.json();
                    if (isMounted && data.logs) {
                        setLogs(prev => prev + data.logs);
                        currentOffset = data.offset;
                    }
                } catch (error) {
                    console.error('Failed to fetch logs:', error);
                }
            }, 2000);
        }

        return () => {
            isMounted = false;
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            if (interval) clearInterval(interval);
        };
    }, [runId, stepName, isRunning, useWebSocket]);

    if (loading && !logs) {
        return (
            <div className="flex items-center justify-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className={`bg-slate-900 rounded-lg p-4 font-mono text-sm overflow-x-auto ${maxHeight} overflow-y-auto`}>
            {logs ? (
                <>
                    <pre className="text-green-400 whitespace-pre-wrap break-words">{minimal ? logs.split('\n').slice(-10).join('\n') : logs}</pre>
                    <div ref={logsEndRef} />
                </>
            ) : (
                <div className="text-slate-500 italic">No logs available for this step.</div>
            )}
            {!minimal && isRunning && (
                <div className="mt-2 text-amber-500 flex items-center gap-2 animate-pulse">
                    <Activity size={14} />
                    {useWebSocket ? 'Live streaming...' : 'Polling for logs...'}
                </div>
            )}
        </div>
    );
}

/**
 * Training Metrics Section Wrapper
 * Only renders the training metrics section if there's actual training data.
 * This prevents showing an empty section for non-training pipelines.
 */
function TrainingMetricsSectionWrapper({ runId, isRunning }) {
    const [hasData, setHasData] = useState(false);
    const [isExpanded, setIsExpanded] = useState(true);
    const [loading, setLoading] = useState(true);

    // Check if training data exists
    useEffect(() => {
        const checkTrainingData = async () => {
            try {
                const res = await fetchApi(`/api/runs/${runId}/training-history`);
                if (res.ok) {
                    const data = await res.json();
                    setHasData(data.has_history && data.training_history?.epochs?.length > 0);
                }
            } catch (err) {
                console.error('Error checking training history:', err);
            } finally {
                setLoading(false);
            }
        };

        if (runId) {
            checkTrainingData();
        }
    }, [runId]);

    // Don't render anything if no training data
    if (loading) return null;
    if (!hasData) return null;

    return (
        <div className="mt-8">
            <Card className="overflow-hidden">
                <div
                    className="p-6 cursor-pointer flex items-center justify-between bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-xl shadow-lg">
                            <LineChart size={20} className="text-white" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                Training Metrics
                            </h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                Interactive training history visualization
                            </p>
                        </div>
                    </div>
                    <ChevronRight
                        size={20}
                        className={`text-slate-400 transform transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                    />
                </div>
                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                        >
                            <div className="p-6">
                                <TrainingMetricsPanel
                                    runId={runId}
                                    isRunning={isRunning}
                                    autoRefresh={true}
                                />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Card>
        </div>
    );
}
