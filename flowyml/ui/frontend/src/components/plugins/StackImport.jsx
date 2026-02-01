import React, { useState } from 'react';
import { Layers, ArrowRight, CheckCircle, AlertCircle, Loader2, Import } from 'lucide-react';
import { Button } from '../ui/Button';
import { pluginService } from '../../services/pluginService';

export function StackImport() {
    const [stackName, setStackName] = useState('');
    const [importType, setImportType] = useState('zenml');
    const [status, setStatus] = useState('idle'); // idle, importing, success, error
    const [logs, setLogs] = useState([]);

    const handleImport = async () => {
        if (!stackName) return;

        setStatus('importing');
        setLogs([`Connecting to ${importType === 'zenml' ? 'ZenML' : 'Source'}...`, 'Fetching stack details...']);

        try {
            const result = await pluginService.importStack(stackName, importType);
            setLogs(prev => [...prev, `Found stack '${stackName}' with ${result.components.length} components.`]);

            // Artificial delay for UX
            await new Promise(r => setTimeout(r, 800));

            setLogs(prev => [...prev, 'Generating flowyml configuration...', 'Import successful!']);
            setStatus('success');
        } catch (error) {
            console.error('Import failed:', error);
            setLogs(prev => [...prev, `Error: ${error.message}`]);
            setStatus('error');
        }
    };

    return (
        <div className="space-y-6">
            <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                <div className="flex items-start gap-3">
                    <Import className="text-primary-500 mt-1" size={20} />
                    <div>
                        <h3 className="font-medium text-slate-900 dark:text-white">Import External Stack</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                            Migrate your existing infrastructure to FlowyML. We'll automatically detect your components and generate the necessary configuration.
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Source Type
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            onClick={() => setImportType('zenml')}
                            className={`p-3 rounded-lg border text-sm font-medium flex items-center justify-center gap-2 transition-all ${importType === 'zenml'
                                    ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-500 text-primary-700 dark:text-primary-300'
                                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                }`}
                        >
                            ZenML
                        </button>
                        <button
                            disabled
                            className="p-3 rounded-lg border border-dashed border-slate-200 dark:border-slate-800 text-slate-400 text-sm font-medium flex items-center justify-center gap-2 cursor-not-allowed"
                        >
                            FlowyML YAML (Coming Soon)
                        </button>
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Stack Name
                    </label>
                    <input
                        type="text"
                        placeholder="e.g., production-stack"
                        value={stackName}
                        onChange={(e) => setStackName(e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                </div>
            </div>

            <div className="flex justify-end">
                <Button
                    onClick={handleImport}
                    disabled={status === 'importing' || !stackName}
                    className="flex items-center gap-2"
                >
                    {status === 'importing' ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            Importing...
                        </>
                    ) : (
                        <>
                            Start Import
                            <ArrowRight size={16} />
                        </>
                    )}
                </Button>
            </div>

            {status !== 'idle' && (
                <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm overflow-hidden">
                    <div className="space-y-1">
                        {logs.map((log, i) => (
                            <div key={i} className="flex items-center gap-2 text-slate-300">
                                <span className="text-slate-600">➜</span>
                                {log}
                            </div>
                        ))}
                    </div>
                    {status === 'success' && (
                        <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-2 text-green-400">
                            <CheckCircle size={16} />
                            <span>Stack imported successfully! You can now use it in your pipelines.</span>
                        </div>
                    )}
                    {status === 'error' && (
                        <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-2 text-red-400">
                            <AlertCircle size={16} />
                            <span>Failed to import stack. Please check the name and try again.</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
