import React, { useState, useEffect } from 'react';
import { fetchApi } from '../../../../utils/api';
import { DataView } from '../../../../components/ui/DataView';
import { FileBox, Database, Box, Clock, Tag } from 'lucide-react';
import { formatDate } from '../../../../utils/date';

export function ProjectArtifactsList({ projectId, type }) {
    const [artifacts, setArtifacts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchArtifacts = async () => {
            try {
                let url = `/api/assets?project=${projectId}`;
                if (type) {
                    url += `&asset_type=${type}`;
                }

                const response = await fetchApi(url);
                const data = await response.json();

                if (data.assets && Array.isArray(data.assets)) {
                    setArtifacts(data.assets);
                } else {
                    setArtifacts([]);
                }
            } catch (error) {
                console.error('Failed to fetch artifacts:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchArtifacts();
        }
    }, [projectId, type]);

    const columns = [
        {
            key: 'name',
            label: 'Name',
            sortable: true,
            render: (item) => (
                <div className="flex items-center gap-2">
                    <FileBox className="w-4 h-4 text-blue-500" />
                    <span className="font-medium text-slate-900 dark:text-white">{item.name}</span>
                </div>
            )
        },
        {
            key: 'type',
            label: 'Type',
            sortable: true,
            render: (item) => (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                    {item.type}
                </span>
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
            key: 'path',
            label: 'Path',
            render: (item) => (
                <span className="text-xs text-slate-400 font-mono truncate max-w-[200px] block" title={item.path}>
                    {item.path}
                </span>
            )
        }
    ];

    return (
        <DataView
            items={artifacts}
            loading={loading}
            columns={columns}
            initialView="table"
            searchKeys={['name', 'type', 'path']}
            renderGrid={(item) => (
                <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                <FileBox className="w-5 h-5 text-blue-500" />
                            </div>
                            <div>
                                <h3 className="font-medium text-slate-900 dark:text-white">{item.name}</h3>
                                <span className="text-xs text-slate-500">{item.type}</span>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            <span>{formatDate(item.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Database className="w-4 h-4" />
                            <span className="truncate font-mono text-xs">{item.path}</span>
                        </div>
                    </div>
                </div>
            )}
            emptyState={
                <div className="text-center py-12">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 mb-4">
                        <Box className="w-6 h-6 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">No artifacts found</h3>
                    <p className="text-slate-500">
                        {type ? `No ${type}s have been created yet.` : 'No artifacts have been created yet.'}
                    </p>
                </div>
            }
        />
    );
}
