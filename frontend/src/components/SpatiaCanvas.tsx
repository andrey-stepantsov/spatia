import React, { useCallback } from 'react';
import { ReactFlow, Background, Controls, Node, Edge, OnNodesChange, OnEdgesChange, Connection } from '@xyflow/react';
import SpatiaNode from '../nodes/SpatiaNode';
import EnvelopeNode from '../nodes/EnvelopeNode';
import api from '../utils/api';

const nodeTypes = {
    spatia: SpatiaNode,
    envelope: EnvelopeNode,
};

interface SpatiaCanvasProps {
    nodes: Node[];
    edges: Edge[];
    onNodesChange: OnNodesChange;
    onEdgesChange: OnEdgesChange;
}

export default function SpatiaCanvas({ nodes, edges, onNodesChange, onEdgesChange }: SpatiaCanvasProps) {

    const onNodeDragStop = useCallback((event: React.MouseEvent, node: Node) => {
        // Only sync geometry for atoms (spatia nodes), envelopes are layout boundaries usually fixed?
        // Current App.jsx synchronizes all.
        api.post('/api/geometry', [{
            atom_id: node.id,
            x: parseInt(node.position.x.toString()),
            y: parseInt(node.position.y.toString())
        }]).catch(err => console.error("Sync failed", err));
    }, []);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={nodeTypes}
            fitView
            className="bg-[#050505]"
            colorMode="dark"
        >
            <Background color="#222" gap={24} size={1} />
            <Controls className="bg-gray-900 border-gray-700 fill-gray-400" />
        </ReactFlow>
    );
}
