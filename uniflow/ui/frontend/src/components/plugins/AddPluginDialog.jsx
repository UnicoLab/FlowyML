import React, { useState } from 'react';
import { Plus, X, Package, Link as LinkIcon } from 'lucide-react';
import { Button } from '../ui/Button';

export function AddPluginDialog({ isOpen, onClose, onAdd }) {
    const [method, setMethod] = useState('package'); // 'package' or 'url'
    const [packageName, setPackageName] = useState('');
    const [url, setUrl] = useState('');

    const handleAdd = () => {
        if (method === 'package' && packageName) {
            onAdd({ type: 'package', value: packageName });
            setPackageName('');
            onClose();
        } else if (method === 'url' && url) {
            onAdd({ type: 'url', value: url });
            setUrl('');
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Add Plugin</h3>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Method Selector */}
                <div className="flex gap-2 mb-4 bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
                    <button
                        onClick={() => setMethod('package')}
                        className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all ${method === 'package'
                                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <div className="flex items-center justify-center gap-2">
                            <Package size={16} />
                            Package Name
                        </div>
                    </button>
                    <button
                        onClick={() => setMethod('url')}
                        className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all ${method === 'url'
                                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <div className="flex items-center justify-center gap-2">
                            <LinkIcon size={16} />
                            URL/Git
                        </div>
                    </button>
                </div>

                {/* Input Field */}
                <div className="mb-4">
                    {method === 'package' ? (
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                Package Name
                            </label>
                            <input
                                type="text"
                                placeholder="e.g., zenml-kubernetes"
                                value={packageName}
                                onChange={(e) => setPackageName(e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            />
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Install from PyPI by package name
                            </p>
                        </div>
                    ) : (
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                URL
                            </label>
                            <input
                                type="text"
                                placeholder="e.g., git+https://github.com/..."
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            />
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Install from Git repository or URL
                            </p>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                    <Button variant="outline" onClick={onClose} className="flex-1">
                        Cancel
                    </Button>
                    <Button
                        onClick={handleAdd}
                        disabled={method === 'package' ? !packageName : !url}
                        className="flex-1"
                    >
                        Install
                    </Button>
                </div>
            </div>
        </div>
    );
}
