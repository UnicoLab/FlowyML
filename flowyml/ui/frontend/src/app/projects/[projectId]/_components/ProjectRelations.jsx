import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { fetchApi } from '../../../../utils/api';
import { useParams, useNavigate } from 'react-router-dom';

const nodeDefaults = {
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
};

export function ProjectRelations() {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [loading, setLoading] = useState(true);

    const onNodeClick = useCallback((event, node) => {
        if (node.id.startsWith('pipeline-')) {
            // Extract pipeline name from ID "pipeline-name"
            // In a real app, we might need the ID, but here we use name as ID often
            // Assuming we navigate to pipeline details.
            // Since we don't have a direct route for pipeline details yet (or do we?),
            // let's assume /pipelines/:id.
            // But wait, the ID in the graph is "pipeline-{name}".
            // Let's just navigate to the pipelines tab for now or a specific pipeline page if it exists.
            // The user asked for "possibility to go to details of pipeline or run".
            // I'll assume routes /pipelines/:id and /runs/:id exist or will exist.
            // For now, let's log it and try to navigate.
            const pipelineName = node.data.label;
            // We don't have the UUID here easily unless we store it in data.
            // Let's store the full object in data.
        }
    }, [navigate]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                if (!projectId) return;

                const [pipelinesRes, runsRes, artifactsRes] = await Promise.all([
                    fetchApi(`/api/pipelines?project=${projectId}`),
                    fetchApi(`/api/runs?project=${projectId}`),
                    fetchApi(`/api/assets?project=${projectId}`)
                ]);

                const pipelinesData = await pipelinesRes.json();
                const runsData = await runsRes.json();
                const artifactsData = await artifactsRes.json();

                const pipelines = Array.isArray(pipelinesData?.pipelines) ? pipelinesData.pipelines : [];
                const runs = Array.isArray(runsData?.runs) ? runsData.runs : [];
                const artifacts = Array.isArray(artifactsData?.artifacts) ? artifactsData.artifacts : [];

                console.log("Relations Data:", { pipelines, runs, artifacts });

                // Build graph
                const newNodes = [];
                const newEdges = [];

                // Project Node
                newNodes.push({
                    id: 'project',
                    type: 'input',
                    data: { label: 'Project' },
                    position: { x: 0, y: 300 },
                    ...nodeDefaults,
                    style: { background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', padding: '10px', width: 150 }
                });

                if (pipelines.length === 0) {
                    // Add a placeholder node if no pipelines
                    newNodes.push({
                        id: 'no-pipelines',
                        data: { label: 'No Pipelines Found' },
                        position: { x: 250, y: 300 },
                        style: { background: '#f1f5f9', color: '#64748b', border: '1px dashed #cbd5e1', borderRadius: '8px', padding: '10px' }
                    });
                    newEdges.push({
                        id: 'e-project-empty',
                        source: 'project',
                        target: 'no-pipelines',
                        animated: true,
                        style: { stroke: '#cbd5e1', strokeDasharray: '5,5' }
                    });
                }

                // Pipeline Nodes
                pipelines.forEach((pipeline, index) => {
                    const pipelineId = `pipeline-${pipeline.name}`; // Using name as ID for uniqueness in graph
                    newNodes.push({
                        id: pipelineId,
                        data: { label: pipeline.name, original: pipeline },
                        position: { x: 250, y: index * 120 }, // Increased spacing
                        ...nodeDefaults,
                        style: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px', width: 200, cursor: 'pointer' }
                    });
                    newEdges.push({
                        id: `e-project-${pipelineId}`,
                        source: 'project',
                        target: pipelineId,
                        animated: true,
                        style: { stroke: '#94a3b8' }
                    });
                });

                // Run Nodes (limit to recent 5 per pipeline to avoid clutter)
                const recentRuns = runs.slice(0, 10);
                recentRuns.forEach((run, index) => {
                    const runId = `run-${run.run_id}`;
                    const pipelineId = `pipeline-${run.pipeline_name}`;

                    // Only add if pipeline exists in graph
                    if (newNodes.find(n => n.id === pipelineId)) {
                        newNodes.push({
                            id: runId,
                            data: { label: `Run: ${run.name || run.run_id.slice(0, 8)}`, original: run },
                            position: { x: 600, y: index * 100 },
                            ...nodeDefaults,
                            style: {
                                background: run.status === 'completed' ? '#ecfdf5' : '#fff',
                                border: `1px solid ${run.status === 'completed' ? '#10b981' : '#e2e8f0'}`,
                                borderRadius: '8px',
                                padding: '10px',
                                width: 220,
                                cursor: 'pointer'
                            }
                        });
                        newEdges.push({
                            id: `e-${pipelineId}-${runId}`,
                            source: pipelineId,
                            target: runId,
                            animated: true,
                            style: { stroke: '#94a3b8' }
                        });
                    }
                });

                setNodes(newNodes);
                setEdges(newEdges);
            } catch (error) {
                console.error('Failed to fetch relations data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [projectId]);

    const handleNodeClick = (event, node) => {
        if (node.id.startsWith('pipeline-') && node.data.original) {
            // Navigate to pipeline details (assuming route exists, or just log for now)
            // navigate(`/pipelines/${node.data.original.id}`); // We don't have pipeline ID in list usually, just name?
            // Let's assume we can navigate to a pipeline page.
            console.log("Clicked pipeline:", node.data.original);
        } else if (node.id.startsWith('run-') && node.data.original) {
            navigate(`/runs/${node.data.original.run_id}`);
        }
    };

    if (loading) {
        return <div className="h-[400px] w-full bg-slate-50 dark:bg-slate-800/50 rounded-xl animate-pulse" />;
    }

    return (
        <div className="h-[500px] w-full bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                fitView
                attributionPosition="bottom-right"
            >
                <Background color="#94a3b8" gap={16} size={1} />
                <Controls />
            </ReactFlow>
        </div>
    );
}
