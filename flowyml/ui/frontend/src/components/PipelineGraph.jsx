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
import { CheckCircle, XCircle, Clock, Loader, Database, Box, BarChart2, FileText, Layers, GitFork, User } from 'lucide-react';
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

export function PipelineGraph({ dag, steps, selectedStep, onStepSelect, onArtifactSelect }) {
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

        // Map execution groups to colors
        const groupColors = {};
        const groupColorPalette = [
            { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-400 dark:border-blue-500', text: 'text-blue-700 dark:text-blue-300', badge: 'bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300' },
            { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-400 dark:border-purple-500', text: 'text-purple-700 dark:text-purple-300', badge: 'bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300' },
            { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-400 dark:border-green-500', text: 'text-green-700 dark:text-green-300', badge: 'bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300' },
            { bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-400 dark:border-orange-500', text: 'text-orange-700 dark:text-orange-300', badge: 'bg-orange-100 dark:bg-orange-800 text-orange-700 dark:text-orange-300' },
            { bg: 'bg-pink-50 dark:bg-pink-900/20', border: 'border-pink-400 dark:border-pink-500', text: 'text-pink-700 dark:text-pink-300', badge: 'bg-pink-100 dark:bg-pink-800 text-pink-700 dark:text-pink-300' },
            { bg: 'bg-cyan-50 dark:bg-cyan-900/20', border: 'border-cyan-400 dark:border-cyan-500', text: 'text-cyan-700 dark:text-cyan-300', badge: 'bg-cyan-100 dark:bg-cyan-800 text-cyan-700 dark:text-cyan-300' },
        ];

        // First pass: collect all execution groups
        const executionGroups = new Set();
        dag.nodes.forEach(node => {
            const stepData = steps?.[node.id] || {};
            if (stepData.execution_group) {
                executionGroups.add(stepData.execution_group);
            }
        });

        // Assign colors to groups
        Array.from(executionGroups).forEach((group, idx) => {
            groupColors[group] = groupColorPalette[idx % groupColorPalette.length];
        });

        // 1. Create Step Nodes and Connections
        dag.nodes.forEach(node => {
            const stepData = steps?.[node.id] || {};
            const status = stepData.success ? 'success' : stepData.error ? 'failed' : stepData.running ? 'running' : 'pending';
            const executionGroup = stepData.execution_group;
            const groupColor = executionGroup ? groupColors[executionGroup] : null;

            // Detect special step types
            const isConditional = node.name.toLowerCase().startsWith('if') || node.name.includes('condition');
            const isHumanInLoop = node.name.toLowerCase().includes('approve') || node.name.includes('review') || node.name.includes('human');


            nodes.push({
                id: node.id,
                type: 'step',
                data: {
                    label: node.name,
                    status,
                    duration: stepData.duration,
                    cached: stepData.cached,
                    selected: selectedStep === node.id,
                    execution_group: executionGroup,
                    groupColor: groupColor,
                    isConditional: isConditional,
                    isHumanInLoop: isHumanInLoop,
                    inputs: node.inputs || [],
                    outputs: node.outputs || []
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
        } else if (node.type === 'artifact' && onArtifactSelect) {
            onArtifactSelect(node.data.label);
        }
    }, [onStepSelect, onArtifactSelect]);

    const nodeTypes = useMemo(() => ({
        step: CustomStepNode,
        artifact: CustomArtifactNode
    }), []);

    return (
        <div className="w-full h-full bg-slate-50/50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
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
            color: 'text-emerald-600 dark:text-emerald-400',
            bg: 'bg-white dark:bg-slate-800',
            border: 'border-emerald-500 dark:border-emerald-500',
            ring: 'ring-emerald-200 dark:ring-emerald-900',
            shadow: 'shadow-emerald-100 dark:shadow-none'
        },
        failed: {
            icon: <XCircle size={18} />,
            color: 'text-rose-600 dark:text-rose-400',
            bg: 'bg-white dark:bg-slate-800',
            border: 'border-rose-500 dark:border-rose-500',
            ring: 'ring-rose-200 dark:ring-rose-900',
            shadow: 'shadow-rose-100 dark:shadow-none'
        },
        running: {
            icon: <Loader size={18} className="animate-spin" />,
            color: 'text-amber-600 dark:text-amber-400',
            bg: 'bg-white dark:bg-slate-800',
            border: 'border-amber-500 dark:border-amber-500',
            ring: 'ring-amber-200 dark:ring-amber-900',
            shadow: 'shadow-amber-100 dark:shadow-none animate-pulse ring-2 ring-amber-400/50'
        },
        pending: {
            icon: <Clock size={18} />,
            color: 'text-slate-400 dark:text-slate-500',
            bg: 'bg-slate-50 dark:bg-slate-800/50',
            border: 'border-slate-300 dark:border-slate-700',
            ring: 'ring-slate-200 dark:ring-slate-800',
            shadow: 'shadow-slate-100 dark:shadow-none'
        }
    };

    const config = statusConfig[data.status] || statusConfig.pending;
    const groupColor = data.groupColor;
    const hasGroup = data.execution_group && groupColor;

    // Special styling for conditional nodes
    if (data.isConditional) {
        return (
            <div
                className={`
                    relative px-4 py-3 rounded-xl border-2 transition-all duration-200 flex flex-col justify-center items-center text-center
                    ${config.bg} border-violet-400 dark:border-violet-500
                    ${data.selected ? 'ring-4 ring-violet-200 dark:ring-violet-900 shadow-lg scale-105' : 'hover:shadow-md'}
                    transform rotate-0
                `}
                style={{ width: 180, height: 100 }} // Slightly different size for conditional
            >
                <Handle type="target" position={Position.Top} className="!bg-violet-400 !w-3 !h-3" />

                <div className="bg-violet-100 dark:bg-violet-900/50 p-2 rounded-full mb-2">
                    <GitFork size={20} className="text-violet-600 dark:text-violet-300" />
                </div>
                <div className="font-bold text-xs text-violet-900 dark:text-violet-100 uppercase tracking-wider mb-1">Decision</div>
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 line-clamp-2 leading-tight">
                    {data.label}
                </div>

                {data.status !== 'pending' && (
                    <div className={`absolute -right-2 -top-2 rounded-full p-1 border-2 border-white dark:border-slate-900 ${config.bg}`}>
                        <div className={config.color}>{config.icon}</div>
                    </div>
                )}

                <Handle type="source" position={Position.Bottom} className="!bg-violet-400 !w-3 !h-3" />
            </div>
        );
    }

    return (
        <div
            className={`
                relative px-4 py-3 rounded-lg border-2 transition-all duration-200
                ${hasGroup ? groupColor.bg : config.bg}
                ${hasGroup ? groupColor.border : config.border}
                ${data.selected ? `ring-4 ${config.ring} shadow-lg` : `hover:shadow-md ${config.shadow}`}
                ${data.isHumanInLoop ? 'border-dashed border-amber-400 dark:border-amber-500' : ''}
            `}
            style={{ width: stepNodeWidth, height: stepNodeHeight }}
        >
            <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />

            <div className="flex flex-col h-full justify-between">
                <div className="flex items-start gap-3">
                    <div className={`p-1.5 rounded-md bg-slate-50 border border-slate-100 ${config.color} relative`}>
                        {config.icon}
                        {data.isHumanInLoop && (
                            <div className="absolute -bottom-1 -right-1 bg-amber-100 text-amber-600 rounded-full p-0.5 border border-white" title="Human in the loop">
                                <User size={10} />
                            </div>
                        )}
                    </div>
                    <div className="min-w-0 flex-1">
                        <h3 className={`font-bold text-sm truncate ${hasGroup ? groupColor.text : 'text-slate-900 dark:text-white'}`} title={data.label}>
                            {data.label}
                        </h3>
                        <div className="flex items-center gap-2 mt-0.5">
                            <p className="text-xs text-slate-500 capitalize">{data.status}</p>
                            {hasGroup && (
                                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${groupColor.badge}`}>
                                    {data.execution_group}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-1">
                    {data.duration !== undefined ? (
                        <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
                            <Clock size={10} /> {data.duration.toFixed(2)}s
                        </span>
                    ) : <span className="text-xs text-slate-300">-</span>}

                    {data.cached && (
                        <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-full uppercase tracking-wider shadow-sm">
                            <Database size={8} /> Cached
                        </span>
                    )}
                </div>
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
                bgColor: 'bg-purple-100 dark:bg-purple-900/40',
                borderColor: 'border-purple-300 dark:border-purple-600',
                iconColor: 'text-purple-600 dark:text-purple-400',
                textColor: 'text-purple-900 dark:text-purple-100'
            };
        }
        if (lowerLabel.includes('feature') || lowerLabel.includes('train_set') || lowerLabel.includes('test_set')) {
            return {
                icon: Layers,
                bgColor: 'bg-emerald-100 dark:bg-emerald-900/40',
                borderColor: 'border-emerald-300 dark:border-emerald-600',
                iconColor: 'text-emerald-600 dark:text-emerald-400',
                textColor: 'text-emerald-900 dark:text-emerald-100'
            };
        }
        if (lowerLabel.includes('data') || lowerLabel.includes('batch') || lowerLabel.includes('set')) {
            return {
                icon: Database,
                bgColor: 'bg-blue-100 dark:bg-blue-900/40',
                borderColor: 'border-blue-300 dark:border-blue-600',
                iconColor: 'text-blue-600 dark:text-blue-400',
                textColor: 'text-blue-900 dark:text-blue-100'
            };
        }
        if (lowerLabel.includes('metrics') || lowerLabel.includes('report') || lowerLabel.includes('status')) {
            return {
                icon: BarChart2,
                bgColor: 'bg-orange-100 dark:bg-orange-900/40',
                borderColor: 'border-orange-300 dark:border-orange-600',
                iconColor: 'text-orange-600 dark:text-orange-400',
                textColor: 'text-orange-900 dark:text-orange-100'
            };
        }
        if (lowerLabel.includes('image') || lowerLabel.includes('docker')) {
            return {
                icon: Box,
                bgColor: 'bg-cyan-100 dark:bg-cyan-900/40',
                borderColor: 'border-cyan-300 dark:border-cyan-600',
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
            className={`px-4 py-1.5 rounded-full ${style.bgColor} border ${style.borderColor} flex items-center justify-center gap-2 shadow-sm hover:shadow-md transition-all min-w-[120px] cursor-pointer`}
            style={{ height: 36 }}
        >
            <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />

            <Icon size={12} className={style.iconColor} />
            <span className={`text-[11px] font-bold ${style.textColor} truncate max-w-[120px] uppercase tracking-wide`} title={data.label}>
                {data.label}
            </span>

            <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
        </div>
    );
}
