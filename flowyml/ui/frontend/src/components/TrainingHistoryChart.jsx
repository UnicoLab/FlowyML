import React, { useMemo, useState, useCallback } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Area,
    AreaChart,
    Brush,
    ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, Target, Zap, Activity, Eye, EyeOff, ZoomIn, ZoomOut, Maximize2, BarChart3 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Beautiful color palette for dynamic metric assignment
const METRIC_COLORS = [
    { main: '#3b82f6', light: '#93c5fd' },  // blue
    { main: '#8b5cf6', light: '#c4b5fd' },  // purple
    { main: '#10b981', light: '#6ee7b7' },  // emerald
    { main: '#f59e0b', light: '#fcd34d' },  // amber
    { main: '#ef4444', light: '#fca5a5' },  // red
    { main: '#ec4899', light: '#f9a8d4' },  // pink
    { main: '#06b6d4', light: '#67e8f9' },  // cyan
    { main: '#84cc16', light: '#bef264' },  // lime
];

// Custom tooltip with glassmorphism effect
const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white/95 backdrop-blur-lg p-4 rounded-xl shadow-2xl border border-slate-200/50 max-w-xs"
            >
                <p className="font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <Target size={14} className="text-primary-500" />
                    Epoch {label}
                </p>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {payload.map((entry, index) => (
                        <div key={index} className="flex items-center justify-between gap-4">
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: entry.color }}
                                />
                                <span className="text-sm text-slate-600 truncate">{entry.name}</span>
                            </div>
                            <span className="text-sm font-mono font-bold text-slate-900">
                                {typeof entry.value === 'number' ? entry.value.toExponential(4) : entry.value}
                            </span>
                        </div>
                    ))}
                </div>
            </motion.div>
        );
    }
    return null;
};

// Animated metric card
function MetricCard({ icon: Icon, label, value, trend, color, subValue }) {
    const isPositive = trend === 'up';
    const TrendIcon = isPositive ? TrendingUp : TrendingDown;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02, y: -2 }}
            className="relative overflow-hidden p-4 bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300"
        >
            <div
                className="absolute top-0 right-0 w-24 h-24 rounded-full blur-2xl opacity-20"
                style={{ backgroundColor: color }}
            />
            <div className="relative">
                <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20` }}>
                        <Icon size={16} style={{ color }} />
                    </div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                        {label}
                    </span>
                </div>
                <div className="flex items-end justify-between">
                    <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                        {typeof value === 'number' ? value.toFixed(4) : value}
                    </span>
                    {trend && (
                        <div className={`flex items-center gap-1 text-xs ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                            <TrendIcon size={12} />
                            <span className="font-medium">{isPositive ? 'Improving' : 'Degrading'}</span>
                        </div>
                    )}
                </div>
                {subValue && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{subValue}</p>
                )}
            </div>
        </motion.div>
    );
}

