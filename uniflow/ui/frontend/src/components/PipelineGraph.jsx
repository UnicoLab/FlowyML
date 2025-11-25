import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { CheckCircle, XCircle, Clock, Loader, Database, Box, BarChart2 } from 'lucide-react';
import dagre from 'dagre';
import { Handle, Position } from 'reactflow';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 280;
const nodeHeight = 160;

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
    const isHorizontal = direction === 'LR';
    dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 150 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
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
        node.position = {
            x: nodeWithPosition.x - nodeWidth / 2,
            y: nodeWithPosition.y - nodeHeight / 2,
        };

        return node;
    });

    return { nodes, edges };
};

export function PipelineGraph({ dag, steps, selectedStep, onStepSelect }) {
    // Transform DAG data to ReactFlow format
    const initialNodes = useMemo(() => {
        if (!dag || !dag.nodes) return [];

        return dag.nodes.map((node) => {
            const stepData = steps?.[node.id] || {};
            const status = stepData.success ? 'success' : stepData.error ? 'failed' : 'pending';

            return {
                id: node.id,
                type: 'custom',
                data: {
                    label: node.name,
                    status,
                    duration: stepData.duration,
                    cached: stepData.cached,
                    inputs: node.inputs,
                    outputs: node.outputs,
                    selected: selectedStep === node.id
                },
            };
        });
    }, [dag, steps, selectedStep]);

    const initialEdges = useMemo(() => {
        if (!dag || !dag.edges) return [];

        return dag.edges.map((edge, index) => {
            // Find the artifact being passed
            const sourceNode = dag.nodes.find(n => n.id === edge.source);
            const targetNode = dag.nodes.find(n => n.id === edge.target);

            // Find common artifacts
            const artifacts = sourceNode?.outputs?.filter(output =>
                targetNode?.inputs?.includes(output)
            ) || [];

            return {
                id: `e${index}-${edge.source}-${edge.target}`,
                source: edge.source,
                target: edge.target,
                type: 'smoothstep',
                animated: true,
                label: artifacts.length > 0 ? artifacts.join(', ') : undefined,
                labelStyle: {
                    fill: '#475569',
                    fontWeight: 600,
                    fontSize: 12,
                },
                labelBgStyle: {
                    fill: '#f1f5f9',
                    fillOpacity: 0.9,
                },
                labelBgPadding: [8, 4],
                labelBgBorderRadius: 4,
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 24,
                    height: 24,
                    color: '#3b82f6',
                },
                style: {
                    strokeWidth: 3,
                    stroke: '#3b82f6',
                },
            };
        });
    }, [dag]);

    const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
        return getLayoutedElements(initialNodes, initialEdges, 'TB');
    }, [initialNodes, initialEdges]);

    // Debug logging
    React.useEffect(() => {
        console.log('PipelineGraph - DAG:', dag);
        console.log('PipelineGraph - Initial Nodes:', initialNodes);
        console.log('PipelineGraph - Initial Edges:', initialEdges);
        console.log('PipelineGraph - Layouted Edges:', layoutedEdges);
    }, [dag, initialNodes, initialEdges, layoutedEdges]);

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

    // Update nodes when selection changes
    React.useEffect(() => {
        setNodes((nds) =>
            nds.map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    selected: selectedStep === node.id
                }
            }))
        );
    }, [selectedStep, setNodes]);

    const onNodeClick = useCallback((event, node) => {
        if (onStepSelect) {
            onStepSelect(node.id);
        }
    }, [onStepSelect]);

    // Custom node component
    const nodeTypes = useMemo(() => ({
        custom: CustomStepNode
    }), []);

    return (
        <div className="w-full h-full bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border-2 border-slate-200 overflow-hidden shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
                minZoom={0.3}
                maxZoom={1.5}
                defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
                fitViewOptions={{ padding: 0.3 }}
            >
                <Background
                    color="#cbd5e1"
                    gap={20}
                    size={1.5}
                    variant="dots"
                />
                <Controls
                    className="bg-white border-2 border-slate-200 rounded-lg shadow-lg"
                    showInteractive={false}
                />
            </ReactFlow>
        </div>
    );
}

function CustomStepNode({ data }) {
    const statusConfig = {
        success: {
            icon: <CheckCircle size={24} />,
            color: 'text-emerald-600',
            bg: 'bg-emerald-50',
            border: 'border-emerald-400',
            ring: 'ring-emerald-400',
            glow: 'shadow-emerald-200'
        },
        failed: {
            icon: <XCircle size={24} />,
            color: 'text-rose-600',
            bg: 'bg-rose-50',
            border: 'border-rose-400',
            ring: 'ring-rose-400',
            glow: 'shadow-rose-200'
        },
        running: {
            icon: <Loader size={24} className="animate-spin" />,
            color: 'text-amber-600',
            bg: 'bg-amber-50',
            border: 'border-amber-400',
            ring: 'ring-amber-400',
            glow: 'shadow-amber-200'
        },
        pending: {
            icon: <Clock size={24} />,
            color: 'text-slate-600',
            bg: 'bg-slate-50',
            border: 'border-slate-300',
            ring: 'ring-slate-400',
            glow: 'shadow-slate-200'
        }
    };

    const config = statusConfig[data.status] || statusConfig.pending;

    return (
        <div
            className={`
                px-5 py-4 rounded-xl border-2 bg-white shadow-xl transition-all duration-200
                ${config.border}
                ${data.selected ? `ring-4 ${config.ring} scale-105 ${config.glow}` : `hover:shadow-2xl hover:scale-102 ${config.glow}`}
                cursor-pointer
            `}
            style={{ width: nodeWidth }}
        >
            {/* Connection Handles */}
            <Handle
                type="target"
                position={Position.Top}
                className="w-3 h-3 !bg-primary-500 !border-2 !border-white"
            />
            <Handle
                type="source"
                position={Position.Bottom}
                className="w-3 h-3 !bg-primary-500 !border-2 !border-white"
            />

            {/* Header */}
            <div className="flex items-start gap-3 mb-3">
                <div className={`p-2.5 rounded-lg ${config.bg} ${config.color} flex-shrink-0`}>
                    {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-slate-900 text-base leading-tight mb-1">{data.label}</h3>
                    {data.duration !== undefined && (
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-0.5 rounded">
                                {data.duration.toFixed(2)}s
                            </span>
                            {data.cached && (
                                <span className="text-xs text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded">
                                    ⚡ cached
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* I/O Section */}
            <div className="space-y-2 text-xs">
                {data.inputs?.length > 0 && (
                    <div className="flex items-start gap-2">
                        <span className="text-slate-400 font-semibold min-w-[40px]">IN:</span>
                        <div className="flex-1 flex flex-wrap gap-1">
                            {data.inputs.map(input => (
                                <span key={input} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium">
                                    <Database size={12} />
                                    {input}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
                {data.outputs?.length > 0 && (
                    <div className="flex items-start gap-2">
                        <span className="text-slate-400 font-semibold min-w-[40px]">OUT:</span>
                        <div className="flex-1 flex flex-wrap gap-1">
                            {data.outputs.map(output => (
                                <span key={output} className="inline-flex items-center gap-1 bg-purple-50 text-purple-700 px-2 py-0.5 rounded font-medium">
                                    {output === 'metrics' ? <BarChart2 size={12} /> : <Box size={12} />}
                                    {output}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
