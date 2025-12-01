import React, { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { FlaskConical, ArrowRight, Sparkles, Calendar, Activity, FolderPlus, Layout } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';
import { EmptyState } from '../../components/ui/EmptyState';
import { NavigationTree } from '../../components/NavigationTree';
import { ExperimentDetailsPanel } from '../../components/ExperimentDetailsPanel';

export function Experiments() {
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedExperiment, setSelectedExperiment] = useState(null);
    const { selectedProject } = useProject();
    const navigate = useNavigate();

    useEffect(() => {
        const fetchExperiments = async () => {
            setLoading(true);
            try {
                const url = selectedProject
                    ? `/api/experiments/?project=${encodeURIComponent(selectedProject)}`
                    : '/api/experiments/';
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

    const handleExperimentSelect = (experiment) => {
        setSelectedExperiment(experiment);
    };

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <FlaskConical className="text-purple-500" />
                            Experiments
                        </h1>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Manage and track your ML experiments
                        </p>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-[1800px] mx-auto px-6 py-6">
                    <div className="h-full flex gap-6">
                        {/* Left Sidebar - Navigation */}
                        <div className="w-[320px] shrink-0 flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            <div className="p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
                                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Explorer</h3>
                            </div>
                            <div className="flex-1 min-h-0">
                                <NavigationTree
                                    mode="experiments"
                                    projectId={selectedProject}
                                    onSelect={handleExperimentSelect}
                                    selectedId={selectedExperiment?.experiment_id}
                                />
                            </div>
                        </div>

                        {/* Right Content - Details Panel or Empty State */}
                        <div className="flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            {selectedExperiment ? (
                                <ExperimentDetailsPanel
                                    experiment={selectedExperiment}
                                    onClose={() => setSelectedExperiment(null)}
                                />
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-50/50 dark:bg-slate-900/50">
                                    <div className="w-20 h-20 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mb-6 animate-pulse">
                                        <FlaskConical size={40} className="text-purple-500" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                                        Select an Experiment
                                    </h2>
                                    <p className="text-slate-500 max-w-md">
                                        Choose an experiment from the sidebar to view detailed metrics, runs, and analysis.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
