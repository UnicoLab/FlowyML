import React, { useEffect, useState } from 'react';
import { fetchApi } from '../utils/api';
import { Link } from 'react-router-dom';
import { Layers, Play, Clock, CheckCircle, XCircle, TrendingUp, Calendar, Activity, ArrowRight, Zap } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { format } from 'date-fns';
import { DataView } from './ui/DataView';
import { useProject } from '../contexts/ProjectContext';

export function Pipelines() {
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const pipelinesUrl = selectedProject
                    ? `/api/pipelines?project=${encodeURIComponent(selectedProject)}`
                    : '/api/pipelines';
                const runsUrl = selectedProject
                    ? `/api/runs?project=${encodeURIComponent(selectedProject)}`
                    : '/api/runs';

                const pipelinesRes = await fetchApi(pipelinesUrl);
                const pipelinesData = await pipelinesRes.json();

                // Fetch runs to calculate stats per pipeline
                const runsRes = await fetchApi(runsUrl);
                const runsData = await runsRes.json();

                // Calculate stats for each pipeline
                const pipelinesWithStats = pipelinesData.pipelines.map(pipeline => {
                    const pipelineRuns = runsData.runs.filter(r => r.pipeline_name === pipeline);
                    const completedRuns = pipelineRuns.filter(r => r.status === 'completed');
                    const failedRuns = pipelineRuns.filter(r => r.status === 'failed');
                    const avgDuration = pipelineRuns.length > 0
                        ? pipelineRuns.reduce((sum, r) => sum + (r.duration || 0), 0) / pipelineRuns.length
                        : 0;

                    const lastRun = pipelineRuns.length > 0
                        ? pipelineRuns.sort((a, b) => new Date(b.start_time) - new Date(a.start_time))[0]
                        : null;

                    return {
                        name: pipeline,
                        totalRuns: pipelineRuns.length,
                        completedRuns: completedRuns.length,
                        failedRuns: failedRuns.length,
                        successRate: pipelineRuns.length > 0 ? (completedRuns.length / pipelineRuns.length) * 100 : 0,
                        avgDuration,
                        lastRun
                    };
                });

                setPipelines(pipelinesWithStats);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [selectedProject]);

    const columns = [
        {
            header: 'Pipeline',
            key: 'name',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-primary-500 to-purple-500 rounded-lg text-white">
                        <Layers size={16} />
                    </div>
                    <span className="font-medium text-slate-900 dark:text-white">{item.name}</span>
                </div>
            )
        },
        {
            header: 'Success Rate',
            key: 'successRate',
            sortable: true,
            render: (item) => {
                const rate = item.successRate;
                const color = rate >= 80 ? 'text-emerald-600 bg-emerald-50' : rate >= 50 ? 'text-amber-600 bg-amber-50' : 'text-rose-600 bg-rose-50';
                return (
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${color}`}>
                        {rate.toFixed(0)}%
                    </span>
                );
            }
        },
        {
            header: 'Total Runs',
            key: 'totalRuns',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Activity size={14} />
                    {item.totalRuns}
                </div>
            )
        },
        {
            header: 'Avg Duration',
            key: 'avgDuration',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Clock size={14} />
                    {item.avgDuration > 0 ? `${item.avgDuration.toFixed(1)}s` : '-'}
                </div>
            )
        },
        {
            header: 'Last Run',
            key: 'lastRun',
            render: (item) => item.lastRun ? (
                <div className="text-sm text-slate-500">
                    {format(new Date(item.lastRun.start_time), 'MMM d, HH:mm')}
                </div>
            ) : '-'
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (item) => (
                <Link
                    to={`/runs?pipeline=${encodeURIComponent(item.name)}`}
                    className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
                >
                    View Runs <ArrowRight size={14} />
                </Link>
            )
        }
    ];

    const renderGrid = (item) => {
        const successRate = item.successRate || 0;
        const statusColor = successRate >= 80 ? 'emerald' : successRate >= 50 ? 'amber' : 'rose';

        const colorClasses = {
            emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
            amber: { bg: 'bg-amber-50', text: 'text-amber-600' },
            rose: { bg: 'bg-rose-50', text: 'text-rose-600' }
        };
        const colors = colorClasses[statusColor];

        return (
            <Card className="group cursor-pointer hover:shadow-xl hover:border-primary-300 transition-all duration-200 overflow-hidden h-full">
                <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl text-white group-hover:scale-110 transition-transform shadow-lg">
                        <Layers size={24} />
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        {item.totalRuns > 0 && (
                            <Badge variant="secondary" className="text-xs bg-slate-100 text-slate-600">
                                {item.totalRuns} runs
                            </Badge>
                        )}
                        {successRate > 0 && (
                            <div className={`text-xs font-semibold px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                                {successRate.toFixed(0)}% success
                            </div>
                        )}
                    </div>
                </div>

                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-3 group-hover:text-primary-600 transition-colors">
                    {item.name}
                </h3>

                <div className="grid grid-cols-2 gap-3 mb-4">
                    <StatItem icon={<Activity size={14} />} label="Total" value={item.totalRuns} color="blue" />
                    <StatItem icon={<CheckCircle size={14} />} label="Success" value={item.completedRuns} color="emerald" />
                    <StatItem icon={<Clock size={14} />} label="Avg Time" value={item.avgDuration > 0 ? `${item.avgDuration.toFixed(1)}s` : '-'} color="purple" />
                    <StatItem icon={<XCircle size={14} />} label="Failed" value={item.failedRuns} color="rose" />
                </div>

                {item.lastRun && (
                    <div className="pt-4 border-t border-slate-100 dark:border-slate-700">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500 flex items-center gap-1">
                                <Calendar size={12} />
                                Last run
                            </span>
                            <span className="text-slate-700 dark:text-slate-300 font-medium">
                                {format(new Date(item.lastRun.start_time), 'MMM d, HH:mm')}
                            </span>
                        </div>
                    </div>
                )}

                <Link
                    to={`/runs?pipeline=${encodeURIComponent(item.name)}`}
                    className="mt-4 flex items-center justify-center gap-2 py-2 px-4 bg-slate-50 dark:bg-slate-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-slate-700 dark:text-slate-200 hover:text-primary-600 rounded-lg transition-all group-hover:bg-primary-50"
                >
                    <span className="text-sm font-semibold">View Runs</span>
                    <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </Link>
            </Card>
        );
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <DataView
                title="Pipelines"
                subtitle="Manage and monitor your ML pipeline definitions"
                items={pipelines}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-6">
                            <Layers className="text-slate-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No pipelines found</h3>
                        <p className="text-slate-500 max-w-md mx-auto">
                            Create your first pipeline by defining steps and running them with UniFlow
                        </p>
                    </div>
                }
            />
        </div>
    );
}

function StatItem({ icon, label, value, color }) {
    const colorClasses = {
        blue: 'bg-blue-50 text-blue-600',
        emerald: 'bg-emerald-50 text-emerald-600',
        purple: 'bg-purple-50 text-purple-600',
        rose: 'bg-rose-50 text-rose-600'
    };

    return (
        <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded ${colorClasses[color]}`}>
                {icon}
            </div>
            <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-sm font-bold text-slate-900 dark:text-white">{value}</p>
            </div>
        </div>
    );
}
