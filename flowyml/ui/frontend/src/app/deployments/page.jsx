import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import { useSearchParams } from 'react-router-dom';
import {
    Rocket,
    Plus,
    Play,
    Square,
    Trash2,
    RefreshCw,
    Copy,
    ExternalLink,
    Terminal,
    Shield,
    Clock,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Settings,
    ChevronDown,
    ChevronUp,
    Eye,
    EyeOff,
    X,
    Package,
    Download
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export function DeploymentLab() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [deployments, setDeployments] = useState([]);
    const [availableModels, setAvailableModels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedDeployment, setSelectedDeployment] = useState(null);
    const [visibleTokens, setVisibleTokens] = useState(new Set());
    const [modelSearch, setModelSearch] = useState('');
    const [showModelDropdown, setShowModelDropdown] = useState(false);
    const [deploymentLogs, setDeploymentLogs] = useState([]);
    const [logsLoading, setLogsLoading] = useState(false);
    const [deleteConfirmId, setDeleteConfirmId] = useState(null);

    // Dependency installation state
    const [showDependencies, setShowDependencies] = useState(false);
    const [installedDeps, setInstalledDeps] = useState({});
    const [installingDeps, setInstallingDeps] = useState(new Set());

    // Form state
    const [newDeployment, setNewDeployment] = useState({
        name: '',
        model_artifact_id: '',
        model_version: null,
        port: null,
        config: {
            rate_limit: 100,
            timeout_seconds: 30,
            max_batch_size: 1,
            enable_cors: true,
            ttl_seconds: null  // Auto-destroy after N seconds (null = never)
        }
    });

    useEffect(() => {
        fetchDeployments();
        fetchAvailableModels();

        // Auto-refresh deployment status every 5 seconds for status updates and TTL countdown
        const refreshInterval = setInterval(() => {
            fetchDeployments();
        }, 5000);

        return () => clearInterval(refreshInterval);
    }, []);

    // Handle URL parameters for deploy action from Assets page
    useEffect(() => {
        const deployId = searchParams.get('deploy');
        const modelName = searchParams.get('name');

        if (deployId) {
            // Pre-populate form with model info
            setNewDeployment(prev => ({
                ...prev,
                model_artifact_id: deployId,
                name: modelName ? `${modelName}-api` : ''
            }));
            setShowCreateModal(true);
            // Clear the URL params
            setSearchParams({});
        }
    }, [searchParams, setSearchParams]);

    const fetchDeployments = async () => {
        try {
            const response = await fetchApi('/api/deployments/');
            const data = await response.json();
            setDeployments(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Failed to fetch deployments:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchAvailableModels = async () => {
        try {
            const response = await fetchApi('/api/deployments/available-models');
            const data = await response.json();
            setAvailableModels(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Failed to fetch models:', error);
        }
    };

    const fetchDependencyStatus = async () => {
        try {
            const response = await fetchApi('/api/deployments/dependencies/status');
            const data = await response.json();
            setInstalledDeps(data.installed || {});
        } catch (error) {
            console.error('Failed to fetch dependency status:', error);
        }
    };

    const installDependency = async (framework) => {
        setInstallingDeps(prev => new Set([...prev, framework]));
        try {
            const response = await fetchApi('/api/deployments/dependencies/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frameworks: [framework] })
            });
            if (response.ok) {
                // Wait a bit for installation to start, then refresh status
                setTimeout(() => {
                    fetchDependencyStatus();
                    setInstallingDeps(prev => {
                        const next = new Set(prev);
                        next.delete(framework);
                        return next;
                    });
                }, 3000);
            }
        } catch (error) {
            console.error('Failed to install dependency:', error);
            setInstallingDeps(prev => {
                const next = new Set(prev);
                next.delete(framework);
                return next;
            });
        }
    };

    const createDeployment = async (e) => {
        e.preventDefault();
        try {
            const response = await fetchApi('/api/deployments/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newDeployment)
            });
            if (response.ok) {
                setShowCreateModal(false);
                setNewDeployment({
                    name: '',
                    model_artifact_id: '',
                    model_version: null,
                    port: null,
                    config: { rate_limit: 100, timeout_seconds: 30, max_batch_size: 1, enable_cors: true, ttl_seconds: null }
                });
                fetchDeployments();
            }
        } catch (error) {
            console.error('Failed to create deployment:', error);
        }
    };

    const toggleDeployment = async (id, action) => {
        try {
            await fetchApi(`/api/deployments/${id}/${action}`, { method: 'POST' });
            fetchDeployments();
        } catch (error) {
            console.error(`Failed to ${action} deployment:`, error);
        }
    };

    const deleteDeployment = async (id) => {
        try {
            await fetchApi(`/api/deployments/${id}`, { method: 'DELETE' });
            setDeleteConfirmId(null);
            fetchDeployments();
        } catch (error) {
            console.error('Failed to delete deployment:', error);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    const toggleTokenVisibility = (id) => {
        setVisibleTokens(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) newSet.delete(id);
            else newSet.add(id);
            return newSet;
        });
    };

    const maskToken = (token) => {
        if (!token) return '••••••••••••••••';
        return `${token.substring(0, 8)}••••••••${token.substring(token.length - 4)}`;
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'running': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400';
            case 'pending':
            case 'starting': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400';
            case 'stopped': return 'bg-slate-100 text-slate-700 dark:bg-slate-900/20 dark:text-slate-400';
            case 'error': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400';
            default: return 'bg-slate-100 text-slate-700';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'running': return <CheckCircle2 size={14} />;
            case 'pending':
            case 'starting': return <Loader2 size={14} className="animate-spin" />;
            case 'stopped': return <Square size={14} />;
            case 'error': return <AlertCircle size={14} />;
            default: return <Clock size={14} />;
        }
    };

    // Fetch deployment logs
    const fetchDeploymentLogs = async (deployment) => {
        setSelectedDeployment(deployment);
        setLogsLoading(true);
        try {
            const response = await fetchApi(`/api/deployments/${deployment.id}/logs`);
            if (response.ok) {
                const data = await response.json();
                setDeploymentLogs(data.logs || []);
            }
        } catch (error) {
            console.error('Failed to fetch logs:', error);
            setDeploymentLogs([{ timestamp: new Date().toISOString(), level: 'ERROR', message: 'Failed to fetch logs' }]);
        } finally {
            setLogsLoading(false);
        }
    };

    // Calculate TTL countdown
    const getTimeRemaining = (expiresAt) => {
        if (!expiresAt) return null;
        const diff = new Date(expiresAt) - new Date();
        if (diff <= 0) return 'Expired';
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            return `${hours}h ${minutes % 60}m`;
        }
        return `${minutes}m ${seconds}s`;
    };


    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="w-12 h-12 animate-spin text-primary-600" />
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-orange-500 to-red-500 rounded-xl text-white">
                            <Rocket size={28} />
                        </div>
                        Deployment Lab
                        <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-xs font-medium">
                            Experimental
                        </Badge>
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Deploy models as API endpoints (TFServing for Keras models coming soon)
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button
                        onClick={() => {
                            setShowDependencies(!showDependencies);
                            if (!showDependencies) fetchDependencyStatus();
                        }}
                        variant="ghost"
                        className="flex items-center gap-2"
                    >
                        <Package size={16} />
                        Dependencies
                    </Button>
                    <Button
                        onClick={fetchDeployments}
                        variant="ghost"
                        className="flex items-center gap-2"
                    >
                        <RefreshCw size={16} />
                        Refresh
                    </Button>
                    <Button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center gap-2 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                    >
                        <Plus size={16} />
                        New Deployment
                    </Button>
                </div>
            </div>

            {/* ML Dependencies Panel */}
            {showDependencies && (
                <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
                    <div className="p-4">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Package className="text-blue-500" size={20} />
                                <h3 className="font-semibold text-slate-900 dark:text-white">ML Framework Dependencies</h3>
                            </div>
                            <Button variant="ghost" size="sm" onClick={fetchDependencyStatus}>
                                <RefreshCw size={14} />
                            </Button>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                            Install ML frameworks on the server to enable model predictions
                        </p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {['keras', 'tensorflow', 'pytorch', 'sklearn', 'xgboost', 'onnx'].map(framework => (
                                <div key={framework} className="flex items-center justify-between p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
                                    <span className="font-medium capitalize">{framework}</span>
                                    {installedDeps[framework] ? (
                                        <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                                            <CheckCircle2 size={12} className="mr-1" />
                                            Installed
                                        </Badge>
                                    ) : installingDeps.has(framework) ? (
                                        <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                            <Loader2 size={12} className="mr-1 animate-spin" />
                                            Installing...
                                        </Badge>
                                    ) : (
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => installDependency(framework)}
                                            className="text-blue-600 hover:bg-blue-50"
                                        >
                                            <Download size={14} className="mr-1" />
                                            Install
                                        </Button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </Card>
            )}

            {/* Deployments Grid */}
            {deployments.length === 0 ? (
                <Card className="text-center py-16 bg-slate-50 dark:bg-slate-800/30">
                    <div className="mx-auto w-20 h-20 bg-gradient-to-br from-orange-100 to-red-100 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl flex items-center justify-center mb-6">
                        <Rocket className="text-orange-500" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No Deployments Yet</h3>
                    <p className="text-slate-500 max-w-md mx-auto mb-6">
                        Deploy your first model as an API endpoint to start testing predictions
                    </p>
                    <Button
                        onClick={() => setShowCreateModal(true)}
                        className="bg-gradient-to-r from-orange-500 to-red-500"
                    >
                        <Plus size={16} className="mr-2" />
                        Create Your First Deployment
                    </Button>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2">
                    {deployments.map((deployment) => (
                        <Card key={deployment.id} className="hover:shadow-lg transition-all duration-200">
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg ${deployment.status === 'running' ? 'bg-emerald-100 dark:bg-emerald-900/20' : 'bg-slate-100 dark:bg-slate-800'}`}>
                                        <Rocket className={deployment.status === 'running' ? 'text-emerald-600' : 'text-slate-500'} size={20} />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-900 dark:text-white">{deployment.name}</h3>
                                        <p className="text-xs text-slate-500">ID: {deployment.id.substring(0, 8)}...</p>
                                    </div>
                                </div>
                                <Badge className={getStatusColor(deployment.status)}>
                                    <span className="flex items-center gap-1">
                                        {getStatusIcon(deployment.status)}
                                        {deployment.status}
                                    </span>
                                </Badge>
                            </div>

                            {/* Endpoint URL */}
                            <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3 mb-4">
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-medium text-slate-500">Endpoint</span>
                                    <button
                                        onClick={() => copyToClipboard(deployment.endpoint_url + '/predict')}
                                        className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                                    >
                                        <Copy size={12} className="text-slate-500" />
                                    </button>
                                </div>
                                <code className="text-sm text-primary-600 dark:text-primary-400">
                                    {deployment.endpoint_url}/predict
                                </code>
                            </div>

                            {/* API Token */}
                            <div className="bg-amber-50 dark:bg-amber-900/10 rounded-lg p-3 mb-4 border border-amber-200 dark:border-amber-800">
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-medium text-amber-700 dark:text-amber-400 flex items-center gap-1">
                                        <Shield size={12} />
                                        API Token
                                    </span>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => toggleTokenVisibility(deployment.id)}
                                            className="p-1 hover:bg-amber-200 dark:hover:bg-amber-800 rounded"
                                        >
                                            {visibleTokens.has(deployment.id) ? <EyeOff size={12} /> : <Eye size={12} />}
                                        </button>
                                        <button
                                            onClick={() => copyToClipboard(deployment.api_token)}
                                            className="p-1 hover:bg-amber-200 dark:hover:bg-amber-800 rounded"
                                        >
                                            <Copy size={12} />
                                        </button>
                                    </div>
                                </div>
                                <code className="text-xs text-amber-800 dark:text-amber-300 font-mono">
                                    {visibleTokens.has(deployment.id) ? deployment.api_token : maskToken(deployment.api_token)}
                                </code>
                            </div>

                            {/* TTL Countdown & Health Status */}
                            {(deployment.expires_at || deployment.status === 'running') && (
                                <div className="flex items-center gap-3 mb-4">
                                    {deployment.expires_at && (
                                        <div className="flex items-center gap-1.5 px-2 py-1 bg-purple-100 dark:bg-purple-900/20 rounded text-xs">
                                            <Clock size={12} className="text-purple-600" />
                                            <span className="font-medium text-purple-700 dark:text-purple-400">
                                                TTL: {getTimeRemaining(deployment.expires_at)}
                                            </span>
                                        </div>
                                    )}
                                    {deployment.status === 'running' && (
                                        <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-100 dark:bg-emerald-900/20 rounded text-xs">
                                            <CheckCircle2 size={12} className="text-emerald-600" />
                                            <span className="font-medium text-emerald-700 dark:text-emerald-400">Healthy</span>
                                        </div>
                                    )}
                                    {deployment.status === 'error' && deployment.error_message && (
                                        <div className="flex items-center gap-1.5 px-2 py-1 bg-rose-100 dark:bg-rose-900/20 rounded text-xs flex-1">
                                            <AlertCircle size={12} className="text-rose-600" />
                                            <span className="font-medium text-rose-700 dark:text-rose-400 truncate">{deployment.error_message}</span>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex gap-2">
                                {deployment.status === 'running' ? (
                                    <Button
                                        onClick={() => toggleDeployment(deployment.id, 'stop')}
                                        variant="ghost"
                                        className="flex-1 text-amber-600 hover:bg-amber-50"
                                    >
                                        <Square size={14} className="mr-1" />
                                        Stop
                                    </Button>
                                ) : deployment.status === 'stopped' ? (
                                    <Button
                                        onClick={() => toggleDeployment(deployment.id, 'start')}
                                        variant="ghost"
                                        className="flex-1 text-emerald-600 hover:bg-emerald-50"
                                    >
                                        <Play size={14} className="mr-1" />
                                        Start
                                    </Button>
                                ) : null}
                                <Button
                                    onClick={() => fetchDeploymentLogs(deployment)}
                                    variant="ghost"
                                    className="flex-1"
                                >
                                    <Terminal size={14} className="mr-1" />
                                    Logs
                                </Button>
                                <Button
                                    onClick={() => setDeleteConfirmId(deployment.id)}
                                    variant="ghost"
                                    className="text-rose-600 hover:bg-rose-50"
                                >
                                    <Trash2 size={14} />
                                </Button>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            {/* Create Deployment Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="max-w-lg w-full max-h-[90vh] overflow-y-auto">
                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
                            <Rocket className="text-orange-500" size={24} />
                            New Deployment
                        </h2>

                        <form onSubmit={createDeployment} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                    Deployment Name
                                </label>
                                <input
                                    type="text"
                                    value={newDeployment.name}
                                    onChange={(e) => setNewDeployment({ ...newDeployment, name: e.target.value })}
                                    placeholder="e.g., My Model API"
                                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-orange-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                    Model {availableModels.length > 0 && <span className="text-slate-400">({availableModels.length} available)</span>}
                                </label>
                                {/* Searchable model selector */}
                                <div className="relative">
                                    <input
                                        type="text"
                                        placeholder="Search models..."
                                        value={modelSearch}
                                        onChange={(e) => setModelSearch(e.target.value)}
                                        onFocus={() => setShowModelDropdown(true)}
                                        className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-orange-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    />
                                    {newDeployment.model_artifact_id && (
                                        <div className="mt-1 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 rounded text-sm text-orange-700 dark:text-orange-300 flex items-center justify-between">
                                            <span>Selected: {availableModels.find(m => m.artifact_id === newDeployment.model_artifact_id)?.name || newDeployment.model_artifact_id}</span>
                                            <button type="button" onClick={() => setNewDeployment({ ...newDeployment, model_artifact_id: '' })} className="text-orange-500 hover:text-orange-700">×</button>
                                        </div>
                                    )}
                                    {showModelDropdown && (
                                        <div className="absolute z-50 w-full mt-1 max-h-60 overflow-y-auto bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg shadow-lg">
                                            {availableModels
                                                .filter(m =>
                                                    m.name?.toLowerCase().includes(modelSearch.toLowerCase()) ||
                                                    m.type?.toLowerCase().includes(modelSearch.toLowerCase()) ||
                                                    m.project?.toLowerCase().includes(modelSearch.toLowerCase())
                                                )
                                                .slice(0, 20)
                                                .map((model) => (
                                                    <button
                                                        key={model.artifact_id}
                                                        type="button"
                                                        onClick={() => {
                                                            setNewDeployment({ ...newDeployment, model_artifact_id: model.artifact_id });
                                                            setModelSearch('');
                                                            setShowModelDropdown(false);
                                                        }}
                                                        className="w-full text-left px-4 py-2 hover:bg-slate-100 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700 last:border-0"
                                                    >
                                                        <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                                                            {model.name}
                                                            {model.file_exists ? (
                                                                <span className="px-1 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded">Ready</span>
                                                            ) : model.has_file ? (
                                                                <span className="px-1 py-0.5 text-xs bg-amber-100 text-amber-700 rounded">Missing</span>
                                                            ) : (
                                                                <span className="px-1 py-0.5 text-xs bg-rose-100 text-rose-700 rounded">No File</span>
                                                            )}
                                                        </div>
                                                        <div className="text-xs text-slate-500 flex gap-2">
                                                            <span className="px-1 bg-slate-200 dark:bg-slate-600 rounded">{model.type}</span>
                                                            {model.project && <span>{model.project}</span>}
                                                        </div>
                                                    </button>
                                                ))}
                                            {availableModels.filter(m => m.name?.toLowerCase().includes(modelSearch.toLowerCase())).length === 0 && (
                                                <div className="px-4 py-3 text-slate-500 text-center">No models found</div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {availableModels.length === 0 && (
                                    <p className="text-xs text-slate-500 mt-1">
                                        No models available. Train a model first!
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                    Port (optional)
                                </label>
                                <input
                                    type="number"
                                    value={newDeployment.port || ''}
                                    onChange={(e) => setNewDeployment({ ...newDeployment, port: e.target.value ? parseInt(e.target.value) : null })}
                                    placeholder="Auto-assigned if empty"
                                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-orange-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                    Auto-Destroy (TTL)
                                </label>
                                <select
                                    value={newDeployment.config.ttl_seconds || ''}
                                    onChange={(e) => setNewDeployment({
                                        ...newDeployment,
                                        config: {
                                            ...newDeployment.config,
                                            ttl_seconds: e.target.value ? parseInt(e.target.value) : null
                                        }
                                    })}
                                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-orange-500 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                >
                                    <option value="">Never (keep running)</option>
                                    <option value="300">5 minutes</option>
                                    <option value="900">15 minutes</option>
                                    <option value="1800">30 minutes</option>
                                    <option value="3600">1 hour</option>
                                    <option value="7200">2 hours</option>
                                </select>
                                <p className="text-xs text-slate-500 mt-1">
                                    Automatically stop deployment after selected time
                                </p>
                            </div>

                            <div className="pt-4 flex gap-3 justify-end">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => setShowCreateModal(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    className="bg-gradient-to-r from-orange-500 to-red-500"
                                >
                                    <Rocket size={16} className="mr-2" />
                                    Deploy
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            )}

            {/* Logs Modal */}
            {selectedDeployment && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="max-w-2xl w-full max-h-[80vh] flex flex-col">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <Terminal className="text-orange-500" size={20} />
                                Logs: {selectedDeployment.name}
                            </h2>
                            <div className="flex items-center gap-2">
                                <Badge className={getStatusColor(selectedDeployment.status)}>
                                    {selectedDeployment.status}
                                </Badge>
                                <button
                                    onClick={() => { setSelectedDeployment(null); setDeploymentLogs([]); }}
                                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                                >
                                    <X size={20} />
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto bg-slate-900 rounded-lg p-4 font-mono text-sm">
                            {logsLoading ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="animate-spin text-slate-400" size={24} />
                                </div>
                            ) : deploymentLogs.length === 0 ? (
                                <div className="text-slate-500 text-center py-8">No logs available</div>
                            ) : (
                                deploymentLogs.map((log, index) => (
                                    <div key={index} className="mb-1 flex gap-2">
                                        <span className="text-slate-500 shrink-0">
                                            {new Date(log.timestamp).toLocaleTimeString()}
                                        </span>
                                        <span className={`shrink-0 px-1 rounded text-xs font-bold ${log.level === 'ERROR' ? 'bg-rose-900 text-rose-400' :
                                            log.level === 'WARN' ? 'bg-amber-900 text-amber-400' :
                                                'bg-emerald-900 text-emerald-400'
                                            }`}>
                                            {log.level}
                                        </span>
                                        <span className="text-slate-300">{log.message}</span>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="mt-4 flex justify-between">
                            <Button
                                onClick={() => fetchDeploymentLogs(selectedDeployment)}
                                variant="ghost"
                                className="flex items-center gap-2"
                            >
                                <RefreshCw size={14} />
                                Refresh Logs
                            </Button>
                            <Button
                                onClick={() => { setSelectedDeployment(null); setDeploymentLogs([]); }}
                                variant="ghost"
                            >
                                Close
                            </Button>
                        </div>
                    </Card>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deleteConfirmId && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="max-w-sm w-full">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <AlertCircle className="text-rose-500" size={24} />
                            Delete Deployment
                        </h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-6">
                            Are you sure you want to delete this deployment? This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <Button
                                variant="ghost"
                                onClick={() => setDeleteConfirmId(null)}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={() => deleteDeployment(deleteConfirmId)}
                                className="bg-rose-500 hover:bg-rose-600 text-white"
                            >
                                <Trash2 size={14} className="mr-2" />
                                Delete
                            </Button>
                        </div>
                    </Card>
                </div>
            )}

            {/* Footer Branding */}
            <div className="text-center pt-8 pb-4 border-t border-slate-200 dark:border-slate-700">
                <p className="text-xs text-slate-400 dark:text-slate-500">
                    Made with ❤️ by <span className="font-medium text-primary-500">UnicoLab</span>
                </p>
            </div>
        </div>
    );
}