// Scale selector component
function ScaleSelector({ scale, onChange }) {
    return (
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
            {['linear', 'log'].map((s) => (
                <button
                    key={s}
                    onClick={() => onChange(s)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                        scale === s
                            ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                    }`}
                >
                    {s === 'log' ? 'Log' : 'Linear'}
                </button>
            ))}
        </div>
    );
}

// Metric toggle button
function MetricToggle({ metric, color, visible, onToggle }) {
    return (
        <button
            onClick={onToggle}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                visible
                    ? 'bg-white dark:bg-slate-700 shadow-sm border border-slate-200 dark:border-slate-600'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
            }`}
        >
            <div
                className={`w-3 h-3 rounded-full transition-opacity ${visible ? 'opacity-100' : 'opacity-30'}`}
                style={{ backgroundColor: color }}
            />
            <span className={visible ? 'text-slate-700 dark:text-slate-200' : ''}>{metric}</span>
            {visible ? <Eye size={12} /> : <EyeOff size={12} />}
        </button>
    );
}

// Group metrics by type
function groupMetrics(metrics) {
    const groups = {
        loss: { train: [], val: [] },
        accuracy: { train: [], val: [] },
        other: { train: [], val: [] },
    };

    metrics.forEach(metric => {
        const isVal = metric.startsWith('val_');
        const baseName = isVal ? metric.replace('val_', '') : metric.replace('train_', '');
        const side = isVal ? 'val' : 'train';

        if (baseName.includes('loss') || baseName.includes('mse') || baseName.includes('mae') || baseName.includes('error')) {
            groups.loss[side].push(metric);
        } else if (baseName.includes('accuracy') || baseName.includes('acc') || baseName.includes('f1') || baseName.includes('precision') || baseName.includes('recall')) {
            groups.accuracy[side].push(metric);
        } else {
            groups.other[side].push(metric);
        }
    });

    return groups;
}

// Format metric name for display
function formatMetricName(name) {
    return name
        .replace('train_', 'Train ')
        .replace('val_', 'Val ')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

// Interactive Chart Component with zoom, pan, scale, and visibility controls
function InteractiveChart({
    data,
    metrics,
    title,
    icon,
    iconColor,
    compact = false,
    defaultScale = 'linear',
    isLossLike = true,
}) {
    const [scale, setScale] = useState(defaultScale);
    const [visibleMetrics, setVisibleMetrics] = useState(() =>
        metrics.reduce((acc, m) => ({ ...acc, [m]: true }), {})
    );
    const [brushRange, setBrushRange] = useState(null);
    const [isExpanded, setIsExpanded] = useState(false);

    const toggleMetric = useCallback((metric) => {
        setVisibleMetrics(prev => ({ ...prev, [metric]: !prev[metric] }));
    }, []);

    // Transform data for log scale (add small offset to avoid log(0))
    const transformedData = useMemo(() => {
        if (scale !== 'log') return data;
        return data.map(point => {
            const newPoint = { ...point };
            metrics.forEach(metric => {
                const displayName = formatMetricName(metric);
                if (newPoint[displayName] !== undefined && newPoint[displayName] > 0) {
                    newPoint[displayName] = newPoint[displayName];
                } else if (newPoint[displayName] !== undefined) {
                    newPoint[displayName] = 1e-10; // Small value for log scale
                }
            });
            return newPoint;
        });
    }, [data, metrics, scale]);

    const visibleMetricsList = metrics.filter(m => visibleMetrics[m]);
    const chartHeight = isExpanded ? 400 : (compact ? 200 : 300);

    if (metrics.length === 0) return null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden ${
                isExpanded ? 'col-span-full' : ''
            }`}
        >
            {/* Chart Header */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: iconColor }} />
                    <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">{title}</h4>
                    <span className="text-xs text-slate-400">({visibleMetricsList.length}/{metrics.length} shown)</span>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {/* Scale Selector */}
                    <ScaleSelector scale={scale} onChange={setScale} />

                    {/* Expand/Collapse Button */}
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="p-2 rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                        title={isExpanded ? 'Collapse' : 'Expand'}
                    >
                        <Maximize2 size={14} className="text-slate-600 dark:text-slate-300" />
                    </button>
                </div>
            </div>

            {/* Metric Toggles */}
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex flex-wrap gap-2">
                {metrics.map((metric, idx) => (
                    <MetricToggle
                        key={metric}
                        metric={formatMetricName(metric)}
                        color={METRIC_COLORS[idx % METRIC_COLORS.length].main}
                        visible={visibleMetrics[metric]}
                        onToggle={() => toggleMetric(metric)}
                    />
                ))}
            </div>

            {/* Chart */}
            <div className="p-4">
                <ResponsiveContainer width="100%" height={chartHeight}>
                    <AreaChart data={transformedData}>
                        <defs>
                            {metrics.map((metric, idx) => (
                                <linearGradient key={metric} id={`gradient-${metric}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={METRIC_COLORS[idx % METRIC_COLORS.length].main} stopOpacity={0.3} />
                                    <stop offset="95%" stopColor={METRIC_COLORS[idx % METRIC_COLORS.length].main} stopOpacity={0} />
                                </linearGradient>
                            ))}
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />
                        <XAxis
                            dataKey="epoch"
                            stroke="#94a3b8"
                            tick={{ fontSize: 11 }}
                            tickLine={false}
                            label={{ value: 'Epoch', position: 'insideBottom', offset: -5, fontSize: 11, fill: '#94a3b8' }}
                        />
                        <YAxis
                            stroke="#94a3b8"
                            tick={{ fontSize: 11 }}
                            tickLine={false}
                            scale={scale}
                            domain={scale === 'log' ? ['auto', 'auto'] : [0, 'auto']}
                            tickFormatter={(val) => {
                                if (val === 0) return '0';
                                if (Math.abs(val) < 0.001 || Math.abs(val) > 1000) {
                                    return val.toExponential(1);
                                }
                                return val.toFixed(3);
                            }}
                            label={{
                                value: scale === 'log' ? 'Value (log)' : 'Value',
                                angle: -90,
                                position: 'insideLeft',
                                fontSize: 11,
                                fill: '#94a3b8'
                            }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                            wrapperStyle={{ paddingTop: 10 }}
                            iconType="circle"
                            iconSize={8}
                        />

                        {/* Brush for zoom/pan */}
                        <Brush
                            dataKey="epoch"
                            height={30}
                            stroke="#94a3b8"
                            fill="#f1f5f9"
                            travellerWidth={10}
                        />

                        {metrics.map((metric, idx) => (
                            visibleMetrics[metric] && (
                                <Area
                                    key={metric}
                                    type="monotone"
                                    dataKey={formatMetricName(metric)}
                                    stroke={METRIC_COLORS[idx % METRIC_COLORS.length].main}
                                    strokeWidth={2}
                                    fill={`url(#gradient-${metric})`}
                                    dot={false}
                                    activeDot={{ r: 5, strokeWidth: 2, fill: 'white' }}
                                    animationDuration={500}
                                />
                            )
                        ))}
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Chart Footer with instructions */}
            <div className="px-4 py-2 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700">
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                            <ZoomIn size={12} /> Drag brush to zoom
                        </span>
                        <span className="flex items-center gap-1">
                            <Eye size={12} /> Click legend to toggle
                        </span>
                    </div>
                    <span>{data.length} data points</span>
                </div>
            </div>
        </motion.div>
    );
}

