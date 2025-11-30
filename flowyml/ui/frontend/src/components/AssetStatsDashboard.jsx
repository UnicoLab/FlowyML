import React, { useEffect, useState } from 'react';
import { fetchApi } from '../utils/api';
import { Database, Box, BarChart2, FileText, TrendingUp, HardDrive, Activity, Package, ChevronDown } from 'lucide-react';
import { motion } from 'framer-motion';
import { Card } from './ui/Card';

const AnimatedCounter = ({ value, duration = 1000 }) => {
    const [count, setCount] = useState(0);

    useEffect(() => {
        let startTime;
        let animationFrame;

        const animate = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);

            setCount(Math.floor(progress * value));

            if (progress < 1) {
                animationFrame = requestAnimationFrame(animate);
            }
        };

        animationFrame = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animationFrame);
    }, [value, duration]);

    return <span>{count.toLocaleString()}</span>;
};

const StatCard = ({ icon: Icon, label, value, subtitle, gradient, isLoading }) => {
    if (isLoading) {
        return (
            <Card className="p-6 animate-pulse">
                <div className="h-20 bg-slate-200 dark:bg-slate-700 rounded"></div>
            </Card>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            <Card className="p-6 hover:shadow-xl transition-all duration-300 border-2 hover:border-primary-300 dark:hover:border-primary-700 group overflow-hidden relative">
                {/* Gradient background effect */}
                <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`}></div>

                <div className="relative">
                    <div className="flex items-start justify-between mb-3">
                        <div className={`p-3 rounded-xl bg-gradient-to-br ${gradient} text-white shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                            <Icon size={24} />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{label}</p>
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">
                            {typeof value === 'number' ? <AnimatedCounter value={value} /> : value}
                        </p>
                        {subtitle && (
                            <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
                        )}
                    </div>
                </div>
            </Card>
        </motion.div>
    );
};

const TypeBreakdownChart = ({ typeData }) => {
    const typeConfig = {
        model: { icon: Box, color: 'from-purple-500 to-pink-500', text: 'text-purple-600 dark:text-purple-400' },
        dataset: { icon: Database, color: 'from-blue-500 to-cyan-500', text: 'text-blue-600 dark:text-blue-400' },
        metrics: { icon: BarChart2, color: 'from-emerald-500 to-teal-500', text: 'text-emerald-600 dark:text-emerald-400' },
        default: { icon: FileText, color: 'from-slate-500 to-slate-600', text: 'text-slate-600 dark:text-slate-400' }
    };

    const total = Object.values(typeData).reduce((sum, count) => sum + count, 0);

    return (
        <div className="space-y-3">
            {Object.entries(typeData).map(([type, count]) => {
                const config = typeConfig[type.toLowerCase()] || typeConfig.default;
                const Icon = config.icon;
                const percentage = total > 0 ? (count / total) * 100 : 0;

                return (
                    <motion.div
                        key={type}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="group"
                    >
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                                <div className={`p-1.5 rounded-lg bg-gradient-to-br ${config.color} text-white`}>
                                    <Icon size={14} />
                                </div>
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{type}</span>
                            </div>
                            <span className="text-sm font-semibold text-slate-900 dark:text-white">{count}</span>
                        </div>
                        <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${percentage}%` }}
                                transition={{ duration: 0.8, ease: "easeOut" }}
                                className={`h-full bg-gradient-to-r ${config.color} group-hover:shadow-lg transition-shadow`}
                            />
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};

export function AssetStatsDashboard({ projectId }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showDistribution, setShowDistribution] = useState(false);
    const [showRecent, setShowRecent] = useState(false);

    useEffect(() => {
        const fetchStats = async () => {
            setLoading(true);
            try {
                const url = projectId
                    ? `/api/assets/stats?project=${encodeURIComponent(projectId)}`
                    : '/api/assets/stats';
                const res = await fetchApi(url);
                const data = await res.json();
                setStats(data);
            } catch (err) {
                console.error('Failed to fetch asset stats:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, [projectId]);

    const formatBytes = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="space-y-6">
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    icon={Package}
                    label="Total Assets"
                    value={stats?.total_assets || 0}
                    subtitle="Across all pipelines"
                    gradient="from-blue-500 to-cyan-500"
                    isLoading={loading}
                />
                <StatCard
                    icon={Box}
                    label="Models"
                    value={stats?.by_type?.model || stats?.by_type?.Model || 0}
                    subtitle="Trained models"
                    gradient="from-purple-500 to-pink-500"
                    isLoading={loading}
                />
                <StatCard
                    icon={Database}
                    label="Datasets"
                    value={stats?.by_type?.dataset || stats?.by_type?.Dataset || 0}
                    subtitle="Data artifacts"
                    gradient="from-emerald-500 to-teal-500"
                    isLoading={loading}
                />
                <StatCard
                    icon={HardDrive}
                    label="Storage Used"
                    value={stats ? formatBytes(stats.total_storage_bytes) : '0 MB'}
                    subtitle="Total size"
                    gradient="from-orange-500 to-red-500"
                    isLoading={loading}
                />
            </div>

            {/* Type Breakdown - Collapsible */}
            {stats && Object.keys(stats.by_type).length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <Card className="overflow-hidden">
                        <div
                            className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                            onClick={() => setShowDistribution(!showDistribution)}
                        >
                            <div className="flex items-center gap-2">
                                <TrendingUp className="text-primary-600" size={20} />
                                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Asset Distribution</h3>
                            </div>
                            <motion.div
                                animate={{ rotate: showDistribution ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <ChevronDown className="text-slate-400" size={20} />
                            </motion.div>
                        </div>
                        {showDistribution && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.2 }}
                                className="px-6 pb-6"
                            >
                                <TypeBreakdownChart typeData={stats.by_type} />
                            </motion.div>
                        )}
                    </Card>
                </motion.div>
            )}

            {/* Recent Activity - Collapsible */}
            {stats && stats.recent_assets && stats.recent_assets.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <Card className="overflow-hidden">
                        <div
                            className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                            onClick={() => setShowRecent(!showRecent)}
                        >
                            <div className="flex items-center gap-2">
                                <Activity className="text-primary-600" size={20} />
                                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Assets</h3>
                            </div>
                            <motion.div
                                animate={{ rotate: showRecent ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <ChevronDown className="text-slate-400" size={20} />
                            </motion.div>
                        </div>
                        {showRecent && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.2 }}
                                className="px-6 pb-6"
                            >
                                <div className="space-y-2">
                                    {stats.recent_assets.slice(0, 5).map((asset, idx) => {
                                        const typeConfig = {
                                            model: { icon: Box, color: 'text-purple-600' },
                                            Model: { icon: Box, color: 'text-purple-600' },
                                            dataset: { icon: Database, color: 'text-blue-600' },
                                            Dataset: { icon: Database, color: 'text-blue-600' },
                                            default: { icon: FileText, color: 'text-slate-600' }
                                        };
                                        const config = typeConfig[asset.type] || typeConfig.default;
                                        const Icon = config.icon;

                                        return (
                                            <motion.div
                                                key={asset.artifact_id || idx}
                                                initial={{ opacity: 0, x: -20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.05 }}
                                                className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                            >
                                                <Icon className={config.color} size={16} />
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                                                        {asset.name}
                                                    </p>
                                                    <p className="text-xs text-slate-500 dark:text-slate-400">
                                                        {asset.type} • {asset.step || 'N/A'}
                                                    </p>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            </motion.div>
                        )}
                    </Card>
                </motion.div>
            )}
        </div>
    );
}
