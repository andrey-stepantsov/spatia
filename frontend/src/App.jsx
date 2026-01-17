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
  const [isHollow, setIsHollow] = useState(false);

  useEffect(() => {
    if (isHollow) {
      setShatterContent(`:intent "Describe intent here"\n(defun new_construct ()\n  ...)`);
    } else {
      setShatterContent('');
    }
  }, [isHollow]);

  const fetchAtoms = useCallback(async () => {
    try {
      const [atomsRes, threadsRes] = await Promise.all([
        axios.get('/api/atoms'),
        axios.get('/api/threads')
      ]);

      const atoms = atomsRes.data;
      const threads = threadsRes.data;

      const newNodes = atoms.map((atom) => ({
        id: atom.id,
        type: 'spatia',
        position: { x: atom.x || 0, y: atom.y || 0 },
        // Use dimensions if known, otherwise React Flow defaults or measures
        width: 250, // Approx width for collision calc
        height: 150, // Approx height
        data: {
          id: atom.id,
          content: atom.content,
          status: atom.status,
          domain: atom.domain || 'generic'
        },
      }));
      setNodes(newNodes);

      const newEdges = threads.map((t) => ({
        id: `e${t.source}-${t.target}`,
        source: t.source,
        target: t.target,
        animated: true,
        style: { stroke: '#4b5563' }
      }));
      setEdges(newEdges);

    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
  }, [setNodes, setEdges]);

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
      console.log("SSE Event received:", event.data);
      // For now, naive refetch on any event.
      // Could accept specific events: 'thread_new', 'update', etc.
      fetchAtoms();
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
    };

    return () => {
      console.log("Closing SSE connection");
      eventSource.close();
    };
  }, [fetchAtoms]);

  const onNodeDragStop = useCallback((event, node) => {
    axios.post('/api/geometry', [{
      atom_id: node.id,
      x: parseInt(node.position.x),
      y: parseInt(node.position.y)
    }]).catch(err => console.error("Sync failed", err));
  }, []);

  // Conflict Fold - Collision Detection
  useEffect(() => {
    const interval = setInterval(() => {
      setNodes((nds) => {
        return nds.map((node) => {
          let hasConflict = false;
          // Simple AABB collision
          const r1 = {
            x: node.position.x,
            y: node.position.y,
            w: node.width || 250,
            h: node.height || 150
          };

          for (const other of nds) {
            if (node.id === other.id) continue;
            const r2 = {
              x: other.position.x,
              y: other.position.y,
              w: other.width || 250,
              h: other.height || 150
            };

            if (
              r1.x < r2.x + r2.w &&
              r1.x + r1.w > r2.x &&
              r1.y < r2.y + r2.h &&
              r1.y + r1.h > r2.y
            ) {
              hasConflict = true;
              break;
            }
          }

          // Apply visual feedback
          if (hasConflict) {
            return {
              ...node,
              style: { ...node.style, zIndex: 999, boxShadow: '0 0 20px 5px rgba(255, 69, 0, 0.7)', border: '2px solid red' },
              className: 'conflict-fold'
            };
          } else {
            // Reset style if no conflict (remove specific fields)
            const newStyle = { ...node.style };
            delete newStyle.zIndex;
            delete newStyle.boxShadow;
            delete newStyle.border;
            return {
              ...node,
              style: newStyle,
              className: ''
            };
          }
        });
      });
    }, 500); // Check every 500ms

    return () => clearInterval(interval);
  }, [setNodes]);

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
          <div className="flex items-center gap-2 mb-2">
            <label className="text-[10px] uppercase font-bold text-gray-400">Hollow Construct</label>
            <div
              data-testid="hollow-switch"
              onClick={() => setIsHollow(!isHollow)}
              className={`w-8 h-4 rounded-full p-0.5 cursor-pointer transition-colors ${isHollow ? 'bg-blue-600' : 'bg-gray-700'}`}
            >
              <div className={`w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${isHollow ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
          </div>
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
