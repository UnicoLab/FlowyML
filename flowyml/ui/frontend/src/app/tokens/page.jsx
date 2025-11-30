import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import {
    Key,
    Plus,
    Trash2,
    Copy,
    Check,
    Shield,
    Calendar,
    AlertCircle,
    Eye,
    PenTool,
    Zap,
    ShieldCheck
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

export function TokenManagement() {
    const [tokens, setTokens] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newToken, setNewToken] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchTokens();
    }, []);

    const fetchTokens = async () => {
        try {
            // First check if we have any tokens (for initial token creation)
            const res = await fetchApi('/api/execution/tokens');
            if (res.status === 401) {
                // No tokens exist yet
                setTokens([]);
                setLoading(false);
                return;
            }
            const data = await res.json();
            setTokens(data.tokens || []);
        } catch (err) {
            console.error('Failed to fetch tokens:', err);
            setError('Failed to load tokens');
        } finally {
            setLoading(false);
        }
    };

    const createInitialToken = async () => {
        try {
            const res = await fetchApi('/api/execution/tokens/init', {
                method: 'POST'
            });
            const data = await res.json();
            if (res.ok) {
                setNewToken(data.token);
                await fetchTokens();
            } else {
                setError(data.detail);
            }
        } catch (err) {
            setError('Failed to create initial token');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-6xl mx-auto">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-amber-600 to-orange-800 rounded-lg">
                        <Key className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">API Tokens</h2>
                </div>
                <p className="text-slate-500 dark:text-slate-400 mt-2">
                    Manage API tokens for authenticating CLI and SDK requests
                </p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-4 flex items-start gap-3">
                    <AlertCircle className="text-rose-600 shrink-0" size={20} />
                    <div>
                        <h4 className="font-medium text-rose-900 dark:text-rose-200">Error</h4>
                        <p className="text-sm text-rose-700 dark:text-rose-300 mt-1">{error}</p>
                    </div>
                </div>
            )}

            {/* New Token Display */}
            {newToken && <NewTokenDisplay token={newToken} onClose={() => setNewToken(null)} />}

            {/* No Tokens State */}
            {tokens.length === 0 && !newToken && (
                <Card>
                    <CardContent className="py-16 text-center">
                        <div className="mx-auto w-20 h-20 bg-amber-100 dark:bg-amber-900/30 rounded-2xl flex items-center justify-center mb-6">
                            <Key className="text-amber-600" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                            No API Tokens Yet
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400 max-w-md mx-auto mb-6">
                            Create your first admin token to start using the flowyml API
                        </p>
                        <Button onClick={createInitialToken} className="flex items-center gap-2 mx-auto">
                            <Plus size={18} />
                            Create Initial Token
                        </Button>
                    </CardContent>
                </Card>
            )}

            {/* Tokens List */}
            {tokens.length > 0 && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle>Active Tokens</CardTitle>
                            <Button onClick={() => setShowCreateModal(true)} variant="primary" className="flex items-center gap-2">
                                <Plus size={18} />
                                Create Token
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {tokens.map((token, idx) => (
                                <TokenItem key={idx} token={token} onRevoke={fetchTokens} />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Create Token Modal */}
            {showCreateModal && (
                <CreateTokenModal
                    onClose={() => setShowCreateModal(false)}
                    onCreate={(token) => {
                        setNewToken(token);
                        setShowCreateModal(false);
                        fetchTokens();
                    }}
                />
            )}
        </div>
    );
}

const PERMISSION_STYLES = {
    read: {
        label: 'Read',
        icon: Eye,
        className: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-800'
    },
    write: {
        label: 'Write',
        icon: PenTool,
        className: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800'
    },
    execute: {
        label: 'Execute',
        icon: Zap,
        className: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-800'
    },
    admin: {
        label: 'Admin',
        icon: ShieldCheck,
        className: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-200 dark:border-rose-800'
    }
};

function PermissionChip({ perm }) {
    const config = PERMISSION_STYLES[perm] || {
        label: perm,
        icon: Shield,
        className: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-100 dark:border-slate-700'
    };
    const Icon = config.icon;

    return (
        <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${config.className}`}
        >
            <Icon size={12} />
            {config.label}
        </span>
    );
}

function TokenItem({ token, onRevoke }) {
    const [showRevoke, setShowRevoke] = useState(false);

    const handleRevoke = async () => {
        try {
            // This would need to be implemented in the backend
            await fetch(`/ api / execution / tokens / ${token.name} `, {
                method: 'DELETE'
            });
            onRevoke();
        } catch (err) {
            console.error('Failed to revoke token:', err);
        }
    };

    return (
        <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-semibold text-slate-900 dark:text-white">{token.name}</h4>
                        {token.project && (
                            <Badge variant="secondary" className="text-xs">
                                {token.project}
                            </Badge>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-2 mb-3">
                        {token.permissions?.length ? (
                            token.permissions.map(perm => (
                                <PermissionChip key={perm} perm={perm} />
                            ))
                        ) : (
                            <span className="text-xs text-slate-400">No permissions assigned</span>
                        )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                        <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            Created: {format(new Date(token.created_at), 'MMM d, yyyy')}
                        </span>
                        {token.last_used && (
                            <span>Last used: {format(new Date(token.last_used), 'MMM d, yyyy')}</span>
                        )}
                    </div>
                </div>
                <button
                    onClick={() => setShowRevoke(true)}
                    className="p-2 hover:bg-rose-100 dark:hover:bg-rose-900/30 text-slate-400 hover:text-rose-600 rounded-lg transition-colors"
                >
                    <Trash2 size={16} />
                </button>
            </div>

            {/* Revoke Confirmation */}
            {showRevoke && (
                <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                        Are you sure you want to revoke this token? This action cannot be undone.
                    </p>
                    <div className="flex gap-2">
                        <Button variant="danger" size="sm" onClick={handleRevoke}>
                            Yes, Revoke
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setShowRevoke(false)}>
                            Cancel
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

function NewTokenDisplay({ token, onClose }) {
    const [copied, setCopied] = useState(false);

    const copyToken = () => {
        navigator.clipboard.writeText(token);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border-2 border-emerald-300 dark:border-emerald-700 rounded-lg p-6"
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500 rounded-lg">
                        <Shield className="text-white" size={20} />
                    </div>
                    <div>
                        <h3 className="font-bold text-emerald-900 dark:text-emerald-200">Token Created Successfully!</h3>
                        <p className="text-sm text-emerald-700 dark:text-emerald-300 mt-1">
                            Save this token now - it won't be shown again
                        </p>
                    </div>
                </div>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-emerald-200 dark:border-emerald-800">
                <div className="flex items-center gap-2 mb-2">
                    <code className="flex-1 font-mono text-sm text-slate-900 dark:text-white break-all">
                        {token}
                    </code>
                    <button
                        onClick={copyToken}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors shrink-0"
                    >
                        {copied ? (
                            <Check className="text-emerald-600" size={18} />
                        ) : (
                            <Copy className="text-slate-400" size={18} />
                        )}
                    </button>
                </div>
            </div>
            <Button variant="ghost" onClick={onClose} className="mt-4 w-full">
                I've saved my token
            </Button>
        </motion.div>
    );
}

function CreateTokenModal({ onClose, onCreate }) {
    const [name, setName] = useState('');
    const [project, setProject] = useState('');
    const [permissions, setPermissions] = useState(['read', 'write', 'execute']);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [projects, setProjects] = useState([]);
    const [loadingProjects, setLoadingProjects] = useState(true);

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const res = await fetchApi('/api/projects/');
            const data = await res.json();
            setProjects(data || []);
        } catch (err) {
            console.error('Failed to fetch projects:', err);
        } finally {
            setLoadingProjects(false);
        }
    };

    const handleCreate = async () => {
        if (!name) {
            setError('Token name is required');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/execution/tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    project: project || null,
                    permissions
                })
            });
            const data = await res.json();
            if (res.ok) {
                onCreate(data.token);
            } else {
                setError(data.detail);
            }
        } catch (err) {
            setError('Failed to create token');
        } finally {
            setLoading(false);
        }
    };

    const togglePermission = (perm) => {
        setPermissions(prev =>
            prev.includes(perm)
                ? prev.filter(p => p !== perm)
                : [...prev, perm]
        );
    };

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
                    className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 dark:border-slate-700"
                >
                    <div className="p-6 border-b border-slate-100 dark:border-slate-700">
                        <h3 className="text-2xl font-bold text-slate-900 dark:text-white">Create New Token</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                            Generate a new API token for authentication
                        </p>
                    </div>

                    <div className="p-6 space-y-4">
                        {error && (
                            <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-3 text-sm text-rose-700 dark:text-rose-300">
                                {error}
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                                Token Name *
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Production CLI Token"
                                className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                                Project Scope
                            </label>
                            <select
                                value={project}
                                onChange={(e) => setProject(e.target.value)}
                                disabled={loadingProjects}
                                className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                            >
                                <option value="">All Projects</option>
                                {projects.map(proj => (
                                    <option key={proj.name} value={proj.name}>
                                        {proj.name}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Restrict this token to a specific project or allow access to all
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                Permissions
                            </label>
                            <div className="space-y-2">
                                {['read', 'write', 'execute', 'admin'].map(perm => (
                                    <label key={perm} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50">
                                        <input
                                            type="checkbox"
                                            checked={permissions.includes(perm)}
                                            onChange={() => togglePermission(perm)}
                                            className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
                                        />
                                        <div className="flex-1">
                                            <span className="font-medium text-slate-900 dark:text-white capitalize">{perm}</span>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                                {perm === 'read' && 'View pipelines, runs, and artifacts'}
                                                {perm === 'write' && 'Modify configurations and metadata'}
                                                {perm === 'execute' && 'Run pipelines and workflows'}
                                                {perm === 'admin' && 'Full access including token management'}
                                            </p>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="p-6 border-t border-slate-100 dark:border-slate-700 flex gap-3">
                        <Button variant="ghost" onClick={onClose} className="flex-1">
                            Cancel
                        </Button>
                        <Button onClick={handleCreate} disabled={loading} className="flex-1">
                            {loading ? 'Creating...' : 'Create Token'}
                        </Button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
