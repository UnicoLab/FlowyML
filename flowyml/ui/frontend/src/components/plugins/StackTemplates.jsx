import React, { useState, useEffect } from 'react';
import {
    Layers, Cloud, Server, Cpu, Rocket, Sparkles, CheckCircle,
    Loader2, ChevronDown, ChevronUp, HardDrive, Zap
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { fetchApi } from '../../utils/api';

const CLOUD_ICONS = {
    local: HardDrive,
    gcp: Cloud,
    aws: Cloud,
    azure: Cloud,
    kubernetes: Cpu,
};

const CLOUD_COLORS = {
    local: 'from-slate-500 to-slate-600',
    gcp: 'from-blue-500 to-cyan-500',
    aws: 'from-orange-500 to-amber-500',
    azure: 'from-blue-600 to-indigo-600',
    kubernetes: 'from-indigo-500 to-purple-500',
};

const DIFFICULTY_COLORS = {
    beginner: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    intermediate: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    advanced: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export function StackTemplates() {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [provisioning, setProvisioning] = useState(null);
    const [expandedId, setExpandedId] = useState(null);
    const [stackName, setStackName] = useState('');
    const [provisionSuccess, setProvisionSuccess] = useState(null);
    const [filterCloud, setFilterCloud] = useState('all');

    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            setLoading(true);
            const res = await fetchApi('/api/plugins/stacks/templates');
            const data = await res.json();
            setTemplates(data);
        } catch (error) {
            console.error('Failed to load stack templates:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleProvision = async (templateId) => {
        if (!stackName.trim()) return;
        setProvisioning(templateId);
        try {
            const res = await fetchApi('/api/plugins/stacks/provision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_id: templateId, stack_name: stackName }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Provision failed');
            }
            setProvisionSuccess(templateId);
            setStackName('');
            setTimeout(() => setProvisionSuccess(null), 3000);
        } catch (error) {
            console.error('Provision failed:', error);
            alert(`Provision failed: ${error.message}`);
        } finally {
            setProvisioning(null);
        }
    };

    const cloudFilters = ['all', 'local', 'gcp', 'aws', 'azure', 'kubernetes'];
    const filteredTemplates = templates.filter(
        (t) => filterCloud === 'all' || t.cloud === filterCloud
    );

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <Loader2 className="animate-spin text-primary-500" size={32} />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header / Description */}
            <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 p-4 rounded-xl border border-indigo-200 dark:border-indigo-800">
                <div className="flex items-start gap-3">
                    <Sparkles className="text-indigo-500 mt-1" size={20} />
                    <div>
                        <h3 className="font-medium text-slate-900 dark:text-white">
                            Preconfigured Stack Templates
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                            One-click provision a production-ready stack with best-practice component selections.
                            Each template configures all necessary infrastructure components automatically.
                        </p>
                    </div>
                </div>
            </div>

            {/* Cloud Filter Chips */}
            <div className="flex flex-wrap gap-2">
                {cloudFilters.map((cloud) => (
                    <button
                        key={cloud}
                        onClick={() => setFilterCloud(cloud)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${
                            filterCloud === cloud
                                ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
                        }`}
                    >
                        {cloud === 'all' ? '🌐 All' : cloud.toUpperCase()}
                    </button>
                ))}
            </div>

            {/* Template Cards */}
            <div className="grid gap-4">
                {filteredTemplates.map((template) => {
                    const CloudIcon = CLOUD_ICONS[template.cloud] || Cloud;
                    const isExpanded = expandedId === template.template_id;
                    const isSuccess = provisionSuccess === template.template_id;

                    return (
                        <div
                            key={template.template_id}
                            className="border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800/50 overflow-hidden transition-all hover:border-slate-300 dark:hover:border-slate-600"
                        >
                            {/* Card Header */}
                            <div className="p-5">
                                <div className="flex items-start gap-4">
                                    <div
                                        className={`p-3 rounded-xl bg-gradient-to-br ${CLOUD_COLORS[template.cloud]} text-white shadow-md`}
                                    >
                                        <CloudIcon size={24} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <h3 className="font-semibold text-slate-900 dark:text-white text-lg">
                                                {template.name}
                                            </h3>
                                            <span
                                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${DIFFICULTY_COLORS[template.difficulty]}`}
                                            >
                                                {template.difficulty}
                                            </span>
                                        </div>
                                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                            {template.description}
                                        </p>
                                        <div className="flex items-center gap-4 mt-3 text-xs text-slate-400 dark:text-slate-500">
                                            <span className="flex items-center gap-1">
                                                <Layers size={12} />
                                                {template.components.length} components
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Zap size={12} />
                                                {template.estimated_cost}
                                            </span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() =>
                                            setExpandedId(isExpanded ? null : template.template_id)
                                        }
                                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-400"
                                    >
                                        {isExpanded ? (
                                            <ChevronUp size={18} />
                                        ) : (
                                            <ChevronDown size={18} />
                                        )}
                                    </button>
                                </div>

                                {/* Tags */}
                                <div className="flex flex-wrap gap-1.5 mt-3 ml-16">
                                    {template.tags.map((tag) => (
                                        <span
                                            key={tag}
                                            className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-[11px] rounded-full"
                                        >
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Expanded: Component List + Provision */}
                            {isExpanded && (
                                <div className="border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 p-5 space-y-4">
                                    {/* Component Grid */}
                                    <div>
                                        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                                            Stack Components
                                        </h4>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                            {template.components.map((comp, i) => (
                                                <div
                                                    key={i}
                                                    className="flex items-center gap-2 p-2.5 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                                                >
                                                    <div className="w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" />
                                                    <div className="min-w-0">
                                                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">
                                                            {comp.name}
                                                        </p>
                                                        <p className="text-[10px] text-slate-400 dark:text-slate-500">
                                                            {comp.type}
                                                        </p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Provision Form */}
                                    <div className="flex gap-3 items-end">
                                        <div className="flex-1">
                                            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                                                Stack Name
                                            </label>
                                            <input
                                                type="text"
                                                placeholder={`e.g., my-${template.cloud}-stack`}
                                                value={expandedId === template.template_id ? stackName : ''}
                                                onChange={(e) => setStackName(e.target.value)}
                                                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                                            />
                                        </div>
                                        <Button
                                            onClick={() => handleProvision(template.template_id)}
                                            disabled={
                                                provisioning === template.template_id || !stackName.trim()
                                            }
                                            className="flex items-center gap-2 whitespace-nowrap"
                                        >
                                            {provisioning === template.template_id ? (
                                                <>
                                                    <Loader2 size={14} className="animate-spin" />
                                                    Provisioning...
                                                </>
                                            ) : isSuccess ? (
                                                <>
                                                    <CheckCircle size={14} />
                                                    Provisioned!
                                                </>
                                            ) : (
                                                <>
                                                    <Rocket size={14} />
                                                    Provision Stack
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
