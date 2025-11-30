import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { Link } from 'react-router-dom';
import { Clock, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { format } from 'date-fns';

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
                setRuns(Array.isArray(data) ? data : (data.runs || []));
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
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                        <Clock className="w-4 h-4 text-slate-500" />
                    </div>
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{run.name}</div>
                        <div className="text-xs text-slate-500">{run.pipeline_name}</div>
                    </div>
                </div>
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
                    {run.created ? format(new Date(run.created), 'MMM d, yyyy HH:mm') : '-'}
                </span>
            )
        }
    ];

    return (
        <DataView
            items={runs}
            loading={loading}
            columns={columns}
            emptyState={
                <div className="text-center py-8">
                    <Clock className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                    <p className="text-slate-500">No runs found for this project</p>
                </div>
            }
        />
    );
}
