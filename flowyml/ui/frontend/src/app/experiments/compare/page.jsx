import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { fetchApi } from '../../../utils/api';
import { ArrowLeft, FlaskConical, Calendar, CheckCircle, XCircle, AlertTriangle, Activity, Clock, Layout } from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { format } from 'date-fns';

export function ExperimentComparisonPage() {
    const [searchParams] = useSearchParams();
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const idsParam = searchParams.get('ids');
    const ids = idsParam ? idsParam.split(',').filter(Boolean) : [];

    useEffect(() => {
        if (ids.length < 2) {
            setError('Please select at least two experiments to compare.');
            setLoading(false);
            return;
        }
        fetchData();
    }, [idsParam]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // 1. Fetch Experiments Details
            // Since we don't have a bulk API, we fetch individually
            // Ideally we'd have /api/experiments?ids=... or similar
            // But we can just iterate.

            // Note: Experiment API might not return run stats directly.
            // We might need to fetch runs for each experiment to calculate stats if they aren't provided.
            // Let's assume /api/experiments/{id} returns basic details.

            // To get stats, we might need to fetch runs.
            // Let's parallelize fetching experiment details.
            // CAUTION: If /api/experiments/{id} doesn't exist, we might need to filter from the list API.
            // Let's assume filtering from list API is safer if individual endpoint isn't guaranteed.
            // Actually, usually detail endpoint exists. Let's try to map the list first since current API usage in Experiments page used list.

            // Let's use the list endpoint with a filter if possible, or just fetch all and filter client side (not efficient but safe if list is small).
            // Better: Fetch all experiments (like in main page) and find the ones we need.
            // This is safer given we know /api/experiments/ endpoint works.

            const res = await fetchApi('/api/experiments/?limit=1000'); // Fetch enough
            const data = await res.json();
            const allExperiments = data.experiments || [];

            const selectedExperiments = allExperiments.filter(e => ids.includes(e.experiment_id));

            // Now for each experiment, we need run stats.
            // The list object might have run_count. But for success rate we need runs.
            // Let's fetch runs for each selected experiment.
            // This could be heavy, but it's "Comparison" page, user expects detail.

            const enrichedExperiments = await Promise.all(selectedExperiments.map(async (exp) => {
                try {
                    // Fetch runs for this experiment.
                    // Assuming we can filter by pipeline or if the backend supports filter by experiment
                    // Looking at `ExperimentDetailsPanel`, it filters by pipeline_name AND run_id list.
                    // Let's replicate that logic.

                    const runsUrl = exp.pipeline_name
                        ? `/api/runs?pipeline=${encodeURIComponent(exp.pipeline_name)}&limit=100`
                        : `/api/runs?limit=100`;

                    const runsRes = await fetchApi(runsUrl);
                    const runsData = await runsRes.json();

                    // Filter relevant runs
                    const relevantRuns = (runsData.runs || []).filter(r =>
                        r.pipeline_name === exp.pipeline_name ||
                        (exp.runs && exp.runs.includes(r.run_id))
                    );

                    // Calculate stats
                    const total = relevantRuns.length;
                    const success = relevantRuns.filter(r => r.status === 'completed').length;
                    const failed = relevantRuns.filter(r => r.status === 'failed').length;
                    const durations = relevantRuns.map(r => r.duration || 0).filter(d => d > 0);
                    const avgDuration = durations.length > 0
                        ? durations.reduce((a, b) => a + b, 0) / durations.length
                        : 0;

                    return {
                        ...exp,
                        stats: {
                            total,
                            success,
                            failed,
                            avgDuration,
                            successRate: total > 0 ? (success / total) * 100 : 0
                        }
                    };
                } catch (e) {
                    console.error(`Failed to fetch stats for experiment ${exp.name}`, e);
                    return { ...exp, stats: { total: 0, success: 0, failed: 0, avgDuration: 0, successRate: 0 } };
                }
            }));

            // Sort by order of IDs in param to maintain user selection order
            const ordered = ids.map(id => enrichedExperiments.find(e => e.experiment_id === id)).filter(Boolean);

            setExperiments(ordered);
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
                <p className="text-slate-500">Loading experiments...</p>
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
                    <Link to="/experiments">
                        <Button>Back to Experiments</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const highestSuccessRate = Math.max(...experiments.map(e => e.stats.successRate));
    const lowestAvgDuration = Math.min(...experiments.map(e => e.stats.avgDuration).filter(d => d > 0));

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 overflow-y-auto">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10 w-full overflow-x-auto">
                <div className="w-full min-w-max px-6 py-4">
                    <div className="flex items-center gap-4 mb-4">
                        <Link to="/experiments" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-full transition-colors">
                            <ArrowLeft size={20} className="text-slate-500" />
                        </Link>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            Experiment Comparison
                            <Badge variant="secondary" className="ml-2">({experiments.length} selected)</Badge>
                        </h1>
                    </div>

                    <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${experiments.length}, minmax(300px, 1fr))` }}>
                        {experiments.map(exp => (
                            <div key={exp.experiment_id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600">
                                    <FlaskConical size={20} />
                                </div>
                                <div className="min-w-0">
                                    <h3 className="font-bold text-slate-900 dark:text-white truncate" title={exp.name}>{exp.name}</h3>
                                    <p className="text-xs text-slate-500">{format(new Date(exp.created_at || Date.now()), 'MMM d, yyyy')}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="w-full overflow-x-auto">
                <div className="min-w-max px-6 py-8 space-y-8">
                    {/* Overview Comparison */}
                    <section>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Layout size={18} /> Overview
                        </h2>
                        <Card className="overflow-hidden">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs uppercase text-slate-500 font-medium">
                                    <tr>
                                        <th className="px-6 py-3 w-48 sticky left-0 bg-slate-50 dark:bg-slate-800 z-10 border-r border-slate-200 dark:border-slate-700">Attribute</th>
                                        {experiments.map((exp, i) => (
                                            <th key={exp.experiment_id} className={`px-6 py-3 min-w-[300px] ${i < experiments.length - 1 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}>
                                                {exp.name}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Description</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 text-slate-600 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                {exp.description || '-'}
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Project</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 text-slate-600 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                {exp.project || '-'}
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Pipeline Base</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 text-slate-600 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                {exp.pipeline_name || '-'}
                                                {exp.pipeline_version && <Badge variant="outline" className="ml-2">v{exp.pipeline_version}</Badge>}
                                            </td>
                                        ))}
                                    </tr>
                                </tbody>
                            </table>
                        </Card>
                    </section>

                    {/* Stats Comparison */}
                    <section>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Activity size={18} /> Performance Stats
                        </h2>
                        <Card className="overflow-hidden">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs uppercase text-slate-500 font-medium">
                                    <tr>
                                        <th className="px-6 py-3 w-48 sticky left-0 bg-slate-50 dark:bg-slate-800 z-10 border-r border-slate-200 dark:border-slate-700">Metric</th>
                                        {experiments.map((exp, i) => (
                                            <th key={exp.experiment_id} className={`px-6 py-3 min-w-[300px] ${i < experiments.length - 1 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}>
                                                {exp.name}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Success Rate</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''} ${exp.stats.successRate === highestSuccessRate && exp.stats.successRate > 0 ? 'text-emerald-600 font-bold' : 'text-slate-600'}`}>
                                                {exp.stats.successRate.toFixed(1)}%
                                                {exp.stats.successRate === highestSuccessRate && exp.stats.successRate > 0 && experiments.length > 1 &&
                                                    <span className="ml-2 text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 px-1.5 py-0.5 rounded-full">Best</span>
                                                }
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Avg Duration</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''} ${exp.stats.avgDuration === lowestAvgDuration && exp.stats.avgDuration > 0 ? 'text-emerald-600 font-bold' : 'text-slate-600'}`}>
                                                {exp.stats.avgDuration.toFixed(1)}s
                                                {exp.stats.avgDuration === lowestAvgDuration && exp.stats.avgDuration > 0 && experiments.length > 1 &&
                                                    <span className="ml-2 text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 px-1.5 py-0.5 rounded-full">Fastest</span>
                                                }
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Total Runs</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 text-slate-600 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''}`}>
                                                {exp.stats.total}
                                            </td>
                                        ))}
                                    </tr>
                                    <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                        <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-300 sticky left-0 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-700">Failures</td>
                                        {experiments.map((exp, i) => (
                                            <td key={exp.experiment_id} className={`px-6 py-3 ${i < experiments.length - 1 ? 'border-r border-slate-100 dark:border-slate-700' : ''} ${exp.stats.failed > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                                {exp.stats.failed}
                                            </td>
                                        ))}
                                    </tr>
                                </tbody>
                            </table>
                        </Card>
                    </section>
                </div>
            </div>
        </div>
    );
}
