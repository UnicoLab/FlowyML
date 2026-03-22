import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { Link } from 'react-router-dom';
import { PlayCircle, Package, GitBranch, TrendingUp, Activity, Clock, CheckCircle, CheckCircle2, XCircle, Loader2, Zap, ArrowRight, Database, Layers, MessageSquare, DollarSign, Hash } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { StatusBadge } from '../../components/ui/ExecutionStatus';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import { useProject } from '../../contexts/ProjectContext';
import { useToast } from '../../contexts/ToastContext';

export function Dashboard() {
    const [stats, setStats] = useState(null);
    const [recentRuns, setRecentRuns] = useState([]);
    const [genaiStats, setGenaiStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { selectedProject } = useProject();
    const toast = useToast();

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const statsUrl = selectedProject
                    ? `/api/stats?project=${encodeURIComponent(selectedProject)}`
                    : '/api/stats';
                const runsUrl = selectedProject
                    ? `/api/runs/?limit=5&project=${encodeURIComponent(selectedProject)}`
                    : '/api/runs/?limit=5';

                const [statsRes, runsRes] = await Promise.all([
                    fetchApi(statsUrl),
                    fetchApi(runsUrl)
                ]);

                // Fetch GenAI trace stats (non-blocking)
                fetchApi('/api/traces/stats').then(async (res) => {
                    if (res.ok) setGenaiStats(await res.json());
                }).catch(() => {});

                if (!statsRes.ok) throw new Error(`Failed to fetch stats: ${statsRes.statusText}`);
                if (!runsRes.ok) throw new Error(`Failed to fetch runs: ${runsRes.statusText}`);

                const statsData = await statsRes.json();
                const runsData = await runsRes.json();

                setStats(statsData);
                setRecentRuns(runsData.runs || []);
            } catch (err) {
                console.error(err);
                setError(err.message);
                toast.error(`Failed to load dashboard: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [selectedProject]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center p-8 bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-100 dark:border-red-800 max-w-md">
                    <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-red-700 dark:text-red-300 mb-2">Failed to load dashboard</h3>
                    <p className="text-red-600 dark:text-red-400 mb-6">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300 font-medium"
                    >
                        Retry Connection
                    </button>
                </div>
            </div>
        );
    }

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <motion.div
            initial="hidden"
            animate="show"
            variants={container}
            className="space-y-8"
        >
            {/* Welcome Header */}
            <motion.div variants={item} className="relative overflow-hidden bg-gradient-to-br from-primary-600 via-primary-700 to-purple-700 rounded-2xl p-8 text-white shadow-xl">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-32 -mt-32" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full -ml-24 -mb-24" />

                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-3">
                        <Zap size={32} className="text-yellow-300 drop-shadow-lg" />
                        <h1 className="text-4xl font-bold drop-shadow-md">Welcome to flowyml</h1>
                    </div>
                    <p className="text-white/90 text-lg max-w-2xl drop-shadow-sm">
                        Your lightweight, artifact-centric ML orchestration platform. Build, run, and track your ML pipelines with ease.
                    </p>
                    <div className="mt-6 flex gap-3">
                        <Link to="/pipelines">
                            <button className="px-6 py-2.5 bg-white text-primary-700 rounded-lg font-semibold hover:bg-primary-50 transition-colors shadow-lg">
                                View Pipelines
                            </button>
                        </Link>
                        <Link to="/runs">
                            <button className="px-6 py-2.5 bg-white/10 backdrop-blur-sm text-white rounded-lg font-semibold hover:bg-white/20 transition-colors border border-white/30 shadow-lg">
                                Recent Runs
                            </button>
                        </Link>
                    </div>
                </div>
            </motion.div>

            {/* Stats Grid */}
            <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<Layers size={24} />}
                    label="Total Pipelines"
                    value={stats?.pipelines || 0}
                    color="blue"
                />
                <MetricCard
                    icon={<Activity size={24} />}
                    label="Pipeline Runs"
                    value={stats?.runs || 0}
                    color="purple"
                />
                <MetricCard
                    icon={<Database size={24} />}
                    label="Artifacts"
                    value={stats?.artifacts || 0}
                    color="emerald"
                />
                <MetricCard
                    icon={<CheckCircle size={24} />}
                    label="Success Rate"
                    value={stats?.runs > 0 ? `${Math.round((stats.completed_runs / stats.runs) * 100)}%` : '0%'}
                    color="cyan"
                />
            </motion.div>

            {/* GenAI Observability Card */}
            {genaiStats && (genaiStats.total_traces > 0) && (
                <motion.div variants={item}>
                    <Link to="/traces" className="block group">
                        <div className="relative overflow-hidden bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-shadow">
                            <div className="absolute top-0 right-0 w-40 h-40 bg-white/5 rounded-full -mr-20 -mt-20" />
                            <div className="relative z-10">
                                <div className="flex items-center gap-2 mb-4">
                                    <MessageSquare size={20} className="text-indigo-200" />
                                    <h3 className="text-sm font-semibold text-indigo-200 uppercase tracking-wider">GenAI Observability</h3>
                                    <ArrowRight size={14} className="text-indigo-300 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                                    <div>
                                        <p className="text-3xl font-bold">{genaiStats.total_traces?.toLocaleString() || 0}</p>
                                        <p className="text-xs text-indigo-200 mt-1">Total Traces</p>
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">{genaiStats.total_tokens ? (genaiStats.total_tokens > 999999 ? `${(genaiStats.total_tokens / 1000000).toFixed(1)}M` : genaiStats.total_tokens > 999 ? `${(genaiStats.total_tokens / 1000).toFixed(1)}K` : genaiStats.total_tokens) : '0'}</p>
                                        <p className="text-xs text-indigo-200 mt-1">Total Tokens</p>
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">${(genaiStats.total_cost || 0).toFixed(2)}</p>
                                        <p className="text-xs text-indigo-200 mt-1">Est. Cost</p>
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">{Object.keys(genaiStats.models || {}).length}</p>
                                        <p className="text-xs text-indigo-200 mt-1">Models Used</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Link>
                </motion.div>
            )}

            {/* Recent Activity */}
            <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Runs */}
                <div className="lg:col-span-2">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Clock className="text-primary-500" size={24} />
                            Recent Runs
                        </h3>
                        <Link to="/runs" className="text-sm font-semibold text-primary-600 hover:text-primary-700 flex items-center gap-1">
                            View All <ArrowRight size={16} />
                        </Link>
                    </div>

                    <div className="space-y-3">
                        {recentRuns.length > 0 ? (
                            recentRuns.map((run, index) => (
                                <RecentRunCard key={run.run_id} run={run} index={index} />
                            ))
                        ) : (
                            <Card className="p-12 text-center border-dashed">
                                <Activity className="mx-auto text-slate-300 mb-3" size={32} />
                                <p className="text-slate-500">No recent runs</p>
                            </Card>
                        )}
                    </div>
                </div>

                {/* Quick Stats */}
                <div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
                        <TrendingUp className="text-primary-500" size={24} />
                        Quick Stats
                    </h3>

                    <div className="space-y-3">
                        <QuickStatCard
                            label="Completed Today"
                            value={stats?.completed_runs || 0}
                            icon={<CheckCircle size={18} />}
                            color="emerald"
                        />
                        <QuickStatCard
                            label="Failed Runs"
                            value={stats?.failed_runs || 0}
                            icon={<XCircle size={18} />}
                            color="rose"
                        />
                        <QuickStatCard
                            label="Avg Duration"
                            value={stats?.avg_duration ? `${stats.avg_duration.toFixed(1)}s` : '0s'}
                            icon={<Clock size={18} />}
                            color="blue"
                        />
                        <QuickStatCard
                            label="Cache Hit Rate"
                            value={stats?.cache_hit_rate != null ? `${Math.round(stats.cache_hit_rate * 100)}%` : 'N/A'}
                            icon={<Zap size={18} />}
                            color="amber"
                        />
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

function MetricCard({ icon, label, value, color }) {
    const colorClasses = {
        blue: "from-blue-500 to-cyan-500",
        purple: "from-purple-500 to-pink-500",
        emerald: "from-emerald-500 to-teal-500",
        cyan: "from-cyan-500 to-blue-500"
    };

    return (
        <Card className="relative overflow-hidden group hover:shadow-lg transition-all duration-200">
            <div className={`absolute inset-0 bg-gradient-to-br ${colorClasses[color]} opacity-0 group-hover:opacity-5 transition-opacity`} />

            <div className="relative">
                <div className="flex items-start justify-between mb-4">
                    <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[color]} text-white shadow-lg`}>
                        {icon}
                    </div>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium mb-1">{label}</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
            </div>
        </Card>
    );
}

