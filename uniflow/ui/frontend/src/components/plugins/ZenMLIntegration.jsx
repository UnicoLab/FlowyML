import React, { useState } from 'react';
import { Server, ArrowRight, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { pluginService } from '../../services/pluginService';

export function ZenMLIntegration() {
    const [stackName, setStackName] = useState('');
    const [status, setStatus] = useState('idle'); // idle, importing, success, error
    const [logs, setLogs] = useState([]);

    const handleImport = async () => {
        if (!stackName) return;

        setStatus('importing');
        setLogs(['Connecting to ZenML client...', 'Fetching stack details...']);

        try {
            const result = await pluginService.importZenMLStack(stackName);
            setLogs(prev => [...prev, `Found stack '${stackName}' with ${result.components.length} components.`]);

            // Artificial delay for UX to show the progress
            await new Promise(r => setTimeout(r, 800));

            setLogs(prev => [...prev, 'Generating UniFlow configuration...', 'Import successful!']);
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
                    <Server className="text-primary-500 mt-1" size={20} />
                    <div>
                        <h3 className="font-medium text-slate-900 dark:text-white">Import ZenML Stack</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                            Migrate your existing ZenML infrastructure to UniFlow. We'll automatically detect your components and generate the necessary configuration.
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex gap-4 items-end">
                <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        ZenML Stack Name
                    </label>
                    <input
                        type="text"
                        placeholder="e.g., production-stack"
                        value={stackName}
                        onChange={(e) => setStackName(e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                </div>
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
