import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { FlaskConical, Clock, Tag, PlayCircle } from 'lucide-react';
import { formatDate } from '../../../../utils/date';

export function ProjectExperimentsList({ projectId }) {
    const [experiments, setExperiments] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchExperiments = async () => {
            try {
                const response = await fetchApi(`/api/experiments?project=${projectId}`);
                const data = await response.json();

                if (data.experiments && Array.isArray(data.experiments)) {
                    setExperiments(data.experiments);
                } else {
                    setExperiments([]);
                }
            } catch (error) {
                console.error('Failed to fetch experiments:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchExperiments();
        }
    }, [projectId]);

    const columns = [
        {
            key: 'name',
            label: 'Name',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-purple-500" />
                    <div>
                        <div className="font-medium text-slate-900 dark:text-white">{item.name}</div>
                        {item.description && (
                            <div className="text-xs text-slate-500 truncate max-w-[200px]">{item.description}</div>
                        )}
                    </div>
                </div>
            )
        },
        {
            key: 'run_count',
            label: 'Runs',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-1">
                    <PlayCircle className="w-3 h-3 text-slate-400" />
                    <span>{item.run_count || 0}</span>
                </div>
            )
        },
        {
            key: 'created_at',
            label: 'Created',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-1 text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(item.created_at)}</span>
                </div>
            )
        },
        {
            key: 'tags',
            label: 'Tags',
            render: (item) => (
                <div className="flex flex-wrap gap-1">
                    {Object.entries(item.tags || {}).map(([key, value]) => (
                        <span key={key} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                            <Tag className="w-3 h-3 mr-1" />
                            {key}: {value}
                        </span>
                    ))}
                </div>
            )
        }
    ];

    return (
        <DataView
            items={experiments}
            loading={loading}
            columns={columns}
            initialView="table"
            searchKeys={['name', 'description']}
            renderGrid={(item) => (
                <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                                <FlaskConical className="w-5 h-5 text-purple-500" />
                            </div>
                            <div>
                                <h3 className="font-medium text-slate-900 dark:text-white">{item.name}</h3>
                                <div className="text-xs text-slate-500 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatDate(item.created_at)}
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                            <PlayCircle className="w-3 h-3" />
                            {item.run_count || 0} runs
                        </div>
                    </div>

                    {item.description && (
                        <p className="text-sm text-slate-600 dark:text-slate-400 mb-3 line-clamp-2">
                            {item.description}
                        </p>
                    )}

                    <div className="flex flex-wrap gap-1">
                        {Object.entries(item.tags || {}).map(([key, value]) => (
                            <span key={key} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                                {key}: {value}
                            </span>
                        ))}
                    </div>
                </div>
            )}
            emptyState={
                <div className="text-center py-12">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 mb-4">
                        <FlaskConical className="w-6 h-6 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">No experiments found</h3>
                    <p className="text-slate-500">
                        Create an experiment to track your model development.
                    </p>
                </div>
            }
        />
    );
}
