import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../../../utils/api';

function MetricChip({ label, value }) {
    return (
        <div className="inline-flex items-center px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 mr-2 mb-2">
            <span className="text-slate-500 dark:text-slate-300 mr-1">{label}</span>
            <span className="font-semibold text-slate-900 dark:text-white">{value}</span>
        </div>
    );
}

export function ProjectMetricsPanel({ projectId }) {
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchMetrics = async () => {
            setLoading(true);
            setError(null);
            try {
                const resp = await fetchApi(`/api/projects/${projectId}/metrics?limit=50`);
                const data = await resp.json();
                setMetrics(Array.isArray(data?.metrics) ? data.metrics : []);
            } catch (err) {
                console.error('Failed to load project metrics', err);
                setError('Unable to load metrics');
                setMetrics([]);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchMetrics();
        }
    }, [projectId]);

    if (loading) {
        return (
            <div className="h-32 flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                <span className="text-sm text-slate-500 dark:text-slate-400">Loading production metrics...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="h-32 flex items-center justify-center border border-rose-200/50 dark:border-rose-900/50 rounded-lg bg-rose-50/50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-300 text-sm">
                {error}
            </div>
        );
    }

    if (!metrics.length) {
        return (
            <div className="h-32 flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                <span className="text-sm text-slate-500 dark:text-slate-400">
                    No production metrics have been logged yet. POST to /api/metrics/log to get started.
                </span>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {metrics.slice(0, 10).map((metric, idx) => (
                <div
                    key={`${metric.model_name}-${metric.metric_name}-${metric.created_at}-${idx}`}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm shadow-slate-100/40 dark:shadow-none"
                >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <p className="text-sm text-slate-500 dark:text-slate-400">Model</p>
                            <p className="text-base font-semibold text-slate-900 dark:text-white">{metric.model_name}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-slate-500 dark:text-slate-400">Logged</p>
                            <p className="text-sm font-medium text-slate-900 dark:text-slate-50">
                                {new Date(metric.created_at).toLocaleString()}
                            </p>
                        </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-3">
                        {metric.environment && <MetricChip label="Env" value={metric.environment} />}
                        {metric.run_id && <MetricChip label="Run" value={metric.run_id} />}
                        {Object.entries(metric.tags || {}).map(([tagKey, tagVal]) => (
                            <MetricChip key={`${metric.created_at}-${tagKey}`} label={tagKey} value={String(tagVal)} />
                        ))}
                    </div>

                    <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4">
                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Metric</p>
                            <p className="text-lg font-semibold text-slate-900 dark:text-white">{metric.metric_name}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Value</p>
                            <p className="text-lg font-semibold text-emerald-600 dark:text-emerald-300">{metric.metric_value}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Project</p>
                            <p className="text-lg font-semibold text-slate-900 dark:text-white">{metric.project}</p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
