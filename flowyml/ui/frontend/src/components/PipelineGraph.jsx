import React, { useCallback, useMemo, useEffect } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
    Handle,
    Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { CheckCircle, XCircle, Clock, Loader, Database, Box, BarChart2, FileText, Layers } from 'lucide-react';
import dagre from 'dagre';

const stepNodeWidth = 240;
const stepNodeHeight = 100;
const artifactNodeWidth = 180;
const artifactNodeHeight = 50;

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const isHorizontal = direction === 'LR';
    dagreGraph.setGraph({ rankdir: direction, nodesep: 80, ranksep: 100 });

    nodes.forEach((node) => {
        const width = node.type === 'artifact' ? artifactNodeWidth : stepNodeWidth;
        const height = node.type === 'artifact' ? artifactNodeHeight : stepNodeHeight;
        dagreGraph.setNode(node.id, { width, height });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    nodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        node.targetPosition = isHorizontal ? 'left' : 'top';
        node.sourcePosition = isHorizontal ? 'right' : 'bottom';

        // Shift to center the node
        const width = node.type === 'artifact' ? artifactNodeWidth : stepNodeWidth;
        const height = node.type === 'artifact' ? artifactNodeHeight : stepNodeHeight;

        node.position = {
            x: nodeWithPosition.x - width / 2,
            y: nodeWithPosition.y - height / 2,
        };

        return node;
    });

    return { nodes, edges };
};

export function PipelineGraph({ dag, steps, selectedStep, onStepSelect }) {
    // Transform DAG data to ReactFlow format with Artifact Nodes
    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        if (!dag || !dag.nodes) return { nodes: [], edges: [] };

        const nodes = [];
        const edges = [];
        const artifactIds = new Set();
        const createdArtifacts = new Map(); // Map name -> id

        // Helper to get or create artifact node
        const getArtifactId = (name) => {
            if (createdArtifacts.has(name)) return createdArtifacts.get(name);
            const id = `artifact-${name}`;
            if (!artifactIds.has(id)) {
                nodes.push({
                    id: id,
                    type: 'artifact',
                    data: { label: name }
                });
                artifactIds.add(id);
                createdArtifacts.set(name, id);
            }
            return id;
        };

        // 1. Create Step Nodes and Connections
        dag.nodes.forEach(node => {
            const stepData = steps?.[node.id] || {};
            const status = stepData.success ? 'success' : stepData.error ? 'failed' : stepData.running ? 'running' : 'pending';

            nodes.push({
                id: node.id,
                type: 'step',
                data: {
                    label: node.name,
                    status,
                    duration: stepData.duration,
                    cached: stepData.cached,
                    selected: selectedStep === node.id
                }
            });

            // Input Edges: Artifact -> Step
            node.inputs?.forEach(inputName => {
                const artifactId = getArtifactId(inputName);
                edges.push({
                    id: `e-${artifactId}-${node.id}`,
                    source: artifactId,
                    target: node.id,
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: '#94a3b8', strokeWidth: 2 },
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' }
                });
            });

            // Output Edges: Step -> Artifact
            node.outputs?.forEach(outputName => {
                const artifactId = getArtifactId(outputName);
                edges.push({
                    id: `e-${node.id}-${artifactId}`,
                    source: node.id,
                    target: artifactId,
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: '#94a3b8', strokeWidth: 2 },
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' }
                });
            });
        });

        return { nodes, edges };
    }, [dag, steps, selectedStep]);

    const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
        return getLayoutedElements(initialNodes, initialEdges, 'TB');
    }, [initialNodes, initialEdges]);

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

    // Update nodes when selection changes or layout changes
    useEffect(() => {
        setNodes(layoutedNodes.map(node => {
            if (node.type === 'step') {
                return {
                    ...node,
                    data: {
                        ...node.data,
                        selected: selectedStep === node.id
                    }
                };
            }
            return node;
        }));
        setEdges(layoutedEdges);
    }, [layoutedNodes, layoutedEdges, selectedStep, setNodes, setEdges]);

    const onNodeClick = useCallback((event, node) => {
        if (node.type === 'step' && onStepSelect) {
            onStepSelect(node.id);
        }
    }, [onStepSelect]);

    const nodeTypes = useMemo(() => ({
        step: CustomStepNode,
        artifact: CustomArtifactNode
    }), []);

    return (
        <div className="w-full h-full bg-slate-50/50 rounded-xl border border-slate-200 overflow-hidden">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
                minZoom={0.2}
                maxZoom={1.5}
                defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
                fitViewOptions={{ padding: 0.2 }}
            >
                <Background color="#e2e8f0" gap={20} size={1} />
                <Controls className="bg-white border border-slate-200 shadow-sm rounded-lg" />
                <MiniMap
                    nodeColor={n => n.type === 'step' ? '#3b82f6' : '#cbd5e1'}
                    maskColor="rgba(241, 245, 249, 0.7)"
                    className="bg-white border border-slate-200 shadow-sm rounded-lg"
                />
            </ReactFlow>
        </div>
    );
}

