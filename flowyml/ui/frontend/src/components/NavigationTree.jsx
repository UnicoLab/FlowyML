import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import {
    ChevronRight,
    ChevronDown,
    Box,
    Activity,
    PlayCircle,
    FileBox,
    CheckCircle,
    XCircle,
    Clock,
    Database,
    Layers,
    X,
    Download,
    Info,
    BarChart2,
    FileText,
    Eye,
    Folder,
    GitBranch,
    FlaskConical,
    Search,
    Filter
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '../utils/date';
import { motion, AnimatePresence } from 'framer-motion';

const StatusIcon = ({ status }) => {
    switch (status?.toLowerCase()) {
        case 'completed':
        case 'success':
            return <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />;
        case 'failed':
            return <XCircle className="w-3.5 h-3.5 text-rose-500" />;
        case 'running':
            return <Activity className="w-3.5 h-3.5 text-amber-500 animate-spin" />;
        default:
            return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
};

const TreeNode = ({
    label,
    icon: Icon,
    children,
    defaultExpanded = false,
    actions,
    status,
    level = 0,
    badge,
    onClick,
    isActive = false,
    subLabel
}) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);
    const hasChildren = children && children.length > 0;

    return (
        <div className="select-none">
            <motion.div
                initial={false}
                animate={{ backgroundColor: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent' }}
                className={`
                    group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all
                    hover:bg-slate-100 dark:hover:bg-slate-800
                    ${isActive ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'}
                    ${level === 0 ? 'mb-0.5' : ''}
                `}
                style={{ paddingLeft: `${level * 1.25 + 0.5}rem` }}
                onClick={(e) => {
                    e.stopPropagation();
                    if (hasChildren) {
                        setIsExpanded(!isExpanded);
                    }
                    onClick?.();
                }}
            >
                <div className="flex items-center gap-1 text-slate-400 shrink-0">
                    {hasChildren ? (
                        <motion.div
                            animate={{ rotate: isExpanded ? 90 : 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <ChevronRight className="w-3.5 h-3.5" />
                        </motion.div>
                    ) : (
                        <div className="w-3.5" />
                    )}
                </div>

                {Icon && (
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-500' : 'text-slate-400 group-hover:text-slate-500 dark:text-slate-500 dark:group-hover:text-slate-400'}`} />
                )}

                <div className="flex-1 flex items-center justify-between gap-2 min-w-0 overflow-hidden">
                    <div className="flex flex-col min-w-0">
                        <span className={`text-sm truncate ${isActive ? 'font-medium' : ''}`}>
                            {label}
                        </span>
                        {subLabel && (
                            <span className="text-[10px] text-slate-400 truncate">
                                {subLabel}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        {badge}
                        {status && <StatusIcon status={status} />}
                        {actions}
                    </div>
                </div>
            </motion.div>

            <AnimatePresence initial={false}>
                {isExpanded && hasChildren && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export function NavigationTree({
    projectId,
    onSelect,
    selectedId,
    mode = 'experiments', // experiments, pipelines, runs
    className = ''
}) {
    const [data, setData] = useState({ projects: [], items: [] });
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('');

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                let url = '';
                let itemsKey = '';

                switch (mode) {
                    case 'experiments':
                        url = projectId
                            ? `/api/experiments?project=${encodeURIComponent(projectId)}`
                            : '/api/experiments';
                        itemsKey = 'experiments';
                        break;
                    case 'pipelines':
                        url = projectId
                            ? `/api/pipelines?project=${encodeURIComponent(projectId)}`
                            : '/api/pipelines';
                        itemsKey = 'pipelines';
                        break;
                    case 'runs':
                        url = projectId
                            ? `/api/runs?project=${encodeURIComponent(projectId)}&limit=100`
                            : '/api/runs?limit=100';
                        itemsKey = 'runs';
                        break;
                    default:
                        break;
                }

                const res = await fetchApi(url);
                const jsonData = await res.json();

                // If no project selected, we might need to fetch projects to group by
                let projects = [];
                if (!projectId) {
                    // Extract unique projects from items
                    const items = jsonData[itemsKey] || [];
                    const projectNames = [...new Set(items.map(i => i.project).filter(Boolean))];
                    projects = projectNames.map(name => ({ name }));
                }

                setData({
                    projects,
                    items: jsonData[itemsKey] || []
                });
            } catch (error) {
                console.error('Failed to fetch navigation data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [projectId, mode]);

    if (loading) {
        return (
            <div className={`p-4 ${className}`}>
                <div className="animate-pulse space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
                    ))}
                </div>
            </div>
        );
    }

    const filteredItems = data.items.filter(item =>
        (item.name || item.run_id || '').toLowerCase().includes(filter.toLowerCase())
    );

    const renderExperiments = () => {
        const getRunsForExperiment = (expName) => {
            // This would ideally come from the API or be passed in,
            // but for now we might not have runs loaded here.
            // We'll just show the experiment node.
            return [];
        };

        const renderExperimentNode = (exp, level) => (
            <TreeNode
                key={exp.experiment_id}
                label={exp.name}
                icon={FlaskConical}
                level={level}
                isActive={selectedId === exp.experiment_id}
                onClick={() => onSelect?.(exp)}
                badge={
                    <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded-full">
                        {exp.run_count || 0}
                    </span>
                }
            />
        );

        if (projectId || data.projects.length === 0) {
            return filteredItems.map(exp => renderExperimentNode(exp, 0));
        } else {
            return data.projects.map(proj => {
                const projExperiments = filteredItems.filter(e => e.project === proj.name);
                if (projExperiments.length === 0) return null;

                return (
                    <TreeNode
                        key={proj.name}
                        label={proj.name}
                        icon={Folder}
                        level={0}
                        defaultExpanded={true}
                        badge={
                            <span className="text-xs text-slate-400">
                                {projExperiments.length}
                            </span>
                        }
                    >
                        {projExperiments.map(exp => renderExperimentNode(exp, 1))}
                    </TreeNode>
                );
            });
        }
    };

    const renderPipelines = () => {
        const renderPipelineNode = (pipeline, level) => (
            <TreeNode
                key={pipeline.name}
                label={pipeline.name}
                icon={Layers}
                level={level}
                isActive={selectedId === pipeline.name}
                onClick={() => onSelect?.(pipeline)}
                badge={
                    <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded-full">
                        v{pipeline.version || '1'}
                    </span>
                }
            />
        );

        if (projectId || data.projects.length === 0) {
            return filteredItems.map(p => renderPipelineNode(p, 0));
        } else {
            return data.projects.map(proj => {
                const projPipelines = filteredItems.filter(p => p.project === proj.name);
                if (projPipelines.length === 0) return null;

                return (
                    <TreeNode
                        key={proj.name}
                        label={proj.name}
                        icon={Folder}
                        level={0}
                        defaultExpanded={true}
                    >
                        {projPipelines.map(p => renderPipelineNode(p, 1))}
                    </TreeNode>
                );
            });
        }
    };

    const renderRuns = () => {
        const renderRunNode = (run, level) => (
            <TreeNode
                key={run.run_id}
                label={run.name || run.run_id.slice(0, 8)}
                subLabel={formatDate(run.created || run.start_time)}
                icon={PlayCircle}
                level={level}
                status={run.status}
                isActive={selectedId === run.run_id}
                onClick={() => onSelect?.(run)}
            />
        );

        // Group by Pipeline
        const pipelines = [...new Set(filteredItems.map(r => r.pipeline_name).filter(Boolean))];

        return pipelines.map(pipelineName => {
            const pipelineRuns = filteredItems.filter(r => r.pipeline_name === pipelineName);

            return (
                <TreeNode
                    key={pipelineName}
                    label={pipelineName}
                    icon={Activity}
                    level={0}
                    defaultExpanded={true}
                    badge={
                        <span className="text-xs text-slate-400">
                            {pipelineRuns.length}
                        </span>
                    }
                >
                    {pipelineRuns.map(run => renderRunNode(run, 1))}
                </TreeNode>
            );
        });
    };

    return (
        <div className={`flex flex-col h-full bg-slate-50/50 dark:bg-slate-900/50 ${className}`}>
            {/* Search */}
            <div className="p-2 sticky top-0 bg-inherit z-10">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder={`Search ${mode}...`}
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    />
                </div>
            </div>

            {/* Tree Content */}
            <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
                {filteredItems.length === 0 ? (
                    <div className="text-center py-8 text-slate-400 text-sm">
                        No {mode} found
                    </div>
                ) : (
                    <>
                        {mode === 'experiments' && renderExperiments()}
                        {mode === 'pipelines' && renderPipelines()}
                        {mode === 'runs' && renderRuns()}
                    </>
                )}
            </div>
        </div>
    );
}
