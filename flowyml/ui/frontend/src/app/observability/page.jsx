import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { Activity, TrendingUp, Zap, Clock, BarChart2, CheckCircle, XCircle } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';

export function Observability() {
    const [orchestratorMetrics, setOrchestratorMetrics] = useState(null);
    const [cacheMetrics, setCacheMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const [orchRes, cacheRes] = await Promise.all([
                    fetchApi('/api/metrics/observability/orchestrator'),
                    fetchApi('/api/metrics/observability/cache')
                ]);

                const orchData = await orchRes.json();
                const cacheData = await cacheRes.json();

                setOrchestratorMetrics(orchData);
                setCacheMetrics(cacheData);
            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchMetrics();
        // Refresh every 30 seconds
        const interval = setInterval(fetchMetrics, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    const successRate = orchestratorMetrics?.success_rate || 0;
    const cacheHitRate = cacheMetrics?.cache_hit_rate || 0;

    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <Activity className="text-primary-500" size={32} />
                        Observability Dashboard
                    </h1>
                    <p className="text-slate-500 mt-1">
                        System performance and metrics (Last 30 days)
                    </p>
                </div>
                <Badge variant="secondary" className="text-xs">
                    Auto-refresh: 30s
                </Badge>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<BarChart2 size={24} />}
                    label="Total Runs"
                    value={orchestratorMetrics?.total_runs || 0}
                    color="blue"
                />
                <MetricCard
                    icon={<CheckCircle size={24} />}
                    label="Success Rate"
                    value={`${(successRate * 100).toFixed(1)}%`}
                    color="emerald"
                    trend={successRate >= 0.9 ? 'positive' : successRate >= 0.7 ? 'neutral' : 'negative'}
                />
                <MetricCard
                    icon={<Clock size={24} />}
                    label="Avg Duration"
                    value={`${(orchestratorMetrics?.avg_duration_seconds || 0).toFixed(2)}s`}
                    color="purple"
                />
                <MetricCard
                    icon={<Zap size={24} />}
                    label="Cache Hit Rate"
                    value={`${(cacheHitRate * 100).toFixed(1)}%`}
                    color="amber"
                    trend={cacheHitRate >= 0.5 ? 'positive' : cacheHitRate >= 0.2 ? 'neutral' : 'negative'}
                />
            </div>

            {/* Detailed Sections */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Orchestrator Performance */}
                <Card className="p-6">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <TrendingUp className="text-primary-500" size={20} />
                        Orchestrator Performance
                    </h3>

                    <div className="space-y-4">
                        {/* Status Distribution */}
                        <div>
                            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                                Status Distribution
                            </h4>
                            <div className="space-y-2">
                                {orchestratorMetrics?.status_distribution &&
                                    Object.entries(orchestratorMetrics.status_distribution).map(([status, count]) => (
                                        <div key={status} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div className={`w-3 h-3 rounded-full ${status === 'completed' ? 'bg-emerald-500' :
                                                        status === 'failed' ? 'bg-rose-500' :
                                                            'bg-amber-500'
                                                    }`} />
                                                <span className="text-sm text-slate-600 dark:text-slate-400 capitalize">
                                                    {status}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-sm font-mono font-semibold text-slate-900 dark:text-white">
                                                    {count}
                                                </span>
                                                <div className="w-24 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                                    <div
                                                        className={`h-2 rounded-full ${status === 'completed' ? 'bg-emerald-500' :
                                                                status === 'failed' ? 'bg-rose-500' :
                                                                    'bg-amber-500'
                                                            }`}
                                                        style={{
                                                            width: `${(count / orchestratorMetrics.total_runs) * 100}%`
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                }
                            </div>
                        </div>

                        {/* Summary Stats */}
                        <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                                <div className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">
                                    Success Rate
                                </div>
                                <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
                                    {(successRate * 100).toFixed(1)}%
                                </div>
                            </div>
                            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                <div className="text-xs text-blue-600 dark:text-blue-400 mb-1">
                                    Avg Duration
                                </div>
                                <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                                    {(orchestratorMetrics?.avg_duration_seconds || 0).toFixed(1)}s
                                </div>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Cache Performance */}
                <Card className="p-6">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Zap className="text-amber-500" size={20} />
                        Cache Performance
                    </h3>

                    <div className="space-y-4">
                        {/* Cache Stats */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-xl border border-amber-100 dark:border-amber-800">
                                <div className="text-xs text-amber-600 dark:text-amber-400 mb-1">
                                    Total Steps
                                </div>
                                <div className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                                    {cacheMetrics?.total_steps || 0}
                                </div>
                            </div>
                            <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-xl border border-emerald-100 dark:border-emerald-800">
                                <div className="text-xs text-emerald-600 dark:text-emerald-400 mb-1">
                                    Cached Steps
                                </div>
                                <div className="text-3xl font-bold text-emerald-700 dark:text-emerald-300">
                                    {cacheMetrics?.cached_steps || 0}
                                </div>
                            </div>
                        </div>

                        {/* Cache Hit Rate Visualization */}
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                                    Cache Hit Rate
                                </span>
                                <span className="text-lg font-bold text-slate-900 dark:text-white">
                                    {(cacheHitRate * 100).toFixed(1)}%
                                </span>
                            </div>
                            <div className="relative h-8 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div
                                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-end px-3 transition-all duration-500"
                                    style={{ width: `${cacheHitRate * 100}%` }}
                                >
                                    {cacheHitRate > 0.1 && (
                                        <span className="text-xs font-bold text-white">
                                            {(cacheHitRate * 100).toFixed(0)}%
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Performance Impact */}
                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                            <div className="flex items-center gap-2 mb-2">
                                <TrendingUp size={16} className="text-blue-600" />
                                <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                                    Performance Impact
                                </span>
                            </div>
                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                Cache saved approximately{' '}
                                <strong>{cacheMetrics?.cached_steps || 0}</strong> step executions,
                                improving pipeline efficiency.
                            </p>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}

function MetricCard({ icon, label, value, color, trend }) {
    const colorClasses = {
        blue: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
        emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400",
        purple: "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400",
        amber: "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400",
    };

    const trendColors = {
        positive: "text-emerald-600 dark:text-emerald-400",
        neutral: "text-amber-600 dark:text-amber-400",
        negative: "text-rose-600 dark:text-rose-400",
    };

    return (
        <Card className="hover:shadow-lg transition-shadow duration-200">
            <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
                    {icon}
                </div>
                <div className="flex-1">
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{label}</p>
                    <div className="flex items-baseline gap-2">
                        <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
                        {trend && (
                            <TrendingUp
                                size={16}
                                className={`${trendColors[trend]} ${trend === 'negative' ? 'rotate-180' : ''}`}
                            />
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}
