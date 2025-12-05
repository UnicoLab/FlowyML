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
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const runIdsParam = searchParams.get('runs');
    const run1Id = searchParams.get('run1');
    const run2Id = searchParams.get('run2');

    // Normalize run IDs from different possible query params
    const runIds = runIdsParam
        ? runIdsParam.split(',').filter(Boolean)
        : [run1Id, run2Id].filter(Boolean);

    useEffect(() => {
        if (runIds.length < 2) {
            setError('Please select at least two runs to compare.');
            setLoading(false);
            return;
        }
        fetchData();
    }, [runIdsParam, run1Id, run2Id]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const promises = runIds.map(id => fetchApi(`/api/runs/${id}`));
            const responses = await Promise.all(promises);

            const data = [];
            for (const res of responses) {
                if (!res.ok) throw new Error('Failed to fetch run details');
                data.push(await res.json());
            }

            setRuns(data);
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
                <p className="text-slate-500">Loading comparison...</p>
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

    // Helper to find best values (min duration)
    const minDuration = Math.min(...runs.map(r => r.duration || Infinity));

    // Calculate step specific diffs
    const allStepNames = Array.from(new Set(
        runs.flatMap(r => Object.keys(r.steps || {}))
    ));

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 overflow-y-auto">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10 w-full overflow-x-auto">
                <div className="w-full min-w-max px-6 py-4">
                    <div className="flex items-center gap-4 mb-4">
                        <Link to="/runs" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-full transition-colors">
                            <ArrowLeft size={20} className="text-slate-500" />
                        </Link>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            Run Comparison
                            <Badge variant="secondary" className="ml-2">({runs.length} runs)</Badge>
                        </h1>
                    </div>

                    <div className={`grid gap-4`} style={{ gridTemplateColumns: `repeat(${runs.length}, minmax(300px, 1fr))` }}>
                        {runs.map(run => (
                            <div key={run.run_id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                                <StatusBadge status={run.status} />
                                <div className="min-w-0">
                                    <h3 className="font-bold text-slate-900 dark:text-white truncate" title={run.run_id}>{run.run_id}</h3>
                                    <p className="text-xs text-slate-500">{format(new Date(run.start_time), 'MMM d, HH:mm:ss')}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="w-full overflow-x-auto">
                <div className="min-w-max px-6 py-8 space-y-8">

                    {/* Metrics Comparison */}
                    <section>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Activity size={18} /> Performance Metrics
                        </h2>
                        <Card className="overflow-hidden">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs uppercase text-slate-500 font-medium">
                                    <tr>
                                        <th className="px-6 py-3 w-48 sticky left-0 bg-slate-50 dark:bg-slate-800 z-10 border-r border-slate-200 dark:border-slate-700">Metric</th>
                                        {runs.map((run, i) => (
                                            <th key={run.run_id} className={`px-6 py-3 min-w-[200px] ${i < runs.length - 1 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}>
                                                {run.run_id.slice(0, 8)}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Duration</td>
                                        {runs.map((run, i) => (
                                            <td key={run.run_id} className={`px-6 py-3 ${i < runs.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''} ${run.duration === minDuration ? 'text-emerald-600 font-bold' : 'text-slate-600'}`}>
                                                {run.duration?.toFixed(2)}s
                                                {run.duration === minDuration && runs.length > 1 && <span className="ml-2 text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 px-1.5 py-0.5 rounded-full">Fastest</span>}
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Step Count</td>
                                        {runs.map((run, i) => (
                                            <td key={run.run_id} className={`px-6 py-3 text-slate-600 ${i < runs.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                {Object.keys(run.steps || {}).length}
                                            </td>
                                        ))}
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
                                        <th className="px-6 py-3 w-48 sticky left-0 bg-slate-50 dark:bg-slate-800 z-10 border-r border-slate-200 dark:border-slate-700">Step Name</th>
                                        {runs.map((run, i) => (
                                            <th key={run.run_id} className={`px-6 py-3 min-w-[200px] ${i < runs.length - 1 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}>
                                                {run.run_id.slice(0, 8)}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    {allStepNames.map(stepName => {
                                        // Calculate diffs for this step row
                                        const stepDurations = runs.map(r => r.steps?.[stepName]?.duration || Infinity);
                                        const minStepDuration = Math.min(...stepDurations);

                                        return (
                                            <tr key={stepName} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                                <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">{stepName}</td>
                                                {runs.map((run, i) => {
                                                    const step = run.steps?.[stepName];
                                                    return (
                                                        <td key={run.run_id} className={`px-6 py-3 ${i < runs.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                            {step ? (
                                                                <div className="flex items-center justify-between gap-4">
                                                                    <StatusBadge status={step.success ? 'completed' : step.error ? 'failed' : 'pending'} size="sm" />
                                                                    <span className={`font-mono text-xs ${step.duration === minStepDuration && runs.length > 1 ? 'text-emerald-600 font-bold' : 'text-slate-500'}`}>
                                                                        {step.duration?.toFixed(2)}s
                                                                    </span>
                                                                </div>
                                                            ) : (
                                                                <span className="text-slate-400 italic text-xs">Not executed</span>
                                                            )}
                                                        </td>
                                                    );
                                                })}
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </Card>
                    </section>
                </div>
            </div>
        </div>
    );
}
