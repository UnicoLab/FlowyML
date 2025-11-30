import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { Link } from 'react-router-dom';
import { Activity, Clock } from 'lucide-react';
import { formatDate } from '../../../../utils/date';

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
                // API returns {pipelines: [...]}
                setPipelines(Array.isArray(data?.pipelines) ? data.pipelines : []);
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
                <Link to={`/pipelines/${pipeline.id || pipeline.name}`} className="flex items-center gap-3 group">
                    <div className="p-2 bg-blue-500/10 rounded-lg group-hover:bg-blue-500/20 transition-colors">
                        <Activity className="w-4 h-4 text-blue-500" />
                    </div>
                    <span className="font-medium text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {pipeline.name}
                    </span>
                </Link>
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
                    {formatDate(pipeline.created)}
                </span>
            )
        }
    ];

    return (
        <DataView
            items={pipelines}
            loading={loading}
            columns={columns}
            initialView="table"
            renderGrid={(pipeline) => (
                <Link to={`/pipelines/${pipeline.id || pipeline.name}`} className="block">
                    <div className="group p-5 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-500/50 hover:shadow-md transition-all duration-300">
                        <div className="flex items-start justify-between mb-4">
                            <div className="p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-lg group-hover:bg-blue-100 dark:group-hover:bg-blue-900/40 transition-colors">
                                <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                            </div>
                            <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-700 rounded-full text-xs font-medium text-slate-600 dark:text-slate-300">
                                v{pipeline.version || '1.0'}
                            </span>
                        </div>

                        <h3 className="font-semibold text-lg text-slate-900 dark:text-white mb-1 truncate" title={pipeline.name}>
                            {pipeline.name}
                        </h3>

                        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mt-4 pt-4 border-t border-slate-100 dark:border-slate-700/50">
                            <Clock className="w-4 h-4" />
                            <span>Created {formatDate(pipeline.created)}</span>
                        </div>
                    </div>
                </Link>
            )}
            emptyState={
                <div className="text-center py-8">
                    <Activity className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                    <p className="text-slate-500">No pipelines found for this project</p>
                </div>
            }
        />
    );
}
