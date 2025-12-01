import React, { useEffect, useState } from 'react';
import { fetchApi } from '../../utils/api';
import { Link, useSearchParams } from 'react-router-dom';
import { PlayCircle, Clock, CheckCircle, XCircle, Activity, ArrowRight, Calendar, Filter, RefreshCw, Layout } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { format } from 'date-fns';
import { DataView } from '../../components/ui/DataView';
import { StatusBadge } from '../../components/ui/ExecutionStatus';
import { useProject } from '../../contexts/ProjectContext';
import { NavigationTree } from '../../components/NavigationTree';
import { RunDetailsPanel } from '../../components/RunDetailsPanel';

export function Runs() {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedRun, setSelectedRun] = useState(null);
    const [searchParams] = useSearchParams();
    const { selectedProject } = useProject();

    // Filter states
    const [statusFilter, setStatusFilter] = useState('all');
    const pipelineFilter = searchParams.get('pipeline');

    const fetchRuns = async () => {
        setLoading(true);
        try {
            let url = '/api/runs/?limit=100';
            if (selectedProject) {
                url += `&project=${encodeURIComponent(selectedProject)}`;
            }
            if (pipelineFilter) {
                url += `&pipeline=${encodeURIComponent(pipelineFilter)}`;
            }

            const res = await fetchApi(url);
            const data = await res.json();
            setRuns(data.runs || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRuns();
    }, [selectedProject, pipelineFilter]);

    const handleRunSelect = (run) => {
        setSelectedRun(run);
    };

    return (
        <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shrink-0">
                <div className="flex items-center justify-between max-w-[1800px] mx-auto">
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <PlayCircle className="text-blue-500" />
                            Pipeline Runs
                        </h1>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Monitor and track all your pipeline executions
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button variant="outline" size="sm" onClick={fetchRuns} disabled={loading}>
                            <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full max-w-[1800px] mx-auto px-6 py-6">
                    <div className="h-full flex gap-6">
                        {/* Left Sidebar - Navigation */}
                        <div className="w-[320px] shrink-0 flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            <div className="p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-center">
                                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Explorer</h3>
                                {pipelineFilter && (
                                    <Badge variant="secondary" className="text-[10px]">
                                        Filtered: {pipelineFilter}
                                    </Badge>
                                )}
                            </div>
                            <div className="flex-1 min-h-0">
                                <NavigationTree
                                    mode="runs"
                                    projectId={selectedProject}
                                    onSelect={handleRunSelect}
                                    selectedId={selectedRun?.run_id}
                                />
                            </div>
                        </div>

                        {/* Right Content - Details Panel or Empty State */}
                        <div className="flex-1 min-w-0 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                            {selectedRun ? (
                                <RunDetailsPanel
                                    run={selectedRun}
                                    onClose={() => setSelectedRun(null)}
                                />
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-50/50 dark:bg-slate-900/50">
                                    <div className="w-20 h-20 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-6 animate-pulse">
                                        <PlayCircle size={40} className="text-blue-500" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                                        Select a Run
                                    </h2>
                                    <p className="text-slate-500 max-w-md">
                                        Choose a run from the sidebar to view execution details, logs, and artifacts.
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
