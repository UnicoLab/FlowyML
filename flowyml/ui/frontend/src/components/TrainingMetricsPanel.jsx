import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import { TrainingHistoryChart } from './TrainingHistoryChart';
import { Activity, TrendingUp, RefreshCcw, Download, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './ui/Button';

/**
 * TrainingMetricsPanel - A comprehensive panel for displaying training metrics
 * in the run details page. Fetches training history from the API and displays
 * beautiful interactive charts.
 *
 * IMPORTANT: This component returns null if no training data is available,
 * so it won't render anything for non-training pipelines.
 */
export function TrainingMetricsPanel({ runId, isRunning = false, autoRefresh = true }) {
    const [trainingHistory, setTrainingHistory] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [hasChecked, setHasChecked] = useState(false);

    const fetchTrainingHistory = async () => {
        try {
            const res = await fetchApi(`/api/runs/${runId}/training-history`);
            if (!res.ok) {
                throw new Error('Failed to fetch training history');
            }
            const data = await res.json();

            if (data.has_history && data.training_history?.epochs?.length > 0) {
                setTrainingHistory(data.training_history);
                setLastUpdated(new Date());
                setError(null);
            } else {
                setTrainingHistory(null);
            }
        } catch (err) {
            console.error('Error fetching training history:', err);
            setError(err.message);
            setTrainingHistory(null);
        } finally {
            setLoading(false);
            setHasChecked(true);
        }
    };

    // Initial fetch
    useEffect(() => {
        if (runId) {
            fetchTrainingHistory();
        }
    }, [runId]);

    // Auto-refresh while running
    useEffect(() => {
        if (!isRunning || !autoRefresh) return;

        const interval = setInterval(fetchTrainingHistory, 5000);
        return () => clearInterval(interval);
    }, [runId, isRunning, autoRefresh]);

    // Export training history as JSON
    const handleExport = () => {
        if (!trainingHistory) return;

        const blob = new Blob([JSON.stringify(trainingHistory, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `training-history-${runId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // Show loading only briefly on first load
    if (loading && !hasChecked) {
        return (
            <div className="flex items-center justify-center p-6">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-200 border-t-primary-600" />
            </div>
        );
    }

    // Don't render anything if there's no training history
    // This makes the section completely disappear for non-training pipelines
    if (!trainingHistory || !trainingHistory.epochs?.length) {
        return null;
    }

    const totalEpochs = trainingHistory.epochs?.length || 0;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-primary-500 to-purple-500 rounded-xl shadow-lg">
                        <TrendingUp size={20} className="text-white" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                            Training Metrics
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            {totalEpochs} epochs recorded
                            {lastUpdated && (
                                <span className="text-xs text-slate-400 ml-2">
                                    • Updated {lastUpdated.toLocaleTimeString()}
                                </span>
                            )}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {isRunning && (
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/30 rounded-full border border-amber-200 dark:border-amber-800">
                            <Activity size={14} className="text-amber-600 dark:text-amber-400 animate-pulse" />
                            <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
                                Live
                            </span>
                        </div>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={fetchTrainingHistory}
                        className="text-slate-500 hover:text-slate-700"
                    >
                        <RefreshCcw size={14} />
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleExport}
                        className="text-slate-600"
                    >
                        <Download size={14} className="mr-1.5" />
                        Export
                    </Button>
                </div>
            </div>

            {/* Training History Charts */}
            <TrainingHistoryChart trainingHistory={trainingHistory} compact={false} />

            {/* Quick Stats Footer */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                    <span>
                        💡 Tip: Hover over the charts for detailed epoch-by-epoch values
                    </span>
                    <a
                        href="https://flowyml.readthedocs.io/integrations/keras/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 hover:text-primary-600 transition-colors"
                    >
                        Learn more about Keras integration
                        <ExternalLink size={12} />
                    </a>
                </div>
            </div>
        </motion.div>
    );
}

export default TrainingMetricsPanel;
