import React, { useState, useEffect } from 'react';
import { Key, Copy, Trash2, Plus, Eye, EyeOff, Calendar, Shield, CheckCircle2 } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { format } from 'date-fns';

export function Settings() {
    const [tokens, setTokens] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newTokenName, setNewTokenName] = useState('');
    const [createdToken, setCreatedToken] = useState(null);
    const [visibleTokens, setVisibleTokens] = useState(new Set());

    useEffect(() => {
        fetchTokens();
    }, []);

    const fetchTokens = async () => {
        try {
            const response = await fetch('/api/execution/tokens');
            const data = await response.json();
            setTokens(data.tokens || []);
        } catch (error) {
            console.error('Failed to fetch tokens:', error);
        } finally {
            setLoading(false);
        }
    };

    const createToken = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/execution/tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newTokenName })
            });
            const data = await response.json();
            setCreatedToken(data.token);
            setNewTokenName('');
            fetchTokens();
        } catch (error) {
            console.error('Failed to create token:', error);
        }
    };

    const deleteToken = async (tokenId) => {
        if (!confirm('Are you sure you want to delete this token? This action cannot be undone.')) return;

        try {
            await fetch(`/api/execution/tokens/${tokenId}`, {
                method: 'DELETE'
            });
            fetchTokens();
        } catch (error) {
            console.error('Failed to delete token:', error);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        // Could add a toast notification here
    };

    const toggleTokenVisibility = (tokenId) => {
        setVisibleTokens(prev => {
            const newSet = new Set(prev);
            if (newSet.has(tokenId)) {
                newSet.delete(tokenId);
            } else {
                newSet.add(tokenId);
            }
            return newSet;
        });
    };

    const maskToken = (token) => {
        if (!token || typeof token !== 'string') return '••••••••••••••••••••••••••••••••••••••••••••••••';
        return `${token.substring(0, 8)}${'•'.repeat(32)}${token.substring(token.length - 8)}`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl text-white">
                            <Key size={28} />
                        </div>
                        API Tokens
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Manage API tokens for programmatic access to flowyml
                    </p>
                </div>
                <Button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700"
                >
                    <Plus size={16} />
                    Create Token
                </Button>
            </div>

            {/* Security Notice */}
            <Card className="border-l-4 border-l-amber-500 bg-amber-50 dark:bg-amber-900/10">
                <div className="flex items-start gap-3">
                    <Shield className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" size={20} />
                    <div>
                        <h3 className="font-semibold text-amber-900 dark:text-amber-200">Security Notice</h3>
                        <p className="text-sm text-amber-800 dark:text-amber-300 mt-1">
                            Treat your API tokens like passwords. Never share them publicly or commit them to version control.
                        </p>
                    </div>
                </div>
            </Card>

            {/* Token List */}
            <div className="grid gap-4">
                {tokens.length === 0 ? (
                    <Card className="text-center py-16 bg-slate-50 dark:bg-slate-800/30">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Key className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No API tokens yet</h3>
                        <p className="text-slate-500 max-w-md mx-auto mb-6">
                            Create your first API token to start making programmatic requests to flowyml
                        </p>
                        <Button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-primary-600 hover:bg-primary-700"
                        >
                            <Plus size={16} className="mr-2" />
                            Create Your First Token
                        </Button>
                    </Card>
                ) : (
                    Array.isArray(tokens) && tokens.map((token) => (
                        <Card key={token.id} className="hover:shadow-lg transition-all duration-200">
                            <div className="flex items-center justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
                                            <Key className="text-primary-600 dark:text-primary-400" size={20} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-lg font-semibold text-slate-900 dark:text-white truncate">
                                                {token.name}
                                            </h3>
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                                                    <Calendar size={12} />
                                                    Created {format(new Date(token.created_at), 'MMM d, yyyy')}
                                                </span>
                                                <Badge variant="secondary" className="text-xs">
                                                    {token.id}
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Token Value */}
                                    <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3 font-mono text-sm border border-slate-200 dark:border-slate-700">
                                        <div className="flex items-center gap-2">
                                            <code className="flex-1 truncate text-slate-700 dark:text-slate-300">
                                                {visibleTokens.has(token.id) ? token.token : maskToken(token.token)}
                                            </code>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => toggleTokenVisibility(token.id)}
                                                    className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors"
                                                    title={visibleTokens.has(token.id) ? 'Hide token' : 'Show token'}
                                                >
                                                    {visibleTokens.has(token.id) ? (
                                                        <EyeOff size={16} className="text-slate-500" />
                                                    ) : (
                                                        <Eye size={16} className="text-slate-500" />
                                                    )}
                                                </button>
                                                <button
                                                    onClick={() => copyToClipboard(token.token)}
                                                    className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors"
                                                    title="Copy to clipboard"
                                                >
                                                    <Copy size={16} className="text-slate-500" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <Button
                                    onClick={() => deleteToken(token.id)}
                                    variant="ghost"
                                    className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex-shrink-0"
                                >
                                    <Trash2 size={18} />
                                </Button>
                            </div>
                        </Card>
                    ))
                )}
            </div>

            {/* Create Token Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="max-w-lg w-full">
                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Plus className="text-primary-600" size={24} />
                            Create New Token
                        </h2>

                        <form onSubmit={createToken} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                    Token Name
                                </label>
                                <input
                                    type="text"
                                    value={newTokenName}
                                    onChange={(e) => setNewTokenName(e.target.value)}
                                    placeholder="e.g., Production API, CI/CD Pipeline"
                                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    required
                                />
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    Choose a descriptive name to identify this token's purpose
                                </p>
                            </div>

                            <div className="flex gap-3 justify-end pt-4">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => setShowCreateModal(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    className="bg-primary-600 hover:bg-primary-700"
                                >
                                    Create Token
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            )}

            {/* Token Created Success Modal */}
            {createdToken && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="max-w-2xl w-full">
                        <div className="text-center mb-6">
                            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mb-4">
                                <CheckCircle2 className="text-green-600 dark:text-green-400" size={32} />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Token Created Successfully!</h2>
                            <p className="text-slate-500 dark:text-slate-400 mt-2">
                                Copy this token now. You won't be able to see it again.
                            </p>
                        </div>

                        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 mb-6 border-2 border-primary-200 dark:border-primary-800">
                            <div className="flex items-center gap-2 mb-2">
                                <code className="flex-1 font-mono text-sm break-all text-slate-900 dark:text-white">
                                    {createdToken}
                                </code>
                                <button
                                    onClick={() => copyToClipboard(createdToken)}
                                    className="p-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors flex-shrink-0"
                                    title="Copy to clipboard"
                                >
                                    <Copy size={18} />
                                </button>
                            </div>
                        </div>

                        <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6">
                            <div className="flex gap-2">
                                <Shield className="text-amber-600 dark:text-amber-400 flex-shrink-0" size={20} />
                                <div className="text-sm text-amber-800 dark:text-amber-200">
                                    <strong>Important:</strong> Store this token securely. It won't be displayed again.
                                </div>
                            </div>
                        </div>

                        <Button
                            onClick={() => {
                                setCreatedToken(null);
                                setShowCreateModal(false);
                            }}
                            className="w-full bg-primary-600 hover:bg-primary-700"
                        >
                            I've Saved My Token
                        </Button>
                    </Card>
                </div>
            )}
        </div>
    );
}
