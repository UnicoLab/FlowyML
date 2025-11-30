import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../../../utils/api';
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceLine
} from 'recharts';
import { format } from 'date-fns';
import { Box, Activity, Clock, Tag } from 'lucide-react';
import { Card } from '../../../../components/ui/Card';
import { Badge } from '../../../../components/ui/Badge';

export function ProjectMetricsPanel({ projectId }) {
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchMetrics = async () => {
            setLoading(true);
            try {
                const resp = await fetchApi(`/api/projects/${projectId}/metrics?limit=500`);
                const data = await resp.json();
                setMetrics(Array.isArray(data?.metrics) ? data.metrics : []);
            } catch (err) {
                console.error('Failed to load project metrics', err);
                setError('Unable to load metrics');
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchMetrics();
        }
    }, [projectId]);

    if (loading) return <LoadingState />;
    if (error) return <ErrorState error={error} />;
    if (!metrics.length) return <EmptyState />;

    // Group metrics by model
    const modelGroups = metrics.reduce((acc, curr) => {
        if (!acc[curr.model_name]) {
            acc[curr.model_name] = [];
        }
        acc[curr.model_name].push(curr);
        return acc;
    }, {});

    return (
        <div className="space-y-8">
            {Object.entries(modelGroups).map(([modelName, modelMetrics]) => (
                <ModelMetricsDashboard
                    key={modelName}
                    modelName={modelName}
                    metrics={modelMetrics}
                />
            ))}
        </div>
    );
}

function ModelMetricsDashboard({ modelName, metrics }) {
    // Sort by date
    const sortedMetrics = [...metrics].sort((a, b) =>
        new Date(a.created_at) - new Date(b.created_at)
    );

    // Get latest metrics for summary
    const latestMetricEntry = sortedMetrics[sortedMetrics.length - 1];

    // Prepare data for charts
    // We need to pivot the data: one entry per timestamp, with keys for each metric
    // The API returns one row per metric name (e.g. "accuracy", "f1_score") per timestamp?
    // Wait, let's check seed data.
    // project_store.log_model_metrics calls save_metrics which saves individual rows?
    // Or does it save a JSON blob?
    // The seed data calls log_model_metrics with a dict of metrics.
    // The API likely returns flattened rows or the logged object.
    // Let's assume the API returns what we saw in the previous file:
    // { model_name, metric_name, metric_value, created_at, ... }

    // So we need to group by timestamp to form a "run" or "log event"
    const historyData = sortedMetrics.reduce((acc, curr) => {
        const timeKey = curr.created_at;
        if (!acc[timeKey]) {
            acc[timeKey] = {
                timestamp: timeKey,
                displayDate: format(new Date(timeKey), 'MMM d HH:mm'),
                tags: curr.tags,
                run_id: curr.run_id,
                environment: curr.environment
            };
        }
        // Add metric value
        acc[timeKey][curr.metric_name] = typeof curr.metric_value === 'number'
            ? parseFloat(curr.metric_value.toFixed(4))
            : curr.metric_value;
        return acc;
    }, {});

    const chartData = Object.values(historyData);

    // Identify metric names (keys) that are numbers
    const metricNames = [...new Set(metrics.map(m => m.metric_name))];
    const numericMetrics = metricNames.filter(name =>
        chartData.some(d => typeof d[name] === 'number')
    );

    // Separate latency from score metrics (usually 0-1)
    const scoreMetrics = numericMetrics.filter(name => !name.includes('latency') && !name.includes('loss'));
    const latencyMetrics = numericMetrics.filter(name => name.includes('latency'));

    return (
        <Card className="overflow-hidden border-slate-200 dark:border-slate-800">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                        <Box className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-white">{modelName}</h3>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                            <Clock size={12} />
                            Last updated: {format(new Date(latestMetricEntry.created_at), 'MMM d, yyyy HH:mm')}
                        </div>
                    </div>
                </div>
                <div className="flex gap-2">
                    {latestMetricEntry.environment && (
                        <Badge variant="outline" className="bg-white dark:bg-slate-800">
                            {latestMetricEntry.environment}
                        </Badge>
                    )}
                    <Badge className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 border-0">
                        {chartData.length} logs
                    </Badge>
                </div>
            </div>

            <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Latest Stats */}
                <div className="space-y-4">
                    <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Latest Performance</h4>
                    <div className="grid grid-cols-2 gap-3">
                        {scoreMetrics.map(metric => (
                            <div key={metric} className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                                <p className="text-xs text-slate-500 mb-1 capitalize">{metric.replace(/_/g, ' ')}</p>
                                <p className="text-lg font-bold text-slate-900 dark:text-white">
                                    {chartData[chartData.length - 1][metric]}
                                </p>
                            </div>
                        ))}
                        {latencyMetrics.map(metric => (
                            <div key={metric} className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                                <p className="text-xs text-slate-500 mb-1 capitalize">{metric.replace(/_/g, ' ')}</p>
                                <p className="text-lg font-bold text-slate-900 dark:text-white">
                                    {chartData[chartData.length - 1][metric]} <span className="text-xs font-normal text-slate-400">ms</span>
                                </p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Charts */}
                <div className="lg:col-span-2 space-y-6">
                    {scoreMetrics.length > 0 && (
                        <div className="h-[250px] w-full">
                            <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Score Trends</h4>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis
                                        dataKey="displayDate"
                                        stroke="#94a3b8"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        domain={[0, 1]}
                                        stroke="#94a3b8"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                        itemStyle={{ fontSize: '12px' }}
                                    />
                                    <Legend />
                                    {scoreMetrics.map((metric, idx) => (
                                        <Line
                                            key={metric}
                                            type="monotone"
                                            dataKey={metric}
                                            stroke={COLORS[idx % COLORS.length]}
                                            strokeWidth={2}
                                            dot={{ r: 3, fill: COLORS[idx % COLORS.length] }}
                                            activeDot={{ r: 5 }}
                                        />
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            </div>
        </Card>
    );
}

const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

function LoadingState() {
    return (
        <div className="h-64 flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
            <div className="flex flex-col items-center gap-3">
                <Activity className="w-8 h-8 text-primary-500 animate-spin" />
                <p className="text-slate-500 dark:text-slate-400">Loading metrics...</p>
            </div>
        </div>
    );
}

function ErrorState({ error }) {
    return (
        <div className="h-64 flex items-center justify-center border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-900/10 rounded-xl">
            <p className="text-rose-600 dark:text-rose-400">{error}</p>
        </div>
    );
}

function EmptyState() {
    return (
        <div className="h-64 flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
            <div className="text-center">
                <BarChart2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 dark:text-slate-400">No metrics logged yet</p>
                <p className="text-xs text-slate-400 mt-1">Run a pipeline with model evaluation to see metrics here</p>
            </div>
        </div>
    );
}
