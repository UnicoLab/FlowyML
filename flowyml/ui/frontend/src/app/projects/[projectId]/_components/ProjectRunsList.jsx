import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { Link } from 'react-router-dom';
import { Clock, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { formatDate } from '../../../../utils/date';

const StatusIcon = ({ status }) => {
    switch (status?.toLowerCase()) {
        case 'completed':
        case 'success':
            return <CheckCircle className="w-4 h-4 text-green-500" />;
        case 'failed':
            return <XCircle className="w-4 h-4 text-red-500" />;
        case 'running':
            return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
        default:
            return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
};

export function ProjectRunsList({ projectId }) {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRuns = async () => {
            try {
                const response = await fetchApi(`/api/runs?project=${projectId}`);
                const data = await response.json();
                // API returns {runs: [...]}
                setRuns(Array.isArray(data?.runs) ? data.runs : []);
            } catch (error) {
                console.error('Failed to fetch runs:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchRuns();
        }
    }, [projectId]);

    const columns = [
        {
            header: 'Run Name',
            key: 'name',
            render: (run) => (
                <Link to={`/runs/${run.run_id}`} className="flex items-center gap-3 group">
                    <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors">
                        <Clock className="w-4 h-4 text-slate-500" />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            {run.name || run.run_id?.substring(0, 8) || 'N/A'}
                        </div>
                        <div className="text-xs text-slate-500">{run.pipeline_name}</div>
                    </div>
                </Link>
            )
        },
        {
            header: 'Status',
            key: 'status',
            render: (run) => (
                <div className="flex items-center gap-2">
                    <StatusIcon status={run.status} />
                    <span className="capitalize text-sm">{run.status}</span>
                </div>
            )
        },
        {
            header: 'Created',
            key: 'created',
            render: (run) => (
                <span className="text-slate-500 text-sm">
                    {formatDate(run.created, 'MMM d, yyyy HH:mm')}
                </span>
            )
        }
    ];

    return (
        <DataView
            items={runs}
            loading={loading}
            columns={columns}
            initialView="table"
            renderGrid={(run) => (
                <Link to={`/runs/${run.run_id}`} className="block">
                    <div className="group p-5 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-500/50 hover:shadow-md transition-all duration-300">
                        <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-2">
                                <StatusIcon status={run.status} />
                                <span className={`text-sm font-medium capitalize ${run.status === 'completed' ? 'text-green-600 dark:text-green-400' :
                                    run.status === 'failed' ? 'text-red-600 dark:text-red-400' :
                                        'text-slate-600 dark:text-slate-400'
                                    }`}>
                                    {run.status}
                                </span>
                            </div>
                            <span className="text-xs font-mono text-slate-400 bg-slate-50 dark:bg-slate-900 px-2 py-1 rounded">
                                {run.run_id?.substring(0, 8) || 'N/A'}
                            </span>
                        </div>

                        <h3 className="font-semibold text-slate-900 dark:text-white mb-1 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            {run.name || `Run ${run.run_id?.substring(0, 8) || 'N/A'}`}
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 flex items-center gap-1">
                            <span className="opacity-75">Pipeline:</span>
                            <span className="font-medium text-slate-700 dark:text-slate-300">{run.pipeline_name}</span>
                        </p>

                        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                            <div className="flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5" />
                                <span>{formatDate(run.created, 'MMM d, HH:mm')}</span>
                            </div>
                            {run.duration && (
                                <span>{run.duration.toFixed(2)}s</span>
                            )}
                        </div>
                    </div>
                </Link>
            )}
            emptyState={
                <div className="text-center py-8">
                    <Clock className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                    <p className="text-slate-500">No runs found for this project</p>
                </div>
            }
        />
    );
}
