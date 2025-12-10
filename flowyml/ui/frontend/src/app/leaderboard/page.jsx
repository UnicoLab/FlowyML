import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../utils/api';
import { Trophy, TrendingUp, TrendingDown, Filter, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { EmptyState } from '../../components/ui/EmptyState';
import { Button } from '../../components/ui/Button';

export function Leaderboard() {
    const [metric, setMetric] = useState('accuracy');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchLeaderboard();
    }, [metric]);

    const fetchLeaderboard = async () => {
        setLoading(true);
        try {
            const response = await fetchApi(`/api/leaderboard/${metric}`);
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error('Failed to fetch leaderboard:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold flex items-center gap-2 text-slate-900 dark:text-white">
                    <Trophy className="text-yellow-500" />
                    Model Leaderboard
                </h1>

                <div className="flex items-center gap-2 bg-white dark:bg-slate-800 rounded-lg p-1 border border-slate-200 dark:border-slate-700">
                    <Filter className="w-4 h-4 ml-2 text-slate-400 dark:text-slate-500" />
                    <select
                        value={metric}
                        onChange={(e) => setMetric(e.target.value)}
                        className="bg-transparent border-none outline-none text-sm px-2 py-1 text-slate-700 dark:text-slate-200"
                    >
                        <option value="accuracy">Accuracy</option>
                        <option value="loss">Loss</option>
                        <option value="f1_score">F1 Score</option>
                        <option value="latency">Latency</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-500"></div>
                </div>
            ) : !data || data.models.length === 0 ? (
                <EmptyState
                    icon={Trophy}
                    title={`No models found for metric: ${metric}`}
                    description="Generate sample data to populate the leaderboard."
                    action={
                        <Button
                            onClick={async () => {
                                setLoading(true);
                                try {
                                    await fetchApi('/api/leaderboard/generate_sample_data', { method: 'POST' });
                                    fetchLeaderboard();
                                } catch (error) {
                                    console.error('Failed to generate sample data:', error);
                                    setLoading(false);
                                }
                            }}
                            className="flex items-center gap-2"
                        >
                            <RefreshCw size={16} />
                            Generate Sample Data
                        </Button>
                    }
                />
            ) : (
                <div className="bg-white dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Rank</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Model</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Score</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Run ID</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Date</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {data.models.map((model, idx) => (
                                <tr key={model.run_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            {idx === 0 && <Trophy className="w-4 h-4 text-yellow-500" />}
                                            {idx === 1 && <Trophy className="w-4 h-4 text-slate-400" />}
                                            {idx === 2 && <Trophy className="w-4 h-4 text-amber-600" />}
                                            <span className={`font-bold ${idx < 3 ? 'text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-400'}`}>
                                                #{model.rank}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-900 dark:text-white">{model.model_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                                                {model.score.toFixed(4)}
                                            </span>
                                            {data.higher_is_better ? (
                                                <TrendingUp className="w-4 h-4 text-green-500" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-green-500" />
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400 font-mono">
                                        {model.run_id?.substring(0, 8) || 'N/A'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                        {model.timestamp ? format(new Date(model.timestamp), 'MMM d, HH:mm') : '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