function CustomStepNode({ data }) {
    const statusConfig = {
        success: {
            icon: <CheckCircle size={18} />,
            color: 'text-emerald-600',
            bg: 'bg-white',
            border: 'border-emerald-500',
            ring: 'ring-emerald-200',
            shadow: 'shadow-emerald-100'
        },
        failed: {
            icon: <XCircle size={18} />,
            color: 'text-rose-600',
            bg: 'bg-white',
            border: 'border-rose-500',
            ring: 'ring-rose-200',
            shadow: 'shadow-rose-100'
        },
        running: {
            icon: <Loader size={18} className="animate-spin" />,
            color: 'text-amber-600',
            bg: 'bg-white',
            border: 'border-amber-500',
            ring: 'ring-amber-200',
            shadow: 'shadow-amber-100'
        },
        pending: {
            icon: <Clock size={18} />,
            color: 'text-slate-400',
            bg: 'bg-slate-50',
            border: 'border-slate-300',
            ring: 'ring-slate-200',
            shadow: 'shadow-slate-100'
        }
    };

    const config = statusConfig[data.status] || statusConfig.pending;

    return (
        <div
            className={`
                relative px-4 py-3 rounded-lg border-2 transition-all duration-200
                ${config.bg} ${config.border}
                ${data.selected ? `ring-4 ${config.ring} shadow-lg` : `hover:shadow-md ${config.shadow}`}
            `}
            style={{ width: stepNodeWidth, height: stepNodeHeight }}
        >
            <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />

            <div className="flex flex-col h-full justify-between">
                <div className="flex items-start gap-3">
                    <div className={`p-1.5 rounded-md bg-slate-50 border border-slate-100 ${config.color}`}>
                        {config.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                        <h3 className="font-bold text-slate-900 text-sm truncate" title={data.label}>
                            {data.label}
                        </h3>
                        <p className="text-xs text-slate-500 capitalize">{data.status}</p>
                    </div>
                </div>

                {data.duration !== undefined && (
                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-1">
                        <span className="text-xs text-slate-400 font-mono">
                            {data.duration.toFixed(2)}s
                        </span>
                        {data.cached && (
                            <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded uppercase tracking-wider">
                                Cached
                            </span>
                        )}
                    </div>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
        </div>
    );
}


function CustomArtifactNode({ data }) {
    // Determine icon and styling based on artifact type (inferred from label)
    const getArtifactStyle = (label) => {
        const lowerLabel = label.toLowerCase();

        if (lowerLabel.includes('model') || lowerLabel.includes('weights')) {
            return {
                icon: Box,
                bgColor: 'bg-purple-100 dark:bg-purple-900/30',
                borderColor: 'border-purple-400 dark:border-purple-600',
                iconColor: 'text-purple-600 dark:text-purple-400',
                textColor: 'text-purple-900 dark:text-purple-100'
            };
        }
        if (lowerLabel.includes('feature') || lowerLabel.includes('train_set') || lowerLabel.includes('test_set')) {
            return {
                icon: Layers,
                bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
                borderColor: 'border-emerald-400 dark:border-emerald-600',
                iconColor: 'text-emerald-600 dark:text-emerald-400',
                textColor: 'text-emerald-900 dark:text-emerald-100'
            };
        }
        if (lowerLabel.includes('data') || lowerLabel.includes('batch') || lowerLabel.includes('set')) {
            return {
                icon: Database,
                bgColor: 'bg-blue-100 dark:bg-blue-900/30',
                borderColor: 'border-blue-400 dark:border-blue-600',
                iconColor: 'text-blue-600 dark:text-blue-400',
                textColor: 'text-blue-900 dark:text-blue-100'
            };
        }
        if (lowerLabel.includes('metrics') || lowerLabel.includes('report') || lowerLabel.includes('status')) {
            return {
                icon: BarChart2,
                bgColor: 'bg-orange-100 dark:bg-orange-900/30',
                borderColor: 'border-orange-400 dark:border-orange-600',
                iconColor: 'text-orange-600 dark:text-orange-400',
                textColor: 'text-orange-900 dark:text-orange-100'
            };
        }
        if (lowerLabel.includes('image') || lowerLabel.includes('docker')) {
            return {
                icon: Box,
                bgColor: 'bg-cyan-100 dark:bg-cyan-900/30',
                borderColor: 'border-cyan-400 dark:border-cyan-600',
                iconColor: 'text-cyan-600 dark:text-cyan-400',
                textColor: 'text-cyan-900 dark:text-cyan-100'
            };
        }

        // Default style
        return {
            icon: FileText,
            bgColor: 'bg-slate-100 dark:bg-slate-800',
            borderColor: 'border-slate-300 dark:border-slate-600',
            iconColor: 'text-slate-500 dark:text-slate-400',
            textColor: 'text-slate-700 dark:text-slate-300'
        };
    };

    const style = getArtifactStyle(data.label);
    const Icon = style.icon;

    return (
        <div
            className={`px-3 py-2 rounded-lg ${style.bgColor} border-2 ${style.borderColor} flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all min-w-[140px]`}
            style={{ height: artifactNodeHeight }}
        >
            <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />

            <Icon size={14} className={style.iconColor} />
            <span className={`text-xs font-semibold ${style.textColor} truncate max-w-[100px]`} title={data.label}>
                {data.label}
            </span>

            <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
        </div>
    );
}
