import React, { useEffect, useState, useCallback } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    Panel,
    MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { Database, Box, BarChart2, FileText, Activity, Loader2, Info } from 'lucide-react';
import { fetchApi } from '../utils/api';

// Custom node component for artifacts
function ArtifactNode({ data }) {
    const getIconAndStyle = (artifactType) => {
        const configs = {
            model: {
                icon: Box,
                gradient: 'from-purple-500 to-pink-500',
                bg: 'bg-purple-50 dark:bg-purple-900/20',
                border: 'border-purple-400',
                text: 'text-purple-700 dark:text-purple-300'
            },
            dataset: {
                icon: Database,
                gradient: 'from-blue-500 to-cyan-500',
                bg: 'bg-blue-50 dark:bg-blue-900/20',
                border: 'border-blue-400',
                text: 'text-blue-700 dark:text-blue-300'
            },
            metrics: {
                icon: BarChart2,
                gradient: 'from-emerald-500 to-teal-500',
                bg: 'bg-emerald-50 dark:bg-emerald-900/20',
                border: 'border-emerald-400',
                text: 'text-emerald-700 dark:text-emerald-300'
            },
            default: {
                icon: FileText,
                gradient: 'from-slate-500 to-slate-600',
                bg: 'bg-slate-50 dark:bg-slate-800',
                border: 'border-slate-400',
                text: 'text-slate-700 dark:text-slate-300'
            }
        };
        return configs[artifactType] || configs.default;
    };

    const config = getIconAndStyle(data.artifact_type);
    const Icon = config.icon;

    return (
        <div
            className={`px-4 py-3 rounded-xl ${config.bg} border-2 ${config.border} shadow-lg hover:shadow-xl transition-all cursor-pointer min-w-[180px]`}
            onClick={() => data.onClick?.(data)}
        >
            <div className="flex items-center gap-3">
                <div className={`p-2 bg-gradient-to-br ${config.gradient} rounded-lg text-white`}>
                    <Icon size={18} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className={`font-semibold text-sm ${config.text} truncate`} title={data.label}>
                        {data.label}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                        {data.artifact_type}
                    </div>
                </div>
            </div>
            {data.metadata?.properties && Object.keys(data.metadata.properties).length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-500">
                        {Object.keys(data.metadata.properties).length} properties
                    </div>
                </div>
            )}
        </div>
    );
}

// Custom node component for runs
function RunNode({ data }) {
    const statusColors = {
        completed: 'bg-emerald-100 dark:bg-emerald-900/20 border-emerald-400 text-emerald-700 dark:text-emerald-300',
        failed: 'bg-rose-100 dark:bg-rose-900/20 border-rose-400 text-rose-700 dark:text-rose-300',
        running: 'bg-blue-100 dark:bg-blue-900/20 border-blue-400 text-blue-700 dark:text-blue-300',
        default: 'bg-slate-100 dark:bg-slate-800 border-slate-400 text-slate-700 dark:text-slate-300'
    };

    const status = data.metadata?.status || 'unknown';
    const colorClass = statusColors[status] || statusColors.default;

    return (
        <div
            className={`px-4 py-2 rounded-lg border-2 ${colorClass} shadow-md hover:shadow-lg transition-all min-w-[150px]`}
        >
            <div className="flex items-center gap-2">
                <Activity size={16} />
                <div>
                    <div className="font-semibold text-sm truncate" title={data.label}>
                        {data.label}
                    </div>
                    {data.metadata?.pipeline_name && (
                        <div className="text-xs opacity-75">
                            {data.metadata.pipeline_name}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

const nodeTypes = {
    artifact: ArtifactNode,
    run: RunNode
};

// Auto-layout using dagre
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const nodeWidth = 200;
    const nodeHeight = 100;

    dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 80 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - nodeWidth / 2,
                y: nodeWithPosition.y - nodeHeight / 2,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};

export function AssetLineageGraph({ projectId, onNodeClick }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchLineage = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const url = projectId
                ? `/api/assets/lineage?project=${encodeURIComponent(projectId)}&depth=3`
                : '/api/assets/lineage?depth=2';

            const res = await fetchApi(url);
            const data = await res.json();

            // Transform API data to ReactFlow format
            const flowNodes = data.nodes.map(node => ({
                id: node.id,
                type: node.type,
                data: {
                    label: node.label,
                    artifact_type: node.artifact_type,
                    metadata: node.metadata,
                    onClick: onNodeClick
                },
                position: { x: 0, y: 0 } // Will be set by layout
            }));

            const flowEdges = data.edges.map(edge => ({
                id: edge.id,
                source: edge.source,
                target: edge.target,
                label: edge.label,
                type: edge.type === 'produces' ? 'default' : 'step',
                animated: edge.type === 'produces',
                style: {
                    stroke: edge.type === 'produces' ? '#3b82f6' : '#94a3b8',
                    strokeWidth: 2
                },
                markerEnd: {
                    type: 'arrowclosed',
                    color: edge.type === 'produces' ? '#3b82f6' : '#94a3b8'
                }
            }));

            // Apply auto-layout
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                flowNodes,
                flowEdges
            );

            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        } catch (err) {
            console.error('Failed to fetch lineage:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [projectId, onNodeClick, setNodes, setEdges]);

    useEffect(() => {
        fetchLineage();
    }, [fetchLineage]);

    if (loading) {
        return (
            <div className="h-[600px] flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-xl">
                <div className="text-center">
                    <Loader2 className="animate-spin h-12 w-12 text-primary-600 mx-auto mb-4" />
                    <p className="text-slate-600 dark:text-slate-400">Loading artifact lineage...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="h-[600px] flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-xl">
                <div className="text-center">
                    <Info className="h-12 w-12 text-rose-600 mx-auto mb-4" />
                    <p className="text-rose-600 font-semibold mb-2">Failed to load lineage</p>
                    <p className="text-slate-600 dark:text-slate-400 text-sm">{error}</p>
                </div>
            </div>
        );
    }

    if (nodes.length === 0) {
        return (
            <div className="h-[600px] flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700">
                <div className="text-center">
                    <Database className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-600 dark:text-slate-400 font-semibold mb-2">No artifact lineage found</p>
                    <p className="text-slate-500 text-sm">Run some pipelines to generate artifact relationships</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-[600px] border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
            >
                <Background color="#94a3b8" gap={16} />
                <Controls />
                <Panel position="top-right" className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700">
                    <div className="text-xs space-y-2">
                        <div className="font-semibold text-slate-900 dark:text-white mb-2">Legend</div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded bg-purple-500"></div>
                            <span className="text-slate-600 dark:text-slate-400">Models</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded bg-blue-500"></div>
                            <span className="text-slate-600 dark:text-slate-400">Datasets</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded bg-emerald-500"></div>
                            <span className="text-slate-600 dark:text-slate-400">Metrics</span>
                        </div>
                    </div>
                </Panel>
            </ReactFlow>
        </div>
    );
}
