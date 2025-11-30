import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchApi } from '../../../utils/api';
import { ProjectHeader } from './_components/ProjectHeader';
import { ProjectHierarchy } from './_components/ProjectHierarchy';
import { ProjectTabs } from './_components/ProjectTabs';
import { ProjectPipelinesList } from './_components/ProjectPipelinesList';
import { ProjectRunsList } from './_components/ProjectRunsList';
import { ProjectArtifactsList } from './_components/ProjectArtifactsList';
import { ProjectExperimentsList } from './_components/ProjectExperimentsList';
import { ErrorBoundary } from '../../../components/ui/ErrorBoundary';
import { ProjectMetricsPanel } from './_components/ProjectMetricsPanel';

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
                const response = await fetchApi(`/api/projects/${projectId}`);
                const projectData = await response.json();
                console.log('Project data:', projectData);

                // Ensure pipelines is an array
                if (projectData.pipelines && !Array.isArray(projectData.pipelines)) {
                    projectData.pipelines = [];
                }

                setProject(projectData);

                // Fetch stats with higher limits to get accurate counts
                const [runsRes, artifactsRes, experimentsRes] = await Promise.all([
                    fetchApi(`/api/runs?project=${projectId}&limit=1000`),
                    fetchApi(`/api/assets?project=${projectId}&limit=1000`),
                    fetchApi(`/api/experiments?project=${projectId}`)
                ]);

                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();
                const experimentsData = await experimentsRes.json();

                console.log('Runs data:', runsData);
                console.log('Artifacts data:', artifactsData);
                console.log('Experiments data:', experimentsData);

                // Ensure we have arrays before mapping
                const runs = Array.isArray(runsData?.runs) ? runsData.runs : (Array.isArray(runsData) ? runsData : []);
                const artifacts = Array.isArray(artifactsData?.assets) ? artifactsData.assets : (Array.isArray(artifactsData?.artifacts) ? artifactsData.artifacts : []);
                const experiments = Array.isArray(experimentsData?.experiments) ? experimentsData.experiments : [];

                const pipelineNames = new Set(runs.map(r => r.pipeline_name).filter(Boolean));
                const models = artifacts.filter(a => a.type === 'Model');

                setStats({
                    runs: runs.length,
                    pipelines: pipelineNames.size,
                    artifacts: artifacts.length,
                    models: models.length,
                    experiments: experiments.length
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
                        <ErrorBoundary>
                            <section>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Project Structure</h2>
                                <ProjectHierarchy projectId={projectId} />
                            </section>
                        </ErrorBoundary>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <ErrorBoundary>
                                <section>
                                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Pipelines</h2>
                                    <ProjectPipelinesList projectId={projectId} />
                                </section>
                            </ErrorBoundary>

                            <ErrorBoundary>
                                <section>
                                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Recent Runs</h2>
                                    <ProjectRunsList projectId={projectId} />
                                </section>
                            </ErrorBoundary>
                        </div>

                        <ErrorBoundary>
                            <section>
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Production Metrics</h2>
                                    <p className="text-sm text-slate-500 dark:text-slate-400">
                                        Live data from /api/projects/{projectId}/metrics
                                    </p>
                                </div>
                                <ProjectMetricsPanel projectId={projectId} />
                            </section>
                        </ErrorBoundary>
                    </div>
                );
            case 'pipelines':
                return (
                    <ErrorBoundary>
                        <ProjectPipelinesList projectId={projectId} />
                    </ErrorBoundary>
                );
            case 'runs':
                return (
                    <ErrorBoundary>
                        <ProjectRunsList projectId={projectId} />
                    </ErrorBoundary>
                );
            case 'experiments':
                return (
                    <ErrorBoundary>
                        <ProjectExperimentsList projectId={projectId} />
                    </ErrorBoundary>
                );
            case 'models':
                return (
                    <ErrorBoundary>
                        <ProjectArtifactsList projectId={projectId} type="Model" />
                    </ErrorBoundary>
                );
            case 'artifacts':
                return (
                    <ErrorBoundary>
                        <ProjectArtifactsList projectId={projectId} />
                    </ErrorBoundary>
                );
            case 'metrics':
                return (
                    <ErrorBoundary>
                        <ProjectMetricsPanel projectId={projectId} />
                    </ErrorBoundary>
                );
            default:
                return null;
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <ErrorBoundary>
                <ProjectHeader project={project} stats={stats} loading={loading} />
            </ErrorBoundary>

            <div>
                <ProjectTabs activeTab={activeTab} onTabChange={setActiveTab} />
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
}
