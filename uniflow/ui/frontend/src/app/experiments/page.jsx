import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FlaskConical, ArrowRight, Sparkles, Calendar, Activity } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';

export function Experiments() {
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);
    const { selectedProject } = useProject();

    useEffect(() => {
        const fetchExperiments = async () => {
            setLoading(true);
            try {
                const url = selectedProject
                    ? `/api/experiments?project=${encodeURIComponent(selectedProject)}`
                    : '/api/experiments';
                const res = await fetch(url);
                const data = await res.json();
                setExperiments(data.experiments || []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchExperiments();
    }, [selectedProject]);

    const columns = [
        {
            header: 'Experiment',
            key: 'name',
            sortable: true,
            render: (exp) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
                        <FlaskConical size={16} />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{exp.name}</div>
                        {exp.description && (
                            <div className="text-xs text-slate-500 truncate max-w-[200px]">{exp.description}</div>
                        )}
                    </div>
                </div>
            )
        },
        {
            header: 'Runs',
            key: 'run_count',
            sortable: true,
            render: (exp) => (
                <Badge variant="secondary" className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {exp.run_count || 0} runs
                </Badge>
            )
        },
        {
            header: 'Created',
            key: 'created_at',
            sortable: true,
            render: (exp) => (
                <div className="flex items-center gap-2 text-slate-500">
                    <Calendar size={14} />
                    {exp.created_at ? format(new Date(exp.created_at), 'MMM d, HH:mm') : '-'}
                </div>
            )
        },
        {
            header: 'Actions',
            key: 'actions',
            render: (exp) => (
                <Link to={`/experiments/${exp.experiment_id}`}>
                    <Button variant="ghost" size="sm" className="text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20">
                        View Details <ArrowRight size={14} className="ml-1" />
                    </Button>
                </Link>
            )
        }
    ];

    const renderGrid = (exp) => (
        <Link to={`/experiments/${exp.experiment_id}`}>
            <Card className="group cursor-pointer hover:border-primary-300 hover:shadow-lg h-full transition-all duration-200 overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-50/50 to-pink-50/50 dark:from-purple-900/10 dark:to-pink-900/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />

                <div className="relative">
                    <div className="flex items-start justify-between mb-4">
                        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl text-purple-600 dark:text-purple-400 group-hover:bg-purple-600 group-hover:text-white transition-all duration-200 group-hover:scale-110">
                            <FlaskConical size={24} />
                        </div>
                        <Badge variant="default" className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30 group-hover:text-purple-700 dark:group-hover:text-purple-300 transition-colors">
                            {exp.run_count || 0} runs
                        </Badge>
                    </div>

                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2 group-hover:text-purple-700 dark:group-hover:text-purple-400 transition-colors">
                        {exp.name}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 line-clamp-2 min-h-[2.5rem]">
                        {exp.description || "No description provided"}
                    </p>

                    <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-700">
                        <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                            <Calendar size={12} />
                            {exp.created_at ? format(new Date(exp.created_at), 'MMM d, yyyy') : '-'}
                        </span>
                        <span className="text-sm font-semibold text-primary-600 group-hover:text-primary-700 dark:text-primary-400 dark:group-hover:text-primary-300 flex items-center gap-1 group-hover:gap-2 transition-all">
                            View <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                        </span>
                    </div>
                </div>
            </Card>
        </Link>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <DataView
                title="Experiments"
                subtitle="Track and compare your ML experiments with detailed metrics and parameters"
                items={experiments}
                loading={loading}
                columns={columns}
                renderGrid={renderGrid}
                emptyState={
                    <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/30 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700">
                        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 rounded-2xl flex items-center justify-center mb-6 shadow-inner">
                            <FlaskConical className="text-purple-400" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No experiments yet</h3>
                        <p className="text-slate-500 max-w-md mx-auto mb-6">
                            Start tracking your ML experiments using the Experiment API to compare runs and optimize your models.
                        </p>
                        <div className="inline-block px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-mono text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            <code>from flowy.tracking import Experiment</code>
                        </div>
                    </div>
                }
            />
        </div>
    );
}