function RecentRunCard({ run, index }) {
    const statusConfig = {
        completed: { icon: <CheckCircle size={16} />, color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
        failed: { icon: <XCircle size={16} />, color: 'text-rose-500', bg: 'bg-rose-50 dark:bg-rose-900/20' },
        running: { icon: <Activity size={16} className="animate-pulse" />, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/20' }
    };

    const config = statusConfig[run.status] || statusConfig.completed;

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
        >
            <Link to={`/runs/${run.run_id}`}>
                <Card className="group hover:shadow-md hover:border-primary-200 transition-all duration-200">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${config.bg} ${config.color}`}>
                            {config.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-slate-900 dark:text-white truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                                {run.pipeline_name}
                            </h4>
                            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                                <span className="font-mono">{run.run_id?.substring(0, 8) || 'N/A'}</span>
                                {run.start_time && (
                                    <>
                                        <span>•</span>
                                        <span>{format(new Date(run.start_time), 'MMM d, HH:mm')}</span>
                                    </>
                                )}
                            </div>
                        </div>
                        <Badge variant={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : 'warning'} className="text-xs">
                            {run.status}
                        </Badge>
                    </div>
                </Card>
            </Link>
        </motion.div>
    );
}

function QuickStatCard({ label, value, icon, color }) {
    const colorClasses = {
        emerald: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400",
        rose: "bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400",
        blue: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
        amber: "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400"
    };

    return (
        <Card className="hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium mb-1">{label}</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
                </div>
                <div className={`p-2.5 rounded-lg ${colorClasses[color]}`}>
                    {icon}
                </div>
            </div>
        </Card>
    );
}