// Main Training History Chart Component
export function TrainingHistoryChart({ trainingHistory, title = "Training History", compact = false }) {
    const { chartData, metricGroups, allMetrics, summary } = useMemo(() => {
        if (!trainingHistory || !trainingHistory.epochs || trainingHistory.epochs.length === 0) {
            return { chartData: [], metricGroups: {}, allMetrics: [], summary: null };
        }

        const epochs = trainingHistory.epochs;
        const data = epochs.map((epoch, idx) => {
            const point = { epoch };
            Object.keys(trainingHistory).forEach(key => {
                if (key !== 'epochs' && trainingHistory[key]?.[idx] !== undefined) {
                    point[formatMetricName(key)] = trainingHistory[key][idx];
                }
            });
            return point;
        });

        const metrics = Object.keys(trainingHistory).filter(k => k !== 'epochs' && trainingHistory[k]?.length > 0);
        const groups = groupMetrics(metrics);

        const summaryData = {
            totalEpochs: epochs.length,
            metrics: {},
        };

        metrics.forEach(metric => {
            const values = trainingHistory[metric];
            if (!values || values.length === 0) return;

            const lastValue = values[values.length - 1];
            const isLossLike = metric.includes('loss') || metric.includes('mae') || metric.includes('mse') || metric.includes('error');
            const bestValue = isLossLike ? Math.min(...values) : Math.max(...values);

            summaryData.metrics[metric] = {
                final: lastValue,
                best: bestValue,
                isLossLike,
                trend: values.length > 1 ? (values[values.length - 1] < values[values.length - 2] ? 'down' : 'up') : null,
            };
        });

        return { chartData: data, metricGroups: groups, allMetrics: metrics, summary: summaryData };
    }, [trainingHistory]);

    // Don't render anything if no data
    if (chartData.length === 0) {
        return null; // Return null instead of placeholder - component won't show if no data
    }

    const lossMetrics = [...metricGroups.loss.train, ...metricGroups.loss.val];
    const accuracyMetrics = [...metricGroups.accuracy.train, ...metricGroups.accuracy.val];
    const otherMetrics = [...metricGroups.other.train, ...metricGroups.other.val];

    return (
        <div className="space-y-6">
            {/* Header with Summary Cards */}
            {!compact && summary && (
                <motion.div
                    initial="hidden"
                    animate="visible"
                    variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
                    }}
                    className="grid grid-cols-2 md:grid-cols-4 gap-4"
                >
                    <MetricCard
                        icon={Zap}
                        label="Epochs Trained"
                        value={summary.totalEpochs}
                        color={METRIC_COLORS[0].main}
                    />
                    {summary.metrics.val_loss && (
                        <MetricCard
                            icon={TrendingDown}
                            label="Best Val Loss"
                            value={summary.metrics.val_loss.best}
                            trend={summary.metrics.val_loss.trend}
                            color={METRIC_COLORS[1].main}
                        />
                    )}
                    {summary.metrics.val_mae && (
                        <MetricCard
                            icon={Target}
                            label="Best Val MAE"
                            value={summary.metrics.val_mae.best}
                            trend={summary.metrics.val_mae.trend}
                            color={METRIC_COLORS[4].main}
                        />
                    )}
                    {summary.metrics.val_accuracy && (
                        <MetricCard
                            icon={TrendingUp}
                            label="Best Val Accuracy"
                            value={summary.metrics.val_accuracy.best}
                            trend={summary.metrics.val_accuracy.trend}
                            color={METRIC_COLORS[2].main}
                        />
                    )}
                </motion.div>
            )}

            {/* Interactive Charts */}
            <div className={`grid gap-6 ${!compact && (lossMetrics.length > 0 && accuracyMetrics.length > 0) ? 'lg:grid-cols-2' : ''}`}>
                {lossMetrics.length > 0 && (
                    <InteractiveChart
                        data={chartData}
                        metrics={lossMetrics}
                        title="Loss & Error Metrics"
                        iconColor="#3b82f6"
                        compact={compact}
                        defaultScale="linear"
                        isLossLike={true}
                    />
                )}

                {accuracyMetrics.length > 0 && (
                    <InteractiveChart
                        data={chartData}
                        metrics={accuracyMetrics}
                        title="Accuracy & Score Metrics"
                        iconColor="#10b981"
                        compact={compact}
                        defaultScale="linear"
                        isLossLike={false}
                    />
                )}

                {otherMetrics.length > 0 && (
                    <InteractiveChart
                        data={chartData}
                        metrics={otherMetrics}
                        title="Additional Metrics"
                        iconColor="#06b6d4"
                        compact={compact}
                        defaultScale="linear"
                        isLossLike={true}
                    />
                )}
            </div>
        </div>
    );
}

export default TrainingHistoryChart;
