import React, { useState, useEffect, useCallback } from 'react';
import {
    Microscope,
    Play,
    RefreshCw,
    Sliders,
    BarChart3,
    Loader2,
    ChevronRight,
    Zap,
    LineChart,
    Settings,
    Download,
    History,
    Trash2,
    Plus,
    Minus,
    Globe,
    Link,
    Unlink,
    Key,
    Code,
    FileJson,
    Table,
    Copy,
    Check,
    AlertCircle,
    GitCompare,
    ArrowLeftRight,
    SplitSquareHorizontal,
    TrendingUp,
    Activity,
    Sparkles,
    Target,
    Layers,
    PanelLeftClose,
    PanelLeftOpen,
    Terminal,
    Info,
    X
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { motion, AnimatePresence } from 'framer-motion';

// Helper to safely display values
const formatValue = (val) => {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'number') return val.toFixed(4);
    if (typeof val === 'object') return JSON.stringify(val, null, 2);
    return String(val);
};

// Simple JSON Editor component
const JsonEditor = ({ value, onChange, error }) => {
    const [text, setText] = useState('');
    const [parseError, setParseError] = useState(null);

    useEffect(() => {
        setText(JSON.stringify(value, null, 2));
    }, []);

    const handleChange = (e) => {
        const newText = e.target.value;
        setText(newText);
        try {
            const parsed = JSON.parse(newText);
            setParseError(null);
            onChange(parsed);
        } catch (err) {
            setParseError(err.message);
        }
    };

    return (
        <div className="relative">
            <textarea
                value={text}
                onChange={handleChange}
                className={`w-full h-48 p-3 font-mono text-sm rounded-lg border-2 transition-all
                    ${parseError ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/10' : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900'}
                    focus:outline-none focus:ring-2 focus:ring-violet-500`}
                placeholder="Enter JSON input..."
            />
            {parseError && (
                <div className="absolute bottom-0 left-0 right-0 px-3 py-2 bg-rose-500 text-white text-xs rounded-b-lg">
                    <AlertCircle size={12} className="inline mr-1" />
                    {parseError}
                </div>
            )}
        </div>
    );
};

