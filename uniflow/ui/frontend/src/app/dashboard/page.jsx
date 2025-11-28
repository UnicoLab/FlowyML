import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import { Link } from 'react-router-dom';
import { Activity, Layers, Database, TrendingUp, Clock, CheckCircle, XCircle, Zap, ArrowRight } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import { useProject } from '../../contexts/ProjectContext';

export function Dashboard() {
    const [stats, setStats] = useState(null);
    const [recentRuns, setRecentRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const statsUrl = selectedProject
                    ? `/api/stats?project=${encodeURIComponent(selectedProject)}`
                    : '/api/stats';
                const runsUrl = selectedProject
                    ? `/api/runs?limit=5&project=${encodeURIComponent(selectedProject)}`
                    : '/api/runs?limit=5';

                const [statsData, runsData] = await Promise.all([
                    fetchApi(statsUrl).then(res => res.json()),
                    fetchApi(runsUrl).then(res => res.json())
                ]);

                setStats(statsData);
                setRecentRuns(runsData.runs || []);
            } catch (err) {
                console.error(err);
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
            <motion.div variants={item} className="relative overflow-hidden bg-gradient-to-br from-primary-500 via-primary-600 to-purple-600 rounded-2xl p-8 text-white shadow-xl">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full -ml-24 -mb-24" />

                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-3">
                        <Zap size={32} className="text-yellow-300" />
                        <h1 className="text-4xl font-bold">Welcome to UniFlow</h1>
                    </div>
                    <p className="text-primary-100 text-lg max-w-2xl">
                        Your lightweight, artifact-centric ML orchestration platform. Build, run, and track your ML pipelines with ease.
                    </p>
                    <div className="mt-6 flex gap-3">
                        <Link to="/pipelines">
                            <button className="px-6 py-2.5 bg-white text-primary-600 rounded-lg font-semibold hover:bg-primary-50 transition-colors shadow-lg">
                                View Pipelines
                            </button>
                        </Link>
                        <Link to="/runs">
                            <button className="px-6 py-2.5 bg-primary-700/50 backdrop-blur-sm text-white rounded-lg font-semibold hover:bg-primary-700/70 transition-colors border border-white/20">
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
                    trend="+12%"
                    color="blue"
                />
                <MetricCard
                    icon={<Activity size={24} />}
                    label="Pipeline Runs"
                    value={stats?.runs || 0}
                    trend="+23%"
                    color="purple"
                />
                <MetricCard
                    icon={<Database size={24} />}
                    label="Artifacts"
                    value={stats?.artifacts || 0}
                    trend="+8%"
                    color="emerald"
                />
                <MetricCard
                    icon={<CheckCircle size={24} />}
                    label="Success Rate"
                    value={stats?.runs > 0 ? `${Math.round((stats.completed_runs / stats.runs) * 100)}%` : '0%'}
                    trend="+5%"
                    color="cyan"
                />
            </motion.div>

            {/* Recent Activity */}
            <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Runs */}
                <div className="lg:col-span-2">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
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
                    <h3 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
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
                            value="87%"
                            icon={<Zap size={18} />}
                            color="amber"
                        />
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

function MetricCard({ icon, label, value, trend, color }) {
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
                    <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                        {trend}
                    </span>
                </div>
                <p className="text-sm text-slate-500 font-medium mb-1">{label}</p>
                <p className="text-3xl font-bold text-slate-900">{value}</p>
            </div>
        </Card>
    );
}

function RecentRunCard({ run, index }) {
    const statusConfig = {
        completed: { icon: <CheckCircle size={16} />, color: 'text-emerald-500', bg: 'bg-emerald-50' },
        failed: { icon: <XCircle size={16} />, color: 'text-rose-500', bg: 'bg-rose-50' },
        running: { icon: <Activity size={16} className="animate-pulse" />, color: 'text-amber-500', bg: 'bg-amber-50' }
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
                            <h4 className="font-semibold text-slate-900 truncate group-hover:text-primary-600 transition-colors">
                                {run.pipeline_name}
                            </h4>
                            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                                <span className="font-mono">{run.run_id.substring(0, 8)}</span>
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
        emerald: "bg-emerald-50 text-emerald-600",
        rose: "bg-rose-50 text-rose-600",
        blue: "bg-blue-50 text-blue-600",
        amber: "bg-amber-50 text-amber-600"
    };

    return (
        <Card className="hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-slate-500 font-medium mb-1">{label}</p>
                    <p className="text-2xl font-bold text-slate-900">{value}</p>
                </div>
                <div className={`p-2.5 rounded-lg ${colorClasses[color]}`}>
                    {icon}
                </div>
            </div>
        </Card>
    );
}
