import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { fetchApi } from '../../utils/api';
import { ArrowLeft, PlayCircle, Clock, Calendar, CheckCircle, XCircle, AlertTriangle, Activity, ArrowRight, Layers } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { StatusBadge } from '../../components/ui/ExecutionStatus';

export function RunComparisonPage() {
    const [searchParams] = useSearchParams();
    const [runs, setRuns] = useState({ left: null, right: null });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const run1Id = searchParams.get('run1');
    const run2Id = searchParams.get('run2');

    useEffect(() => {
        if (!run1Id || !run2Id) {
            setError('Please select two runs to compare.');
            setLoading(false);
            return;
        }
        fetchData();
    }, [run1Id, run2Id]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [res1, res2] = await Promise.all([
                fetchApi(`/api/runs/${run1Id}`),
                fetchApi(`/api/runs/${run2Id}`)
            ]);

            if (!res1.ok || !res2.ok) throw new Error('Failed to fetch run details');

            const data1 = await res1.json();
            const data2 = await res2.json();

            setRuns({ left: data1, right: data2 });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                <p className="text-slate-500">Loading runs for comparison...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="bg-red-50 p-6 rounded-xl border border-red-100 max-w-md text-center">
                    <AlertTriangle className="mx-auto text-red-500 mb-2" size={32} />
                    <h2 className="text-xl font-bold text-slate-800 mb-2">Error</h2>
                    <p className="text-slate-600 mb-4">{error}</p>
                    <Link to="/runs">
                        <Button>Back to Runs</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const { left, right } = runs;

    // Helper to compare values
    const getDiffColor = (val1, val2, type = 'text') => {
        if (val1 === val2) return type === 'bg' ? '' : 'text-slate-500';
        return type === 'bg' ? 'bg-yellow-50 dark:bg-yellow-900/10' : 'text-slate-900 font-medium';
    };

    // Calculate step specific diffs
    const allStepNames = Array.from(new Set([
        ...Object.keys(left.steps || {}),
        ...Object.keys(right.steps || {})
    ]));

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 overflow-y-auto">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center gap-4 mb-4">
                        <Link to="/runs" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-full transition-colors">
                            <ArrowLeft size={20} className="text-slate-500" />
                        </Link>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            Run Comparison
                            <Badge variant="secondary" className="ml-2">Beta</Badge>
                        </h1>
                    </div>

                    <div className="grid grid-cols-2 gap-8">
                        {/* Run 1 Header */}
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                            <StatusBadge status={left.status} />
                            <div className="min-w-0">
                                <h3 className="font-bold text-slate-900 dark:text-white truncate">{left.run_id}</h3>
                                <p className="text-xs text-slate-500">{format(new Date(left.start_time), 'MMM d, HH:mm:ss')}</p>
                            </div>
                        </div>

                        {/* Run 2 Header */}
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                            <StatusBadge status={right.status} />
                            <div className="min-w-0">
                                <h3 className="font-bold text-slate-900 dark:text-white truncate">{right.run_id}</h3>
                                <p className="text-xs text-slate-500">{format(new Date(right.start_time), 'MMM d, HH:mm:ss')}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">

                {/* Metrics Comparison */}
                <section>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Activity size={18} /> Performance Metrics
                    </h2>
                    <Card className="overflow-hidden">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs uppercase text-slate-500 font-medium">
                                <tr>
                                    <th className="px-6 py-3 w-1/3">Metric</th>
                                    <th className="px-6 py-3 w-1/3 border-r border-slate-200 dark:border-slate-700">Run A</th>
                                    <th className="px-6 py-3 w-1/3">Run B</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                    <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300">Duration</td>
                                    <td className={`px-6 py-3 border-r border-slate-100 dark:border-slate-700 ${left.duration < right.duration ? 'text-emerald-600' : 'text-slate-600'}`}>
                                        {left.duration?.toFixed(2)}s
                                    </td>
                                    <td className={`px-6 py-3 ${right.duration < left.duration ? 'text-emerald-600' : 'text-slate-600'}`}>
                                        {right.duration?.toFixed(2)}s
                                    </td>
                                </tr>
                                <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                    <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300">Step Count</td>
                                    <td className="px-6 py-3 border-r border-slate-100 dark:border-slate-700 text-slate-600">
                                        {Object.keys(left.steps || {}).length}
                                    </td>
                                    <td className="px-6 py-3 text-slate-600">
                                        {Object.keys(right.steps || {}).length}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </Card>
                </section>

                {/* Steps Comparison */}
                <section>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Layers size={18} /> Step Execution
                    </h2>
                    <Card className="overflow-hidden">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs uppercase text-slate-500 font-medium">
                                <tr>
                                    <th className="px-6 py-3 w-1/3">Step Name</th>
                                    <th className="px-6 py-3 w-1/3 border-r border-slate-200 dark:border-slate-700">Run A (Status / Time)</th>
                                    <th className="px-6 py-3 w-1/3">Run B (Status / Time)</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                {allStepNames.map(stepName => {
                                    const stepA = left.steps?.[stepName];
                                    const stepB = right.steps?.[stepName];

                                    // Highlight if status matches but duration is significantly different (>20%)
                                    const durationDiffers = stepA?.duration && stepB?.duration &&
                                        Math.abs(stepA.duration - stepB.duration) / Math.min(stepA.duration, stepB.duration) > 0.2;

                                    return (
                                        <tr key={stepName} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                            <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300">{stepName}</td>

                                            {/* Run A Step */}
                                            <td className="px-6 py-3 border-r border-slate-100 dark:border-slate-700">
                                                {stepA ? (
                                                    <div className="flex items-center justify-between">
                                                        <StatusBadge status={stepA.success ? 'completed' : stepA.error ? 'failed' : 'pending'} size="sm" />
                                                        <span className={`font-mono text-xs ${durationDiffers ? 'text-amber-600 font-bold' : 'text-slate-500'}`}>
                                                            {stepA.duration?.toFixed(2)}s
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span className="text-slate-400 italic text-xs">Not executed</span>
                                                )}
                                            </td>

                                            {/* Run B Step */}
                                            <td className="px-6 py-3">
                                                {stepB ? (
                                                    <div className="flex items-center justify-between">
                                                        <StatusBadge status={stepB.success ? 'completed' : stepB.error ? 'failed' : 'pending'} size="sm" />
                                                        <span className={`font-mono text-xs ${durationDiffers ? 'text-amber-600 font-bold' : 'text-slate-500'}`}>
                                                            {stepB.duration?.toFixed(2)}s
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span className="text-slate-400 italic text-xs">Not executed</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </Card>
                </section>
            </div>
        </div>
    );
}
