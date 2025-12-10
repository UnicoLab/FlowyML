import React, { useMemo, useState } from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
} from 'recharts';
import {
    Database,
    BarChart3,
    Table,
    Hash,
    Type,
    Calendar,
    AlertTriangle,
    ChevronDown,
    ChevronRight,
    Eye,
    Columns,
    Rows,
    Info,
    Activity,
    PieChart as PieChartIcon,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Color palette for charts
const COLORS = [
    '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

// Custom tooltip for histograms
const HistogramTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white/95 backdrop-blur-lg p-3 rounded-lg shadow-xl border border-slate-200/50">
                <p className="font-medium text-slate-900 text-sm">{label}</p>
                <p className="text-primary-600 text-sm font-mono">
                    Count: <span className="font-bold">{payload[0].value}</span>
                </p>
            </div>
        );
    }
    return null;
};

// Statistic card component
function StatCard({ icon: Icon, label, value, subValue, color = 'blue' }) {
    const colorClasses = {
        blue: 'from-blue-500 to-blue-600',
        purple: 'from-purple-500 to-purple-600',
        emerald: 'from-emerald-500 to-emerald-600',
        amber: 'from-amber-500 to-amber-600',
        rose: 'from-rose-500 to-rose-600',
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 hover:shadow-md transition-shadow"
        >
            <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-gradient-to-br ${colorClasses[color]} shadow-sm`}>
                    <Icon size={16} className="text-white" />
                </div>
                <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
                    <p className="text-lg font-bold text-slate-900 dark:text-white font-mono">{value}</p>
                    {subValue && (
                        <p className="text-xs text-slate-400 dark:text-slate-500">{subValue}</p>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

// Column card with expandable histogram
function ColumnCard({ column, index, data }) {
    const [expanded, setExpanded] = useState(false);
    const color = COLORS[index % COLORS.length];

    // Calculate statistics for numeric columns
    const stats = useMemo(() => {
        if (!data || !column.values) return null;

        const values = column.values.filter(v => v !== null && v !== undefined && !isNaN(v));
        if (values.length === 0) return null;

        const numericValues = values.map(Number).filter(v => !isNaN(v));
        if (numericValues.length === 0) return null;

        const sum = numericValues.reduce((a, b) => a + b, 0);
        const mean = sum / numericValues.length;
        const sorted = [...numericValues].sort((a, b) => a - b);
        const min = sorted[0];
        const max = sorted[sorted.length - 1];
        const median = sorted[Math.floor(sorted.length / 2)];
        const variance = numericValues.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / numericValues.length;
        const std = Math.sqrt(variance);

        return { mean, min, max, median, std, count: numericValues.length };
    }, [column, data]);

    // Generate histogram data
    const histogramData = useMemo(() => {
        if (!stats || !column.values) return [];

        const values = column.values.map(Number).filter(v => !isNaN(v));
        const binCount = Math.min(20, Math.max(5, Math.ceil(Math.sqrt(values.length))));
        const range = stats.max - stats.min;
        const binSize = range / binCount || 1;

        const bins = Array(binCount).fill(0).map((_, i) => ({
            range: `${(stats.min + i * binSize).toFixed(2)}`,
            count: 0,
        }));

        values.forEach(v => {
            const binIndex = Math.min(Math.floor((v - stats.min) / binSize), binCount - 1);
            if (binIndex >= 0 && binIndex < binCount) {
                bins[binIndex].count++;
            }
        });

        return bins;
    }, [column, stats]);

    const isNumeric = stats !== null;
    const uniqueCount = column.values ? new Set(column.values).size : 0;
    const nullCount = column.values ? column.values.filter(v => v === null || v === undefined || v === '').length : 0;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
            {/* Column Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: color }}
                    />
                    <div className="text-left">
                        <h4 className="font-semibold text-slate-900 dark:text-white">{column.name}</h4>
                        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                            <span className="flex items-center gap-1">
                                {isNumeric ? <Hash size={10} /> : <Type size={10} />}
                                {isNumeric ? 'Numeric' : 'Categorical'}
                            </span>
                            <span>•</span>
                            <span>{uniqueCount} unique</span>
                            {nullCount > 0 && (
                                <>
                                    <span>•</span>
                                    <span className="text-amber-600 flex items-center gap-1">
                                        <AlertTriangle size={10} />
                                        {nullCount} null
                                    </span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
                {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </button>

            {/* Expanded Content */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 pt-0 border-t border-slate-100 dark:border-slate-700">
                            {isNumeric && stats && (
                                <>
                                    {/* Statistics Grid */}
                                    <div className="grid grid-cols-3 gap-2 mb-4">
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Mean</p>
                                            <p className="font-mono font-bold text-slate-900 dark:text-white">
                                                {stats.mean.toFixed(4)}
                                            </p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Std Dev</p>
                                            <p className="font-mono font-bold text-slate-900 dark:text-white">
                                                {stats.std.toFixed(4)}
                                            </p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Median</p>
                                            <p className="font-mono font-bold text-slate-900 dark:text-white">
                                                {stats.median.toFixed(4)}
                                            </p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Min</p>
                                            <p className="font-mono font-bold text-emerald-600">
                                                {stats.min.toFixed(4)}
                                            </p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Max</p>
                                            <p className="font-mono font-bold text-rose-600">
                                                {stats.max.toFixed(4)}
                                            </p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-2 text-center">
                                            <p className="text-xs text-slate-500">Count</p>
                                            <p className="font-mono font-bold text-slate-900 dark:text-white">
                                                {stats.count}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Histogram */}
                                    <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3">
                                        <h5 className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2 flex items-center gap-1">
                                            <BarChart3 size={12} /> Distribution
                                        </h5>
                                        <ResponsiveContainer width="100%" height={120}>
                                            <BarChart data={histogramData}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />
                                                <XAxis
                                                    dataKey="range"
                                                    tick={{ fontSize: 9 }}
                                                    tickLine={false}
                                                    interval="preserveStartEnd"
                                                />
                                                <YAxis tick={{ fontSize: 9 }} tickLine={false} width={30} />
                                                <Tooltip content={<HistogramTooltip />} />
                                                <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </>
                            )}

                            {!isNumeric && column.values && (
                                <CategoricalDistribution values={column.values} color={color} />
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// Categorical distribution component
function CategoricalDistribution({ values, color }) {
    const distribution = useMemo(() => {
        const counts = {};
        values.forEach(v => {
            const key = v === null || v === undefined ? '(null)' : String(v);
            counts[key] = (counts[key] || 0) + 1;
        });

        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([name, count], idx) => ({
                name: name.length > 15 ? name.substring(0, 15) + '...' : name,
                count,
                fill: COLORS[idx % COLORS.length],
            }));
    }, [values]);

    return (
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3">
            <h5 className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2 flex items-center gap-1">
                <PieChartIcon size={12} /> Top Values
            </h5>
            <ResponsiveContainer width="100%" height={150}>
                <BarChart data={distribution} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />
                    <XAxis type="number" tick={{ fontSize: 9 }} />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 9 }} width={80} />
                    <Tooltip content={<HistogramTooltip />} />
                    <Bar dataKey="count" radius={[0, 2, 2, 0]}>
                        {distribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

// Sample data table
function SampleDataTable({ data, columns, maxRows = 10 }) {
    if (!data || !columns || columns.length === 0) return null;

    const sampleData = data.slice(0, maxRows);

    return (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
            <table className="w-full text-xs">
                <thead className="bg-slate-100 dark:bg-slate-800">
                    <tr>
                        <th className="px-3 py-2 text-left text-slate-600 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                            #
                        </th>
                        {columns.map((col, idx) => (
                            <th
                                key={idx}
                                className="px-3 py-2 text-left text-slate-600 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700"
                            >
                                {col}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {sampleData.map((row, rowIdx) => (
                        <tr
                            key={rowIdx}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                        >
                            <td className="px-3 py-2 text-slate-400 border-b border-slate-100 dark:border-slate-800 font-mono">
                                {rowIdx + 1}
                            </td>
                            {columns.map((col, colIdx) => (
                                <td
                                    key={colIdx}
                                    className="px-3 py-2 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800 font-mono"
                                >
                                    {row[col] === null || row[col] === undefined ? (
                                        <span className="text-slate-400 italic">null</span>
                                    ) : typeof row[col] === 'number' ? (
                                        row[col].toFixed(4)
                                    ) : (
                                        String(row[col]).substring(0, 30)
                                    )}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
            {data.length > maxRows && (
                <div className="px-3 py-2 text-center text-xs text-slate-500 bg-slate-50 dark:bg-slate-900">
                    Showing {maxRows} of {data.length} rows
                </div>
            )}
        </div>
    );
}

// Helper to safely parse Python-style dict strings
function parsePythonDict(str) {
    if (!str || typeof str !== 'string') return null;
    try {
        // Replace Python-style quotes and booleans
        let jsonStr = str
            .replace(/'/g, '"')  // Replace single quotes with double quotes
            .replace(/True/g, 'true')
            .replace(/False/g, 'false')
            .replace(/None/g, 'null');
        return JSON.parse(jsonStr);
    } catch (e) {
        console.warn('Failed to parse data string:', e);
        return null;
    }
}

// Normalize different dataset formats (pandas, tensorflow, numpy, etc.)
function normalizeDatasetFormat(data) {
    if (!data) return null;

    // Already in the expected format {features: {...}, target: [...]}
    if (data.features && typeof data.features === 'object') {
        return data;
    }

    // TensorFlow dataset metadata format
    // Often stored as: {element_spec: {...}, cardinality: N, ...}
    if (data.element_spec || data.cardinality !== undefined) {
        return {
            _tf_dataset: true,
            element_spec: data.element_spec,
            cardinality: data.cardinality,
            ...data
        };
    }

    // Pandas DataFrame format: {columns: [...], data: [[...], ...], index: [...]}
    if (data.columns && Array.isArray(data.columns) && data.data && Array.isArray(data.data)) {
        const features = {};
        data.columns.forEach((col, idx) => {
            features[col] = data.data.map(row => row[idx]);
        });
        return { features, target: [] };
    }

    // Numpy array format: {shape: [...], dtype: '...', data: [...]}
    if (data.shape && data.dtype && Array.isArray(data.data)) {
        // Single feature array
        return {
            features: { values: data.data.flat() },
            target: []
        };
    }

    // Dict of arrays format: {col1: [...], col2: [...]}
    if (typeof data === 'object' && !Array.isArray(data)) {
        const keys = Object.keys(data);
        const firstVal = data[keys[0]];
        if (Array.isArray(firstVal)) {
            // Treat last column as target if it's named 'target', 'label', or 'y'
            const targetKeys = ['target', 'label', 'y', 'labels', 'targets'];
            const targetKey = keys.find(k => targetKeys.includes(k.toLowerCase()));
            const featureKeys = keys.filter(k => k !== targetKey);

            const features = {};
            featureKeys.forEach(k => {
                features[k] = data[k];
            });

            return {
                features,
                target: targetKey ? data[targetKey] : []
            };
        }
    }

    return null;
}

// Main DatasetViewer component
export function DatasetViewer({ artifact }) {
    const [activeTab, setActiveTab] = useState('overview');

    // Parse dataset information from artifact
    const datasetInfo = useMemo(() => {
        if (!artifact) return null;

        const props = artifact.properties || {};

        // Data can be in multiple places:
        // 1. artifact.data (if already parsed by backend)
        // 2. props._full_data (full data stored in properties)
        // 3. artifact.value (string that needs parsing - may be truncated!)
        // 4. props.data
        let rawData = artifact.data || props._full_data || props.data;

        // If data is not found, try parsing the value field
        if (!rawData && artifact.value) {
            rawData = parsePythonDict(artifact.value);
        }

        // Normalize the data format (handles pandas, tensorflow, numpy, etc.)
        const data = normalizeDatasetFormat(rawData);

        // Handle TensorFlow dataset metadata (no actual data, just specs)
        if (data && data._tf_dataset) {
            return {
                name: artifact.name || 'Dataset',
                numSamples: data.cardinality || props.num_samples || props.samples || 'Unknown',
                numFeatures: props.num_features || 0,
                featureColumns: props.feature_columns || [],
                columns: [],
                columnNames: [],
                samples: [],
                source: props.source || 'TensorFlow Dataset',
                createdAt: artifact.created_at,
                isTensorFlow: true,
                elementSpec: data.element_spec,
                tfMetadata: data,
            };
        }

        // If still no data, return basic info
        if (!data || typeof data !== 'object') {
            return {
                name: artifact.name || 'Dataset',
                numSamples: props.num_samples || props.samples || props.cardinality || 0,
                numFeatures: props.num_features || (props.feature_columns?.length || 0),
                featureColumns: props.feature_columns || [],
                columns: [],
                columnNames: [],
                samples: [],
                source: props.source,
                createdAt: artifact.created_at,
            };
        }

        // Try to extract features and target
        let features = data.features || {};
        let target = data.target || [];
        let samples = [];
        let columnNames = [];
        let columns = [];

        // If features is an object with column arrays
        if (features && typeof features === 'object' && !Array.isArray(features)) {
            columnNames = Object.keys(features);
            const numRows = features[columnNames[0]]?.length || 0;

            // Build row-based samples for table view
            for (let i = 0; i < numRows; i++) {
                const row = {};
                columnNames.forEach(col => {
                    row[col] = features[col]?.[i];
                });
                if (Array.isArray(target) && target.length > i) {
                    row['target'] = target[i];
                }
                samples.push(row);
            }

            // Build column info for statistics
            columnNames.forEach(col => {
                columns.push({
                    name: col,
                    values: features[col] || [],
                });
            });

            // Add target column if exists
            if (Array.isArray(target) && target.length > 0) {
                columnNames.push('target');
                columns.push({
                    name: 'target',
                    values: target,
                });
            }
        }

        return {
            name: artifact.name || 'Dataset',
            numSamples: props.num_samples || props.samples || samples.length,
            numFeatures: props.num_features || columnNames.length - (Array.isArray(target) && target.length > 0 ? 1 : 0),
            featureColumns: props.feature_columns || columnNames.filter(c => c !== 'target'),
            columns,
            columnNames,
            samples,
            source: props.source,
            createdAt: artifact.created_at,
        };
    }, [artifact]);

    if (!datasetInfo) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-slate-400">
                <Database size={32} className="mb-2 opacity-50" />
                <p className="text-sm">No dataset information available</p>
            </div>
        );
    }

    // Special view for TensorFlow datasets (show metadata/specs instead of data)
    if (datasetInfo.isTensorFlow) {
        return (
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
                    <div className="p-3 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl shadow-lg">
                        <Database size={24} className="text-white" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">{datasetInfo.name}</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            TensorFlow Dataset • {datasetInfo.numSamples} samples
                        </p>
                    </div>
                </div>

                {/* TF Dataset Info */}
                <div className="bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-xl p-6 border border-orange-200 dark:border-orange-800">
                    <h4 className="font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Activity size={18} className="text-orange-600" />
                        TensorFlow Dataset Metadata
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Cardinality</p>
                            <p className="text-lg font-bold text-slate-900 dark:text-white font-mono">
                                {datasetInfo.numSamples}
                            </p>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Source</p>
                            <p className="text-lg font-bold text-slate-900 dark:text-white">
                                {datasetInfo.source}
                            </p>
                        </div>
                    </div>
                    {datasetInfo.elementSpec && (
                        <div className="mt-4 bg-white dark:bg-slate-800 p-4 rounded-lg">
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Element Spec</p>
                            <pre className="text-xs font-mono text-slate-700 dark:text-slate-300 overflow-x-auto">
                                {JSON.stringify(datasetInfo.elementSpec, null, 2)}
                            </pre>
                        </div>
                    )}
                    <p className="text-xs text-slate-500 mt-4 italic">
                        💡 TensorFlow datasets are lazy-loaded. Full data visualization requires materializing the dataset.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
                <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                    <Database size={24} className="text-white" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">{datasetInfo.name}</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Dataset with {datasetInfo.numSamples} samples, {datasetInfo.numFeatures} features
                    </p>
                </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                    icon={Rows}
                    label="Samples"
                    value={datasetInfo.numSamples?.toLocaleString() || '—'}
                    color="blue"
                />
                <StatCard
                    icon={Columns}
                    label="Features"
                    value={datasetInfo.numFeatures || '—'}
                    color="purple"
                />
                <StatCard
                    icon={Hash}
                    label="Columns"
                    value={datasetInfo.columnNames.length}
                    color="emerald"
                />
                <StatCard
                    icon={Info}
                    label="Source"
                    value={datasetInfo.source || 'Pipeline'}
                    color="amber"
                />
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
                <button
                    onClick={() => setActiveTab('overview')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                        activeTab === 'overview'
                            ? 'text-primary-600 border-b-2 border-primary-600'
                            : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                    <BarChart3 size={14} className="inline mr-1" />
                    Column Statistics
                </button>
                <button
                    onClick={() => setActiveTab('sample')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                        activeTab === 'sample'
                            ? 'text-primary-600 border-b-2 border-primary-600'
                            : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                    <Table size={14} className="inline mr-1" />
                    Sample Data
                </button>
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'overview' && (
                    <motion.div
                        key="overview"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="space-y-3"
                    >
                        {datasetInfo.columns.length > 0 ? (
                            datasetInfo.columns.map((column, idx) => (
                                <ColumnCard
                                    key={column.name}
                                    column={column}
                                    index={idx}
                                    data={datasetInfo.samples}
                                />
                            ))
                        ) : (
                            <div className="text-center py-8 text-slate-400">
                                <BarChart3 size={32} className="mx-auto mb-2 opacity-50" />
                                <p className="text-sm">Column statistics not available</p>
                                <p className="text-xs text-slate-500 mt-1">
                                    Data structure may not support detailed analysis
                                </p>
                            </div>
                        )}
                    </motion.div>
                )}

                {activeTab === 'sample' && (
                    <motion.div
                        key="sample"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                    >
                        {datasetInfo.samples.length > 0 ? (
                            <SampleDataTable
                                data={datasetInfo.samples}
                                columns={datasetInfo.columnNames}
                                maxRows={15}
                            />
                        ) : (
                            <div className="text-center py-8 text-slate-400">
                                <Table size={32} className="mx-auto mb-2 opacity-50" />
                                <p className="text-sm">Sample data not available</p>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default DatasetViewer;