// Comparison Result Card
const ComparisonResult = ({ results, models }) => {
    if (!results || results.length < 2) return null;

    const metrics = Object.keys(results[0]?.outputs || {});

    return (
        <div className="space-y-4">
            <h4 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <GitCompare size={16} className="text-violet-500" />
                Comparison Results
            </h4>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-slate-100 dark:bg-slate-800">
                            <th className="px-4 py-2 text-left font-medium text-slate-600">Metric</th>
                            {results.map((r, i) => (
                                <th key={i} className="px-4 py-2 text-center font-medium text-slate-600">
                                    {models[i]?.name || `Model ${i + 1}`}
                                </th>
                            ))}
                            <th className="px-4 py-2 text-center font-medium text-slate-600">Δ Diff</th>
                        </tr>
                    </thead>
                    <tbody>
                        {metrics.map(metric => (
                            <tr key={metric} className="border-b border-slate-200 dark:border-slate-700">
                                <td className="px-4 py-2 font-medium text-slate-700 dark:text-slate-300">{metric}</td>
                                {results.map((r, i) => (
                                    <td key={i} className="px-4 py-2 text-center text-violet-600 dark:text-violet-400 font-mono">
                                        {formatValue(r.outputs?.[metric])}
                                    </td>
                                ))}
                                <td className="px-4 py-2 text-center font-mono">
                                    {typeof results[0]?.outputs?.[metric] === 'number' && typeof results[1]?.outputs?.[metric] === 'number' ? (
                                        <span className={results[0].outputs[metric] > results[1].outputs[metric] ? 'text-emerald-500' : 'text-rose-500'}>
                                            {((results[0].outputs[metric] - results[1].outputs[metric]) * 100 / Math.max(Math.abs(results[1].outputs[metric]), 0.0001)).toFixed(2)}%
                                        </span>
                                    ) : '-'}
                                </td>
                            </tr>
                        ))}
                        <tr className="bg-slate-50 dark:bg-slate-800/50">
                            <td className="px-4 py-2 font-medium text-slate-600">Latency</td>
                            {results.map((r, i) => (
                                <td key={i} className="px-4 py-2 text-center font-mono text-slate-500">
                                    {r.latency_ms?.toFixed(2)}ms
                                </td>
                            ))}
                            <td className="px-4 py-2 text-center font-mono">
                                {results[0]?.latency_ms && results[1]?.latency_ms ? (
                                    <span className={results[0].latency_ms < results[1].latency_ms ? 'text-emerald-500' : 'text-rose-500'}>
                                        {((results[0].latency_ms - results[1].latency_ms) / results[1].latency_ms * 100).toFixed(1)}%
                                    </span>
                                ) : '-'}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// Enhanced Chart Component
const PredictionChart = ({ data, title }) => {
    if (!data || data.length === 0) return null;

    const maxVal = Math.max(...data.map(d => Math.abs(d.value || d.prediction || 0)));

    return (
        <div className="p-6 bg-white dark:bg-slate-800/50 rounded-2xl border border-slate-200 dark:border-slate-700/50 shadow-lg shadow-violet-500/5 backdrop-blur-sm">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6 flex items-center gap-2">
                <BarChart3 size={14} />
                {title}
            </h4>
            <div className="flex items-end gap-2 h-40">
                {data.map((d, i) => {
                    const val = d.value || d.prediction || 0;
                    const height = maxVal > 0 ? (Math.abs(val) / maxVal) * 100 : 50;
                    const isPositive = val >= 0;
                    return (
                        <div key={i} className="flex-1 flex flex-col items-center group relative h-full justify-end">
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: `${Math.max(height, 5)}%`, opacity: 1 }}
                                transition={{ duration: 0.6, delay: i * 0.05, ease: "backOut" }}
                                className={`w-full rounded-t-lg transition-all cursor-pointer relative overflow-hidden
                                    ${isPositive
                                        ? 'bg-gradient-to-t from-violet-600 to-indigo-400 group-hover:from-violet-500 group-hover:to-indigo-300'
                                        : 'bg-gradient-to-t from-rose-600 to-pink-400 group-hover:from-rose-500 group-hover:to-pink-300'
                                    }`}
                            >
                                <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </motion.div>

                            {/* Tooltip */}
                            <div className="absolute -top-10 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-all duration-200 bg-slate-900/90 text-white text-[10px] font-mono px-2 py-1 rounded-md whitespace-nowrap z-20 pointer-events-none shadow-xl -translate-y-2 group-hover:translate-y-0">
                                {d.label}: <span className={isPositive ? "text-emerald-400" : "text-rose-400"}>{formatValue(val)}</span>
                            </div>
                        </div>
                    );
                })}
            </div>
            <div className="flex justify-between mt-3 px-1">
                <span className="text-[10px] font-medium text-slate-400">{data[0]?.label || '0'}</span>
                <span className="text-[10px] font-medium text-slate-400">{data[data.length - 1]?.label || data.length - 1}</span>
            </div>
        </div>
    );
};

// Logs Panel Component for live deployment logs
const LogsPanel = ({ logs, onClose, deploymentId }) => {
    const logsEndRef = React.useRef(null);

    React.useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-[#0D1117] rounded-xl border border-slate-800 overflow-hidden shadow-2xl flex flex-col h-full"
        >
            <div className="flex items-center justify-between px-4 py-2 bg-[#161B22] border-b border-slate-800">
                <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-emerald-500" />
                    <span className="text-xs font-mono text-slate-400">root@deployment:~/{deploymentId}</span>
                </div>
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed space-y-0.5 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                {logs.length === 0 ? (
                    <div className="text-slate-600 italic text-center mt-10">Waiting for logs stream...</div>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className="flex gap-3 hover:bg-white/5 px-2 -mx-2 rounded transition-colors group">
                            <span className="text-slate-600 shrink-0 select-none w-16 text-right">
                                {new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}
                            </span>
                            <span className={`font-bold shrink-0 w-12 ${log.level === 'ERROR' ? 'text-rose-500' :
                                log.level === 'WARNING' ? 'text-amber-500' :
                                    log.level === 'INFO' ? 'text-emerald-500' : 'text-blue-400'
                                }`}>
                                {log.level}
                            </span>
                            <span className="text-slate-300 group-hover:text-white transition-colors">{log.message}</span>
                        </div>
                    ))
                )}
                <div ref={logsEndRef} />
            </div>
        </motion.div>
    );
};

