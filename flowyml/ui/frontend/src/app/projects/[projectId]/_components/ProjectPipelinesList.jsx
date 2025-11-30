import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { Link } from 'react-router-dom';
import { Activity, Clock } from 'lucide-react';
import { format } from 'date-fns';

export function ProjectPipelinesList({ projectId }) {
    const [pipelines, setPipelines] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPipelines = async () => {
            try {
                // In a real scenario, we would filter by project ID
                // For now, we'll fetch all and filter client-side or assume the API handles it
                const response = await fetchApi(`/api/pipelines?project=${projectId}`);
                const data = await response.json();
                setPipelines(Array.isArray(data) ? data : (data.items || []));
            } catch (error) {
                console.error('Failed to fetch pipelines:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchPipelines();
        }
    }, [projectId]);

    const columns = [
        {
            header: 'Pipeline Name',
            key: 'name',
            render: (pipeline) => (
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Activity className="w-4 h-4 text-blue-500" />
                    </div>
                    <span className="font-medium text-slate-900 dark:text-white">{pipeline.name}</span>
                </div>
            )
        },
        {
            header: 'Version',
            key: 'version',
            render: (pipeline) => (
                <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs font-medium">
                    v{pipeline.version || '1.0'}
                </span>
            )
        },
        {
            header: 'Created',
            key: 'created',
            render: (pipeline) => (
                <span className="text-slate-500 text-sm">
                    {pipeline.created ? format(new Date(pipeline.created), 'MMM d, yyyy') : '-'}
                </span>
            )
        }
    ];

    return (
        <DataView
            items={pipelines}
            loading={loading}
            columns={columns}
            emptyState={
                <div className="text-center py-8">
                    <Activity className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                    <p className="text-slate-500">No pipelines found for this project</p>
                </div>
            }
        />
    );
}
