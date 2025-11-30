import React, { useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    Position
} from 'reactflow';
import 'reactflow/dist/style.css';

const initialNodes = [
    {
        id: 'project',
        type: 'input',
        data: { label: 'Project' },
        position: { x: 250, y: 0 },
        sourcePosition: Position.Bottom,
        style: { background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', padding: '10px' }
    },
    {
        id: 'pipelines',
        data: { label: 'Pipelines' },
        position: { x: 100, y: 100 },
        targetPosition: Position.Top,
        sourcePosition: Position.Bottom,
        style: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px' }
    },
    {
        id: 'models',
        data: { label: 'Models' },
        position: { x: 400, y: 100 },
        targetPosition: Position.Top,
        sourcePosition: Position.Bottom,
        style: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px' }
    },
    {
        id: 'runs',
        data: { label: 'Runs' },
        position: { x: 100, y: 200 },
        targetPosition: Position.Top,
        style: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px' }
    },
    {
        id: 'artifacts',
        data: { label: 'Artifacts' },
        position: { x: 400, y: 200 },
        targetPosition: Position.Top,
        style: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px' }
    }
];

const initialEdges = [
    { id: 'e1-2', source: 'project', target: 'pipelines', animated: true, style: { stroke: '#94a3b8' } },
    { id: 'e1-3', source: 'project', target: 'models', animated: true, style: { stroke: '#94a3b8' } },
    { id: 'e2-4', source: 'pipelines', target: 'runs', animated: true, style: { stroke: '#94a3b8' } },
    { id: 'e3-5', source: 'models', target: 'artifacts', animated: true, style: { stroke: '#94a3b8' } }
];

export function ProjectRelations() {
    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);

    return (
        <div className="h-[400px] w-full bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                fitView
                attributionPosition="bottom-right"
            >
                <Background color="#94a3b8" gap={16} size={1} />
                <Controls />
            </ReactFlow>
        </div>
    );
}
