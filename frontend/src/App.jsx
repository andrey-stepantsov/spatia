import React, { useCallback, useEffect, useState } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import axios from 'axios';
import SpatiaNode from './nodes/SpatiaNode';

const nodeTypes = {
  spatia: SpatiaNode,
};

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [shatterPath, setShatterPath] = useState('');
  const [shatterContent, setShatterContent] = useState('');

  const fetchAtoms = useCallback(async () => {
    try {
      const res = await axios.get('/api/atoms');
      const atoms = res.data;

      const newNodes = atoms.map((atom) => ({
        id: atom.id,
        type: 'spatia',
        position: { x: atom.x || 0, y: atom.y || 0 },
        data: {
          id: atom.id,
          content: atom.content,
          status: atom.status,
          domain: atom.domain || 'generic'
        },
      }));

      // Preserve positions of existing nodes if we are just refreshing data?
      // Actually, standard behavior for "sync" is source of truth is DB.
      // But if we are dragging, we don't want to jump back until saved.
      // For now, simple replace.
      setNodes(newNodes);
    } catch (err) {
      console.error("Failed to fetch atoms:", err);
    }
  }, [setNodes]);

  useEffect(() => {
    fetchAtoms();
  }, [fetchAtoms]);

  // SSE Connection for Real-Time Updates
  useEffect(() => {
    console.log("Establishing SSE connection...");
    const eventSource = new EventSource('/api/events');

    eventSource.onopen = () => {
      console.log("SSE connection established");
    };

    eventSource.onmessage = (event) => {
      // For now, any event triggers a refetch to ensure consistency
      // In the future, we can parse event.data to do finer-grained updates
      // const data = JSON.parse(event.data);
      console.log("SSE Event received:", event.data);
      fetchAtoms();
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      // EventSource auto-reconnects, but if we wanted to handle fatal errors we could.
    };

    return () => {
      console.log("Closing SSE connection");
      eventSource.close();
    };
  }, [fetchAtoms]);

  const onNodeDragStop = useCallback((event, node) => {
    // Optimistic persistence: UI is already updated by React Flow.
    // Sync to backend.
    axios.post('/api/geometry', [{
      atom_id: node.id,
      x: parseInt(node.position.x),
      y: parseInt(node.position.y)
    }]).catch(err => console.error("Sync failed", err));
  }, []);

  const handleShatter = async (e) => {
    e.preventDefault();
    if (!shatterPath) return;
    try {
      await axios.post('/api/shatter', { path: shatterPath, content: shatterContent || undefined });
      setShatterPath('');
      setShatterContent('');
      // Short delay to allow DB update
      setTimeout(fetchAtoms, 500);
    } catch (err) {
      alert("Shatter failed: " + err.message);
    }
  };

  return (
    <div className="w-screen h-screen bg-[#050505] text-white overflow-hidden flex flex-col font-sans">
      {/* Shatter Portal */}
      <div className="absolute top-4 left-4 z-50 bg-gray-900/80 backdrop-blur border border-gray-700 shadow-2xl rounded-xl p-4 w-80 transition-opacity hover:opacity-100 opacity-80">
        <h2 className="text-xs font-bold mb-3 text-blue-400 uppercase tracking-widest flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
          Shatter Portal
        </h2>
        <form onSubmit={handleShatter} className="space-y-3">
          <div className="space-y-1">
            <input
              type="text"
              placeholder="Path (e.g. atoms/idea.md)"
              className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono"
              value={shatterPath}
              onChange={(e) => setShatterPath(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <textarea
              placeholder="Content (optional)"
              className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 h-20 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono resize-none"
              value={shatterContent}
              onChange={(e) => setShatterContent(e.target.value)}
            />
          </div>
          <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white rounded-lg py-2 text-xs font-bold tracking-wide transition-all shadow-lg shadow-blue-900/20">
            SHATTER ATOM
          </button>
        </form>
      </div>

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
    </div>
  );
}
