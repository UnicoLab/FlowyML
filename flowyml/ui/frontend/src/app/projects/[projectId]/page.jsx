import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchApi } from '../../../utils/api';
import { ProjectHeader } from './_components/ProjectHeader';
import { ProjectRelations } from './_components/ProjectRelations';
import { ProjectTabs } from './_components/ProjectTabs';
import { ProjectPipelinesList } from './_components/ProjectPipelinesList';
import { ProjectRunsList } from './_components/ProjectRunsList';

export function ProjectDetails() {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        const fetchProjectDetails = async () => {
            try {
                // Fetch project details
                // Assuming API supports fetching by name or ID. projectId from URL might be name.
                const response = await fetchApi(`/api/projects/${projectId}`);
                const projectData = await response.json();
                setProject(projectData);

                // Fetch stats (similar logic to Projects page)
                // This could be optimized into a single API call in the future
                const [runsRes, artifactsRes] = await Promise.all([
                    fetchApi(`/api/runs?project=${projectId}`),
                    fetchApi(`/api/assets?project=${projectId}`)
                ]);

                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();

                const pipelineNames = new Set((runsData.runs || []).map(r => r.pipeline_name));

                setStats({
                    runs: (runsData.runs || []).length,
                    pipelines: pipelineNames.size,
                    artifacts: (artifactsData.artifacts || []).length,
                    models: 0 // Placeholder until models API is ready
                });

            } catch (error) {
                console.error('Failed to fetch project details:', error);
            } finally {
                setLoading(false);
            }
        };

        if (projectId) {
            fetchProjectDetails();
        }
    }, [projectId]);

    const renderContent = () => {
        switch (activeTab) {
            case 'overview':
                return (
                    <div className="space-y-8">
                        <section>
                            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Project Relations</h2>
                            <ProjectRelations />
                        </section>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <section>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Pipelines</h2>
                                <ProjectPipelinesList projectId={projectId} />
                            </section>
                            <section>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Runs</h2>
                                <ProjectRunsList projectId={projectId} />
                            </section>
                        </div>
                    </div>
                );
            case 'pipelines':
                return <ProjectPipelinesList projectId={projectId} />;
            case 'runs':
                return <ProjectRunsList projectId={projectId} />;
            case 'models':
                return <div className="p-8 text-center text-slate-500">Models view coming soon</div>;
            case 'artifacts':
                return <div className="p-8 text-center text-slate-500">Artifacts view coming soon</div>;
            default:
                return null;
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <ProjectHeader project={project} stats={stats} loading={loading} />

            <div>
                <ProjectTabs activeTab={activeTab} onTabChange={setActiveTab} />
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
}
