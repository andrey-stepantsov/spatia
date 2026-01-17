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
  const [envelopes, setEnvelopes] = useState([]);
  const [shatterPath, setShatterPath] = useState('');
  const [shatterContent, setShatterContent] = useState('');
  const [isHollow, setIsHollow] = useState(false);
  const [isGhostMode, setIsGhostMode] = useState(false);

  useEffect(() => {
    if (isHollow) {
      setShatterContent(`:intent "Describe intent here"\n(defun new_construct ()\n  ...)`);
    } else {
      setShatterContent('');
    }
  }, [isHollow]);

  const fetchAtoms = useCallback(async () => {
    try {
      const [atomsRes, threadsRes, envelopesRes] = await Promise.all([
        axios.get('/api/atoms'),
        axios.get('/api/threads'),
        axios.get('/api/envelopes').catch(() => ({ data: [] })) // Graceful fail
      ]);

      const atoms = atomsRes.data;
      const threads = threadsRes.data;
      const envelopesData = envelopesRes.data;

      setEnvelopes(envelopesData);

      const envelopeNodes = envelopesData.map(env => ({
        id: env.id,
        type: 'default',
        position: { x: env.x, y: env.y },
        style: {
          width: env.w,
          height: env.h,
          backgroundColor: 'rgba(0, 255, 0, 0.1)',
          border: '1px dashed #0f0',
          zIndex: -1,
          color: 'rgba(0, 255, 0, 0.5)',
          fontSize: '10px'
        },
        data: { label: `${env.id} (${env.domain || 'Generic'})` },
        draggable: false,
        selectable: false,
        connectable: false
      }));

      const newNodes = atoms
        .filter(atom => isGhostMode || parseInt(atom.status) !== 4)
        .map((atom) => ({
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
      setNodes([...envelopeNodes, ...newNodes]);

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
  }, [setNodes, setEdges, isGhostMode]);

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
      // Determine if we should refetch
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'db_update' || data.type === 'update' || data.type === 'thread_new') {
          fetchAtoms();
        }
      } catch (e) {
        // Fallback if not JSON
        fetchAtoms();
      }
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
          // Skip collision check for Envelopes themselves
          // We can identify them by checking if they are in the envelopes list
          const isEnvelope = envelopes.some(e => e.id === node.id);
          if (isEnvelope) return node;

          let hasConflict = false;
          // Simple AABB collision with other nodes
          const r1 = {
            x: node.position.x,
            y: node.position.y,
            w: node.width || 250,
            h: node.height || 150
          };

          // 1. Node-Node Collision
          for (const other of nds) {
            if (node.id === other.id) continue;

            // Skip collision if 'other' is an envelope
            const isOtherEnvelope = envelopes.some(e => e.id === other.id);
            if (isOtherEnvelope) continue;

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

          // 2. Envelope Policy Collision
          // Check if center of node is inside an envelope
          const cx = r1.x + r1.w / 2;
          const cy = r1.y + r1.h / 2;

          for (const env of envelopes) {
            // Debug ID match
            console.log(`Comparing '${node.id}' === '${env.id}'`);
            if (String(node.id) === String(env.id)) continue;

            // env: x, y, w, h
            if (cx >= env.x && cx <= env.x + env.w &&
              cy >= env.y && cy <= env.y + env.h) {

              // Inside Envelope. Check Domain.
              // If Envelope domain is different from Node domain (and Node domain is not generic/undefined?)
              // Let's assume strict matching for now.
              const nodeDomain = node.data.domain || 'generic';
              const envDomain = env.domain;

              if (nodeDomain !== envDomain) {
                console.log(`Conflict: Node ${node.id} (${nodeDomain}) in Envelope ${env.id} (${envDomain})`);
                hasConflict = true;
              }
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
  }, [setNodes, envelopes]); // Re-run when envelopes change

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
    <div className="w-screen h-screen bg-[#050505] text-white overflow-hidden flex flex-col font-sans relative">
      {/* Background Envelopes Layer */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* We need to apply same transform as ReactFlow viewport to match positions? 
              Actually, ReactFlow has a Background component. 
              Ideally envelopes should be NODES in ReactFlow but 'group' type or simple background nodes.
              Or we can just use ReactFlow nodes with zIndex -1.
              
              Let's try creating them as ReactFlow nodes in fetchAtoms instead? 
              That ensures they pan/zoom correctly.
              
              RE-PLAN: Add envelopes to 'nodes' list with a special type or style.
          */}
      </div>

      {/* Shatter Portal */}
      <div className="absolute top-4 left-4 z-50 bg-gray-900/80 backdrop-blur border border-gray-700 shadow-2xl rounded-xl p-4 w-80 transition-opacity hover:opacity-100 opacity-80">
        <h2 className="text-xs font-bold mb-3 text-blue-400 uppercase tracking-widest flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
          Shatter Portal
        </h2>
        <form onSubmit={handleShatter} className="space-y-3">
          <div className="flex items-center justify-between">
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

            {/* Ghost Mode Toggle */}
            <div className="flex items-center gap-2 mb-2">
              <label className="text-[10px] uppercase font-bold text-gray-400">Ghost Mode</label>
              <div
                data-testid="ghost-mode-switch"
                onClick={() => setIsGhostMode(!isGhostMode)}
                className={`w-8 h-4 rounded-full p-0.5 cursor-pointer transition-colors ${isGhostMode ? 'bg-purple-600' : 'bg-gray-700'}`}
              >
                <div className={`w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${isGhostMode ? 'translate-x-4' : 'translate-x-0'}`} />
              </div>
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