// Model Info Panel Component
const ModelInfoPanel = ({ modelInfo }) => {
    if (!modelInfo) return null;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700/50 shadow-sm overflow-hidden"
        >
            <div className="border-b border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-900/50 p-4">
                <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-violet-100 dark:bg-violet-900/30 rounded-lg">
                        <Info size={16} className="text-violet-600 dark:text-violet-400" />
                    </div>
                    <div>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white">Model Specifications</h4>
                        <p className="text-[10px] text-slate-500">Technical details and architecture</p>
                    </div>
                </div>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Framework</label>
                    <div className="flex items-center gap-2">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">{modelInfo.framework || 'Unknown'}</div>
                        <Badge variant="secondary" className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500">{modelInfo.framework_version || 'v1.0'}</Badge>
                    </div>
                </div>

                {modelInfo.input_shape && (
                    <div className="space-y-1">
                        <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Input Shape</label>
                        <div className="font-mono text-xs font-medium text-violet-600 dark:text-violet-300 bg-violet-50 dark:bg-violet-900/20 px-2 py-1 rounded-md inline-block border border-violet-100 dark:border-violet-800/30">
                            [{modelInfo.input_shape.map(s => s || '?').join(', ')}]
                        </div>
                    </div>
                )}

                {modelInfo.output_shape && (
                    <div className="space-y-1">
                        <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Output Shape</label>
                        <div className="font-mono text-xs font-medium text-emerald-600 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded-md inline-block border border-emerald-100 dark:border-emerald-800/30">
                            [{modelInfo.output_shape.map(s => s || '?').join(', ')}]
                        </div>
                    </div>
                )}

                {modelInfo.layer_count !== undefined && (
                    <div className="space-y-1">
                        <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Layers</label>
                        <div className="font-semibold text-slate-700 dark:text-slate-300">{modelInfo.layer_count}</div>
                    </div>
                )}

                {modelInfo.total_params !== undefined && (
                    <div className="space-y-1">
                        <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Parameters</label>
                        <div className="font-mono font-medium text-slate-700 dark:text-slate-300">
                            {modelInfo.total_params.toLocaleString()}
                        </div>
                    </div>
                )}

                {modelInfo.input_features && (
                    <div className="col-span-full space-y-2">
                        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-1">
                            <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Feature Names</label>
                            <span className="text-[10px] bg-slate-100 px-1.5 rounded-full text-slate-500">{modelInfo.input_features.length} features</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto pr-2 scrollbar-thin">
                            {Array.isArray(modelInfo.input_features) ? modelInfo.input_features.map(f => (
                                <span key={f} className="text-[10px] bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-slate-600 dark:text-slate-400 font-mono">{f}</span>
                            )) : <span className="text-xs text-slate-500 italic">{modelInfo.input_features}</span>}
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export function ModelExplorer() {
    const [deployments, setDeployments] = useState([]);
    const [selectedModels, setSelectedModels] = useState([]); // Support multi-select for comparison
    const [schema, setSchema] = useState(null);
    const [inputs, setInputs] = useState({});
    const [predictions, setPredictions] = useState([]); // Array for comparison
    const [history, setHistory] = useState([]);
    const [sweepResults, setSweepResults] = useState(null);
    const [loading, setLoading] = useState(true);
    const [predicting, setPredicting] = useState(false);
    const [sweeping, setSweeping] = useState(false);

    // UI State
    const [inputMode, setInputMode] = useState('form'); // 'form' | 'json'
    const [viewMode, setViewMode] = useState('single'); // 'single' | 'compare'
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState(null);
    const [showLeftPanel, setShowLeftPanel] = useState(true);
    const [activeTab, setActiveTab] = useState('results'); // 'results', 'history', 'logs', 'info'

    // External API connection state
    const [connectionMode, setConnectionMode] = useState('internal');
    const [externalEndpoint, setExternalEndpoint] = useState('');
    const [externalApiKey, setExternalApiKey] = useState('');
    const [externalConnected, setExternalConnected] = useState(false);
    const [showExternalConfig, setShowExternalConfig] = useState(false);

    // Sweep configuration
    const [sweepParam, setSweepParam] = useState('');
    const [sweepMin, setSweepMin] = useState(0);
    const [sweepMax, setSweepMax] = useState(100);
    const [sweepSteps, setSweepSteps] = useState(10);

    // Logs streaming
    const [logs, setLogs] = useState([]);
    const [showLogs, setShowLogs] = useState(false);
    const [modelInfo, setModelInfo] = useState(null);

    useEffect(() => {
        fetchDeployments();
    }, []);

    const fetchDeployments = async () => {
        try {
            const response = await fetch('/api/deployments/');
            const data = await response.json();
            const running = (Array.isArray(data) ? data : []).filter(d => d.status === 'running');
            setDeployments(running);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch deployments:', err);
            setError('Failed to load deployments. Please check your connection.');
        } finally {
            setLoading(false);
        }
    };

    // Fetch model info (real introspection from loaded model)
    const fetchModelInfo = async (deploymentId) => {
        try {
            const response = await fetch(`/api/explorer/model-info/${deploymentId}`);
            if (response.ok) {
                const data = await response.json();
                setModelInfo(data);

                // If we have input_features, generate appropriate input fields
                if (data.input_features) {
                    const newInputs = {};
                    for (let i = 0; i < data.input_features; i++) {
                        const name = data.input_names?.[i] || `feature_${i}`;
                        newInputs[name] = 0.5;
                    }
                    setInputs(newInputs);
                }
            }
        } catch (err) {
            console.error('Failed to fetch model info:', err);
        }
    };

    // Fetch deployment logs
    const fetchLogs = async (deploymentId) => {
        try {
            const response = await fetch(`/api/explorer/logs/${deploymentId}?lines=50`);
            if (response.ok) {
                const data = await response.json();
                setLogs(data.logs || []);
            }
        } catch (err) {
            console.error('Failed to fetch logs:', err);
        }
    };

    // Poll logs when a model is selected and activeTab is logs
    useEffect(() => {
        if (selectedModels.length > 0 && activeTab === 'logs') {
            fetchLogs(selectedModels[0].id);
            const interval = setInterval(() => {
                fetchLogs(selectedModels[0].id);
            }, 2000);
            return () => clearInterval(interval);
        }
    }, [selectedModels, activeTab]);

    const selectModel = async (deployment, addToComparison = false) => {
        if (viewMode === 'compare' && addToComparison) {
            if (selectedModels.length < 2 && !selectedModels.find(m => m.id === deployment.id)) {
                setSelectedModels(prev => [...prev, deployment]);
            }
        } else {
            setSelectedModels([deployment]);
        }

        try {
            const response = await fetch(`/api/explorer/schema/${deployment.model_artifact_id}`);
            const data = await response.json();
            setSchema(data);
            setSweepResults(null); // Clear previous sweep results
            setPredictions([]);
            setLogs([]); // Clear previous logs
            setError(null);

            const initialInputs = {};
            data.inputs?.forEach(field => {
                if (field.default !== null && field.default !== undefined) {
                    initialInputs[field.name] = field.default;
                } else if (field.type === 'number') {
                    initialInputs[field.name] = (field.min_value || 0) + ((field.max_value || 100) - (field.min_value || 0)) / 2;
                } else if (field.type === 'integer') {
                    initialInputs[field.name] = Math.floor((field.min_value || 0) + ((field.max_value || 100) - (field.min_value || 0)) / 2);
                } else if (field.type === 'object' || field.type === 'array') {
                    initialInputs[field.name] = field.default || {};
                }
            });
            setInputs(initialInputs);
            setSweepParam(data.inputs?.find(f => f.type === 'number' || f.type === 'integer')?.name || '');

            // Also fetch real model info for the deployment
            fetchModelInfo(deployment.id);
        } catch (err) {
            console.error('Failed to fetch schema:', err);
            setError('Failed to load model schema. Using default inputs.');
        }
    };

    const runPrediction = async () => {
        if (selectedModels.length === 0) return;
        setPredicting(true);
        setError(null);

        try {
            const results = await Promise.all(
                selectedModels.map(async (model) => {
                    const startTime = Date.now();
                    const response = await fetch('/api/explorer/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            deployment_id: model.id,
                            inputs: inputs
                        })
                    });
                    const result = await response.json();

                    if (!response.ok) {
                        throw new Error(result.detail || 'Prediction failed');
                    }

                    return {
                        ...result,
                        model_name: model.name,
                        source: 'internal'
                    };
                })
            );

            setPredictions(results);
            setHistory(prev => [...results.map(r => ({ ...r, inputs: { ...inputs } })), ...prev].slice(0, 50));
        } catch (err) {
            console.error('Prediction failed:', err);
            setError(`Prediction failed: ${err.message}`);
        } finally {
            setPredicting(false);
        }
    };

    const runExternalPrediction = async () => {
        if (!externalEndpoint) return;
        setPredicting(true);
        setError(null);

        try {
            const startTime = Date.now();
            const headers = { 'Content-Type': 'application/json' };
            if (externalApiKey) {
                headers['Authorization'] = `Bearer ${externalApiKey}`;
            }

            const response = await fetch(externalEndpoint, {
                method: 'POST',
                headers,
                body: JSON.stringify(inputs)
            });
            const data = await response.json();

            const result = {
                id: Date.now().toString(),
                outputs: data.predictions || data.outputs || data,
                inputs: { ...inputs },
                latency_ms: Date.now() - startTime,
                timestamp: new Date().toISOString(),
                source: 'external'
            };

            setPredictions([result]);
            setHistory(prev => [result, ...prev].slice(0, 50));
        } catch (err) {
            console.error('External prediction failed:', err);
            setError(`External API call failed: ${err.message}`);
        } finally {
            setPredicting(false);
        }
    };

    const runSweep = async () => {
        if (selectedModels.length === 0 || !sweepParam) return;
        setSweeping(true);
        setError(null);

        try {
            const sweepValues = [];
            const step = (sweepMax - sweepMin) / (sweepSteps - 1);
            for (let i = 0; i < sweepSteps; i++) {
                sweepValues.push(sweepMin + step * i);
            }

            const response = await fetch('/api/explorer/sweep', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    deployment_id: selectedModels[0].id,
                    base_inputs: inputs,
                    sweep_param: sweepParam,
                    sweep_values: sweepValues
                })
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Sweep failed');
            }

            setSweepResults(result);
        } catch (err) {
            console.error('Sweep failed:', err);
            setError(`Parameter sweep failed: ${err.message}`);
        } finally {
            setSweeping(false);
        }
    };

    const updateInput = (name, value) => {
        setInputs(prev => ({ ...prev, [name]: value }));
    };

    const copyInputs = () => {
        navigator.clipboard.writeText(JSON.stringify(inputs, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const loadFromHistory = (item) => {
        setInputs(item.inputs);
        setPredictions([item]);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-violet-500 mx-auto mb-4" />
                    <p className="text-slate-500">Loading Model Explorer...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 h-[calc(100vh-20px)] overflow-hidden flex flex-col max-w-full mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl text-white shadow-lg shadow-violet-500/20">
                        <Microscope size={28} />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Model Explorer</h1>
                        <p className="text-slate-500 dark:text-slate-400 mt-1">
                            Test, compare, and analyze ML models interactively
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                        <button
                            onClick={() => { setViewMode('single'); setSelectedModels(selectedModels.slice(0, 1)); }}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${viewMode === 'single'
                                ? 'bg-white dark:bg-slate-700 text-violet-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            <Target size={14} />
                            Single
                        </button>
                        <button
                            onClick={() => setViewMode('compare')}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${viewMode === 'compare'
                                ? 'bg-white dark:bg-slate-700 text-violet-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            <GitCompare size={14} />
                            Compare
                        </button>
                    </div>

                    <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                        <button
                            onClick={() => { setConnectionMode('internal'); setShowExternalConfig(false); }}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${connectionMode === 'internal'
                                ? 'bg-white dark:bg-slate-700 text-emerald-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            <Zap size={14} />
                            FlowyML
                        </button>
                        <button
                            onClick={() => { setConnectionMode('external'); setShowExternalConfig(true); }}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${connectionMode === 'external'
                                ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            <Globe size={14} />
                            External
                        </button>
                    </div>

                    <Button onClick={fetchDeployments} variant="ghost" className="flex items-center gap-2">
                        <RefreshCw size={16} />
                        Refresh
                    </Button>
                </div>
            </div>

            {/* Error Banner */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-4"
                    >
                        <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-4 flex items-center gap-3">
                            <AlertCircle className="text-rose-500" size={20} />
                            <p className="text-rose-700 dark:text-rose-400 text-sm flex-1">{error}</p>
                            <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700">×</button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* External API Config */}
            <AnimatePresence>
                {showExternalConfig && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-6 shrink-0"
                    >
                        <Card className="bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border-violet-200 dark:border-violet-800">
                            {/* ... external config content reused ... */}
                            <div className="flex items-center gap-2 mb-4">
                                <Globe size={18} className="text-violet-500" />
                                <h3 className="font-semibold text-slate-900 dark:text-white">External API Connection</h3>
                                {externalConnected && <Badge className="bg-emerald-100 text-emerald-700 ml-2">Connected</Badge>}
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="md:col-span-2">
                                    <label className="text-xs font-medium text-slate-500 mb-1 block">Endpoint URL</label>
                                    <input type="url" value={externalEndpoint} onChange={(e) => setExternalEndpoint(e.target.value)} placeholder="https://api.example.com/v1/predict" className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-800" />
                                </div>
                                <div>
                                    <label className="text-xs font-medium text-slate-500 mb-1 block">API Key (optional)</label>
                                    <input type="password" value={externalApiKey} onChange={(e) => setExternalApiKey(e.target.value)} placeholder="Bearer token..." className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-800" />
                                </div>
                            </div>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Layout Grid */}
            <div className="grid grid-cols-12 gap-6 flex-1 min-h-0">

                {/* LEFT SIDEBAR - CONFIGURATION */}
                <div className="col-span-3 h-full border-r border-slate-200/50 dark:border-slate-700/50 bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl flex flex-col shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-20">
                    <div className="p-4 flex-1 overflow-y-auto space-y-6 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
                        {/* Model Selection */}
                        <div className="space-y-3">
                            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2 px-1">
                                <Layers size={12} />
                                Model Selection
                            </h3>
                            {deployments.length === 0 ? (
                                <div className="text-center py-8 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-xs">
                                    No active deployments
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {deployments.map(d => {
                                        const isSelected = selectedModels.find(m => m.id === d.id);
                                        return (
                                            <button
                                                key={d.id}
                                                onClick={() => selectModel(d, viewMode === 'compare')}
                                                className={`w-full text-left p-3 rounded-xl border transition-all duration-200 group relative overflow-hidden ${isSelected
                                                    ? 'border-violet-500/50 bg-gradient-to-r from-violet-500/10 to-indigo-500/10 shadow-sm'
                                                    : 'border-transparent hover:bg-white/50 dark:hover:bg-slate-800/50 hover:border-slate-200 dark:hover:border-slate-700'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between relative z-10">
                                                    <div className={`font-medium text-sm transition-colors ${isSelected ? 'text-violet-700 dark:text-violet-300' : 'text-slate-600 dark:text-slate-300'}`}>
                                                        {d.name}
                                                    </div>
                                                    {isSelected && (
                                                        <motion.div layoutId="check" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                                                            <div className="bg-violet-500 text-white p-0.5 rounded-full">
                                                                <Check size={10} strokeWidth={3} />
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </div>
                                                <div className="text-[10px] text-slate-400 mt-1 pl-0.5">{d.id}</div>
                                                {isSelected && <div className="absolute left-0 top-0 bottom-0 w-1 bg-violet-500" />}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Inputs */}
                        <div className="space-y-3 pt-6 border-t border-slate-200/50 dark:border-slate-700/50">
                            <div className="flex items-center justify-between px-1">
                                <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                    <Sliders size={12} />
                                    Parameters
                                </h3>
                                <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 border border-slate-200 dark:border-slate-700">
                                    <button onClick={() => setInputMode('form')} className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition-all ${inputMode === 'form' ? 'bg-white shadow-sm text-violet-600' : 'text-slate-400 hover:text-slate-600'}`}>Form</button>
                                    <button onClick={() => setInputMode('json')} className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition-all ${inputMode === 'json' ? 'bg-white shadow-sm text-violet-600' : 'text-slate-400 hover:text-slate-600'}`}>JSON</button>
                                </div>
                            </div>

                            <div className="min-h-[200px]">
                                {inputMode === 'json' ? (
                                    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                                        <JsonEditor value={inputs} onChange={setInputs} />
                                    </div>
                                ) : (
                                    <div className="space-y-4 px-1">
                                        {schema?.inputs?.map(field => (
                                            <div key={field.name} className="group">
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 group-hover:text-violet-600 transition-colors">{field.name}</label>
                                                    <span className="text-[10px] text-slate-400 font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700">{formatValue(inputs[field.name])?.slice(0, 10)}</span>
                                                </div>
                                                {field.type === 'number' || field.type === 'integer' ? (
                                                    <div className="relative flex items-center">
                                                        <input
                                                            type="range"
                                                            min={field.min_value || 0}
                                                            max={field.max_value || 100}
                                                            step={field.step || (field.type === 'integer' ? 1 : 0.1)}
                                                            value={inputs[field.name] || 0}
                                                            onChange={(e) => updateInput(field.name, parseFloat(e.target.value))}
                                                            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500 hover:accent-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                                                        />
                                                    </div>
                                                ) : field.type === 'boolean' ? (
                                                    <div className="flex gap-2">
                                                        <button onClick={() => updateInput(field.name, true)} className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-all ${inputs[field.name] ? 'bg-violet-500 border-violet-600 text-white shadow-md shadow-violet-500/20' : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'}`}>True</button>
                                                        <button onClick={() => updateInput(field.name, false)} className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-all ${!inputs[field.name] ? 'bg-slate-700 border-slate-800 text-white shadow-md' : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'}`}>False</button>
                                                    </div>
                                                ) : (
                                                    <input
                                                        type="text"
                                                        value={inputs[field.name] || ''}
                                                        onChange={(e) => updateInput(field.name, e.target.value)}
                                                        className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm bg-white dark:bg-slate-800 focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all placeholder:text-slate-300"
                                                        placeholder={`Enter ${field.name}...`}
                                                    />
                                                )}
                                            </div>
                                        )) || <div className="text-sm text-slate-400 text-center py-10 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">Select a model to configure inputs</div>}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="p-4 border-t border-slate-200/60 dark:border-slate-700/60 bg-white/50 dark:bg-slate-900/50 backdrop-blur-md">
                        <Button
                            onClick={connectionMode === 'external' ? runExternalPrediction : runPrediction}
                            disabled={predicting || selectedModels.length === 0}
                            className={`w-full py-6 text-sm font-bold tracking-wide shadow-xl shadow-violet-500/20 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl transition-all active:scale-[0.98] ${predicting ? 'opacity-80' : ''}`}
                        >
                            {predicting ? <Loader2 className="animate-spin mr-2" /> : <Play className="mr-2 fill-current" size={18} />}
                            {predicting ? 'RUNNING...' : 'RUN PREDICTION'}
                        </Button>
                    </div>
                </div>

                {/* RIGHT MAIN - TABS & CONTENT */}
                <div className="col-span-9 flex flex-col h-full overflow-hidden bg-white/30 dark:bg-slate-900/30 backdrop-blur-sm relative">
                    {/* Fluid Mesh Background for Main Content */}
                    <div className="absolute inset-0 bg-gradient-to-br from-white/40 via-transparent to-white/40 pointer-events-none" />

                    {/* Tab Header */}
                    <div className="flex items-center gap-6 border-b border-slate-200/60 dark:border-slate-700/60 px-8 bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl sticky top-0 z-10 h-16 shrink-0">
                        {[
                            { id: 'results', icon: Sparkles, label: 'Results' },
                            { id: 'history', icon: History, label: 'History' },
                            { id: 'logs', icon: Terminal, label: 'Live Logs' },
                            { id: 'info', icon: Info, label: 'Model Specs' }
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`relative h-full flex items-center gap-2.5 text-sm font-medium transition-colors ${activeTab === tab.id
                                    ? 'text-violet-700 dark:text-violet-400'
                                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                                    }`}
                            >
                                <tab.icon size={16} className={activeTab === tab.id ? 'stroke-[2.5px]' : ''} />
                                {tab.label}
                                {tab.id === 'history' && history.length > 0 && (
                                    <span className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full border border-slate-200 dark:border-slate-700">{history.length}</span>
                                )}
                                {activeTab === tab.id && (
                                    <motion.div
                                        layoutId="activeTabIndicator"
                                        className="absolute bottom-0 left-0 right-0 h-[3px] bg-gradient-to-r from-violet-500 to-indigo-500 rounded-t-full shadow-[0_-4px_12px_rgba(139,92,246,0.5)]"
                                    />
                                )}
                            </button>
                        ))}
                    </div>


                    {/* Content Area */}
                    <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30 dark:bg-slate-900/10 relative">
                        {activeTab === 'results' && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                                {/* Result Cards */}
                                {predictions.length > 0 ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {/* Main Result */}
                                        <Card className="md:col-span-2 bg-gradient-to-br from-violet-600 to-purple-700 text-white border-none shadow-xl shadow-violet-500/20">
                                            <div className="text-violet-200 text-xs font-bold uppercase tracking-wider mb-2">Primary Prediction</div>
                                            <div className="text-5xl font-bold font-mono tracking-tight mb-4">
                                                {formatValue(predictions[0]?.outputs?.prediction || Object.values(predictions[0]?.outputs || {})[0])}
                                            </div>
                                            <div className="flex gap-4 text-violet-200 text-sm">
                                                <span className="flex items-center gap-1"><Activity size={14} /> {predictions[0]?.latency_ms?.toFixed(1)}ms</span>
                                                <span className="flex items-center gap-1"><Layers size={14} /> {predictions[0]?.model_name || 'Unknown Model'}</span>
                                            </div>
                                        </Card>

                                        {/* Secondary Metrics / Raw Output */}
                                        {Object.entries(predictions[0]?.outputs || {}).filter(([k]) => k !== 'prediction').map(([key, value]) => (
                                            <Card key={key} className="bg-white dark:bg-slate-800">
                                                <div className="text-xs text-slate-500 uppercase font-bold mb-1">{key}</div>
                                                <div className="text-lg font-mono text-slate-800 dark:text-slate-200 truncate" title={formatValue(value)}>
                                                    {formatValue(value)}
                                                </div>
                                            </Card>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-20 opacity-50">
                                        <Sparkles size={48} className="mx-auto mb-4 text-slate-300" />
                                        <h3 className="text-lg font-medium text-slate-500">Ready to Predict</h3>
                                        <p className="text-sm text-slate-400">Select a model and run a prediction to see results</p>
                                    </div>
                                )}

                                {/* Sensitivity Analysis (Moved here) */}
                                {selectedModels.length > 0 && schema && (
                                    <div className="mt-8 border-t border-slate-200 pt-6">
                                        <h4 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                                            <TrendingUp size={16} className="text-violet-500" />
                                            Sensitivity Analysis
                                        </h4>
                                        <div className="flex gap-4 items-end bg-white p-4 rounded-xl border border-slate-200">
                                            <div className="flex-1">
                                                <label className="text-xs text-slate-500 font-bold mb-1 block">Parameter to Sweep</label>
                                                <select
                                                    value={sweepParam}
                                                    onChange={(e) => setSweepParam(e.target.value)}
                                                    className="w-full px-3 py-2 border rounded-lg text-sm bg-slate-50"
                                                >
                                                    {schema.inputs?.filter(f => f.type === 'number' || f.type === 'integer').map(f => (
                                                        <option key={f.name} value={f.name}>{f.name}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <Button onClick={runSweep} disabled={sweeping} variant="outline" className="mb-0.5">
                                                {sweeping ? <Loader2 className="animate-spin" /> : <Play size={14} className="mr-2" />}
                                                Run Sweep
                                            </Button>
                                        </div>
                                        {sweepResults && (
                                            <div className="mt-4">
                                                <PredictionChart
                                                    data={sweepResults.results?.map((r, i) => ({
                                                        value: r.outputs?.prediction || 0,
                                                        label: r.input_value?.toFixed(1)
                                                    })) || []}
                                                    title={`${sweepParam} Sensitivity`}
                                                />
                                            </div>
                                        )}
                                    </div>
                                )}
                            </motion.div>
                        )}

                        {activeTab === 'history' && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                                {history.map((h, i) => (
                                    <div key={i} onClick={() => loadFromHistory(h)} className="flex items-center justify-between p-4 bg-white border border-slate-100 rounded-xl hover:shadow-md cursor-pointer transition-all group">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-full bg-violet-100 text-violet-600 flex items-center justify-center font-bold text-xs">
                                                #{history.length - i}
                                            </div>
                                            <div>
                                                <div className="font-mono font-bold text-slate-800">{formatValue(h?.outputs?.prediction)}</div>
                                                <div className="text-xs text-slate-500">{new Date(h.timestamp).toLocaleString()}</div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-xs font-bold text-slate-600">{h.latency_ms?.toFixed(0)}ms</div>
                                            <div className="text-[10px] text-slate-400 group-hover:text-violet-500">Restore Inputs</div>
                                        </div>
                                    </div>
                                ))}
                                {history.length === 0 && <div className="text-center py-10 text-slate-400">No history yet</div>}
                            </motion.div>
                        )}

                        {activeTab === 'logs' && selectedModels.length > 0 && (
                            <LogsPanel logs={logs} deploymentId={selectedModels[0]?.id} onClose={() => { }} />
                        )}

                        {activeTab === 'info' && modelInfo && (
                            <ModelInfoPanel modelInfo={modelInfo} onClose={() => { }} />
                        )}

                        {(activeTab === 'logs' || activeTab === 'info') && !selectedModels.length && (
                            <div className="text-center py-20 text-slate-400">Select a deployment to view {activeTab}</div>
                        )}
                    </div>
                </div>
            </div>
            {/* Footer */}
            <div className="text-center mt-2 shrink-0">
                <p className="text-[10px] text-slate-400 dark:text-slate-500">
                    Made with ❤️ by <span className="font-medium text-violet-500">UnicoLab</span>
                </p>
            </div>
        </div>
    );

}
