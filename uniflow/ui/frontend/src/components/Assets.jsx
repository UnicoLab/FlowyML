import React, { useEffect, useState } from 'react';
import { Database, Box, BarChart2, FileText, Search, Filter, Calendar, Package, Download, Eye, X } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

export function Assets() {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [typeFilter, setTypeFilter] = useState('all');
    const [selectedAsset, setSelectedAsset] = useState(null);

    useEffect(() => {
        fetch('/api/assets?limit=50')
            .then(res => res.json())
            .then(data => {
                setAssets(data.assets || []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    // Get unique types
    const types = ['all', ...new Set(assets.map(a => a.type))];

    // Filter assets
    const filteredAssets = assets.filter(asset => {
        const matchesSearch = asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.type.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = typeFilter === 'all' || asset.type === typeFilter;
        return matchesSearch && matchesType;
    });

    // Group by type
    const assetsByType = filteredAssets.reduce((acc, asset) => {
        const type = asset.type;
        if (!acc[type]) acc[type] = [];
        acc[type].push(asset);
        return acc;
    }, {});

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.05
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
            className="space-y-6"
        >
            {/* Header */}
            <motion.div variants={item}>
                <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-lg">
                        <Package className="text-white" size={24} />
                    </div>
                    <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Artifacts</h2>
                </div>
                <p className="text-slate-500 mt-2">Browse and manage pipeline artifacts and outputs</p>
            </motion.div>

            {/* Stats and Filters */}
            <motion.div variants={item} className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                {/* Search */}
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search artifacts..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                </div>

                {/* Type Filter */}
                <div className="flex items-center gap-2">
                    <Filter size={16} className="text-slate-400" />
                    <div className="flex gap-2">
                        {types.map(type => (
                            <button
                                key={type}
                                onClick={() => setTypeFilter(type)}
                                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${typeFilter === type
                                        ? 'bg-primary-500 text-white shadow-md'
                                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                    }`}
                            >
                                {type === 'all' ? 'All' : type}
                                {type !== 'all' && (
                                    <span className="ml-1.5 text-xs opacity-75">
                                        ({assets.filter(a => a.type === type).length})
                                    </span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            </motion.div>

            {/* Assets Grid */}
            {filteredAssets.length > 0 ? (
                <div className="space-y-8">
                    {Object.entries(assetsByType).map(([type, typeAssets]) => (
                        <motion.div key={type} variants={item}>
                            <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                                {getTypeIcon(type)}
                                {type}
                                <span className="text-sm font-normal text-slate-500">({typeAssets.length})</span>
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {typeAssets.map((asset, index) => (
                                    <AssetCard
                                        key={asset.artifact_id}
                                        asset={asset}
                                        index={index}
                                        onClick={() => setSelectedAsset(asset)}
                                    />
                                ))}
                            </div>
                        </motion.div>
                    ))}
                </div>
            ) : (
                <motion.div variants={item}>
                    <Card className="p-16 text-center border-dashed border-2">
                        <div className="mx-auto w-20 h-20 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
                            <Package className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">No artifacts found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            {searchTerm || typeFilter !== 'all'
                                ? 'Try adjusting your search or filters'
                                : 'Run a pipeline to generate artifacts'
                            }
                        </p>
                    </Card>
                </motion.div>
            )}

            {/* Asset Detail Modal */}
            <AssetDetailModal
                asset={selectedAsset}
                onClose={() => setSelectedAsset(null)}
            />
        </motion.div>
    );
}

function AssetCard({ asset, index, onClick }) {
    const typeConfig = {
        Dataset: { icon: <Database size={20} />, color: 'blue' },
        Model: { icon: <Box size={20} />, color: 'purple' },
        Metrics: { icon: <BarChart2 size={20} />, color: 'emerald' },
        default: { icon: <FileText size={20} />, color: 'slate' }
    };

    const config = typeConfig[asset.type] || typeConfig.default;

    const colorClasses = {
        blue: 'from-blue-500 to-cyan-500',
        purple: 'from-purple-500 to-pink-500',
        emerald: 'from-emerald-500 to-teal-500',
        slate: 'from-slate-500 to-slate-600'
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
        >
            <Card
                className="group cursor-pointer hover:shadow-xl hover:border-primary-300 transition-all duration-200 overflow-hidden"
                onClick={onClick}
            >
                {/* Icon Header */}
                <div className="flex items-start justify-between mb-3">
                    <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[config.color]} text-white shadow-lg group-hover:scale-110 transition-transform`}>
                        {config.icon}
                    </div>
                    <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                        <Eye size={16} className="text-slate-400" />
                    </button>
                </div>

                {/* Name */}
                <h4 className="font-bold text-slate-900 mb-1 truncate group-hover:text-primary-600 transition-colors">
                    {asset.name}
                </h4>

                {/* Metadata */}
                <div className="space-y-2 text-xs text-slate-500">
                    <div className="flex items-center justify-between">
                        <span>Step:</span>
                        <span className="font-mono text-slate-700 truncate ml-2">{asset.step}</span>
                    </div>
                    {asset.created_at && (
                        <div className="flex items-center justify-between">
                            <span>Created:</span>
                            <span className="text-slate-700">{format(new Date(asset.created_at), 'MMM d, HH:mm')}</span>
                        </div>
                    )}
                </div>

                {/* Properties Count */}
                {asset.properties && Object.keys(asset.properties).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100">
                        <span className="text-xs text-slate-500">
                            {Object.keys(asset.properties).length} properties
                        </span>
                    </div>
                )}
            </Card>
        </motion.div>
    );
}

function AssetDetailModal({ asset, onClose }) {
    if (!asset) return null;

    const typeConfig = {
        Dataset: { icon: <Database size={24} />, color: 'text-blue-600', bg: 'bg-blue-50' },
        Model: { icon: <Box size={24} />, color: 'text-purple-600', bg: 'bg-purple-50' },
        Metrics: { icon: <BarChart2 size={24} />, color: 'text-emerald-600', bg: 'bg-emerald-50' },
        default: { icon: <FileText size={24} />, color: 'text-slate-600', bg: 'bg-slate-50' }
    };

    const config = typeConfig[asset.type] || typeConfig.default;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden"
                >
                    {/* Header */}
                    <div className={`flex items-center justify-between p-6 border-b border-slate-100 ${config.bg}`}>
                        <div className="flex items-center gap-4">
                            <div className={`p-3 bg-white rounded-xl shadow-sm ${config.color}`}>
                                {config.icon}
                            </div>
                            <div>
                                <h3 className="text-2xl font-bold text-slate-900">{asset.name}</h3>
                                <p className="text-sm text-slate-500 mt-1">{asset.type} • {asset.step}</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-white rounded-lg transition-colors"
                        >
                            <X size={20} className="text-slate-400" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[calc(85vh-200px)]">
                        <div className="space-y-6">
                            {/* Properties */}
                            {asset.properties && Object.keys(asset.properties).length > 0 && (
                                <div>
                                    <h4 className="text-lg font-semibold text-slate-900 mb-4">Properties</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {Object.entries(asset.properties).map(([key, value]) => (
                                            <div key={key} className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                                                <span className="text-sm text-slate-500 block mb-2 font-medium">{key}</span>
                                                <span className="text-base font-mono font-semibold text-slate-900 break-all">
                                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Value Preview */}
                            {asset.value && (
                                <div>
                                    <h4 className="text-lg font-semibold text-slate-900 mb-4">Value Preview</h4>
                                    <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-sm font-mono overflow-x-auto leading-relaxed">
                                        {asset.value}
                                    </pre>
                                </div>
                            )}

                            {/* Metadata */}
                            <div>
                                <h4 className="text-lg font-semibold text-slate-900 mb-4">Metadata</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <MetadataItem label="Artifact ID" value={asset.artifact_id} mono />
                                    <MetadataItem label="Type" value={asset.type} />
                                    <MetadataItem label="Step" value={asset.step} />
                                    <MetadataItem label="Run ID" value={asset.run_id} mono />
                                    {asset.created_at && (
                                        <MetadataItem
                                            label="Created At"
                                            value={format(new Date(asset.created_at), 'MMM d, yyyy HH:mm:ss')}
                                        />
                                    )}
                                    {asset.path && (
                                        <MetadataItem label="Path" value={asset.path} mono />
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center">
                        <span className="text-sm text-slate-500">
                            {asset.created_at && `Created ${format(new Date(asset.created_at), 'MMM d, yyyy')}`}
                        </span>
                        <div className="flex gap-2">
                            <Button variant="ghost" onClick={onClose}>Close</Button>
                            <Button variant="primary" className="flex items-center gap-2">
                                <Download size={16} />
                                Download
                            </Button>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

function MetadataItem({ label, value, mono = false }) {
    return (
        <div className="p-3 bg-white rounded-lg border border-slate-100">
            <span className="text-xs text-slate-500 block mb-1">{label}</span>
            <span className={`text-sm text-slate-900 font-semibold ${mono ? 'font-mono text-xs' : ''} break-all`}>
                {value}
            </span>
        </div>
    );
}

function getTypeIcon(type) {
    const icons = {
        Dataset: <Database size={18} className="text-blue-600" />,
        Model: <Box size={18} className="text-purple-600" />,
        Metrics: <BarChart2 size={18} className="text-emerald-600" />
    };
    return icons[type] || <FileText size={18} className="text-slate-600" />;
}
