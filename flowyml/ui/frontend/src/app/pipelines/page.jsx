import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { Link } from 'react-router-dom';
import { Layers, Play, Clock, CheckCircle, XCircle, TrendingUp, Calendar, Activity, ArrowRight, Zap, FolderPlus } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { format } from 'date-fns';
import { DataView } from '../../components/ui/DataView';
import { useProject } from '../../contexts/ProjectContext';
import { NavigationTree } from '../../components/NavigationTree';
import { PipelineDetailsPanel } from '../../components/PipelineDetailsPanel';

export function Pipelines() {
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedPipeline, setSelectedPipeline] = useState(null);
    const { selectedProject } = useProject();

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const pipelinesUrl = selectedProject
                ? `/api/pipelines/?project=${encodeURIComponent(selectedProject)}`
                : '/api/pipelines/';

            const pipelinesRes = await fetchApi(pipelinesUrl);
            if (!pipelinesRes.ok) throw new Error(`Failed to fetch pipelines: ${pipelinesRes.statusText}`);

            const pipelinesData = await pipelinesRes.json();

            setPipelines(pipelinesData.pipelines || []);
        } catch (err) {
            console.error(err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedProject]);

    const handlePipelineSelect = (pipeline) => {
        setSelectedPipeline(pipeline);
    };

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-900">
                <div className="text-center p-8 bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-100 dark:border-red-800 max-w-md">
                    <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-red-700 dark:text-red-300 mb-2">Failed to load pipelines</h3>
                    <p className="text-red-600 dark:text-red-400 mb-6">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300 font-medium"
                    >
                        Retry Connection
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Layers className="text-primary-500" />
                            Pipelines
                        </h1>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            View and manage your ML pipelines
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
                                    mode="pipelines"
                                    projectId={selectedProject}
                                    onSelect={handlePipelineSelect}
                                    selectedId={selectedPipeline?.name}
                                />
                            </div>
                        </div>

                        {/* Right Content - Details Panel or Empty State */}
                        <div className="flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            {selectedPipeline ? (
                                <PipelineDetailsPanel
                                    pipeline={selectedPipeline}
                                    onClose={() => setSelectedPipeline(null)}
                                    onProjectUpdate={fetchData}
                                />
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-50/50 dark:bg-slate-900/50">
                                    <div className="w-20 h-20 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mb-6 animate-pulse">
                                        <Layers size={40} className="text-primary-500" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                                        Select a Pipeline
                                    </h2>
                                    <p className="text-slate-500 max-w-md">
                                        Choose a pipeline from the sidebar to view execution history and statistics.
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
