import React, { useCallback, useEffect, useState } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import api from './utils/api'; // Use new API utility
import SpatiaNode from './nodes/SpatiaNode';
import EnvelopeNode from './nodes/EnvelopeNode';
import SpatiaLogo from './components/SpatiaLogo';
import WorkspaceSelector from './components/WorkspaceSelector';
import ConnectionStatus from './components/ConnectionStatus';
import { useSpatiaConnection } from './hooks/useSpatiaConnection';

const nodeTypes = {
  spatia: SpatiaNode,
  envelope: EnvelopeNode,
};

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [envelopes, setEnvelopes] = useState([]);
  const [shatterPath, setShatterPath] = useState('');
  const [shatterContent, setShatterContent] = useState('');
  const [isHollow, setIsHollow] = useState(false);
  const [isGhostMode, setIsGhostMode] = useState(false);

  // New Error State
  const [errorToast, setErrorToast] = useState(null);

  const fetchAtoms = useCallback(async () => {
    try {
      const [atomsRes, threadsRes, envelopesRes] = await Promise.all([
        api.get('/api/atoms'),
        api.get('/api/threads'),
        api.get('/api/envelopes').catch(() => ({ data: [] }))
      ]);

      const atoms = atomsRes.data;
      const threads = threadsRes.data;
      const envelopesData = envelopesRes.data;

      setEnvelopes(envelopesData);

      const envelopeNodes = envelopesData.map(env => ({
        id: env.id,
        type: 'envelope', // Custom Type
        position: { x: env.x, y: env.y },
        style: {
          width: env.w,
          height: env.h,
          zIndex: -1,
        },
        data: {
          id: env.id,
          domain: env.domain
        },
        draggable: true, // Allow dragging
        selectable: true,
      }));

      const newNodes = atoms
        .filter(atom => isGhostMode || parseInt(atom.status) !== 4)
        .map((atom) => ({
          id: atom.id,
          type: 'spatia',
          position: { x: atom.x || 0, y: atom.y || 0 },
          width: 250,
          height: 150,
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
      // We don't necessarily alert here as it happens during disconnects
    }
  }, [setNodes, setEdges, isGhostMode]);

  // Use the new Hook
  const { status, workspace } = useSpatiaConnection(fetchAtoms);

  // Initial fetch when connected
  useEffect(() => {
    if (status === 'connected') {
      fetchAtoms();
    }
  }, [status, fetchAtoms]);

  // ... (isHollow useEffect logic unchanged) ...
  useEffect(() => {
    if (isHollow) {
      setShatterContent(`:intent "Describe intent here"\n(defun new_construct ()\n  ...)`);
    } else {
      setShatterContent('');
    }
  }, [isHollow]);

  const onNodeDragStop = useCallback((event, node) => {
    // Check if Envelope or Atom
    if (node.type === 'envelope') {
      api.put(`/api/envelopes/${node.id}`, {
        x: parseInt(node.position.x),
        y: parseInt(node.position.y),
        w: parseInt(node.measured?.width || node.style.width),
        h: parseInt(node.measured?.height || node.style.height)
      }).catch(err => console.error("Env update failed", err));
    } else {
      api.post('/api/geometry', [{
        atom_id: node.id,
        x: parseInt(node.position.x),
        y: parseInt(node.position.y)
      }]).catch(err => console.error("Sync failed", err));
    }
  }, []);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge(params, eds));
    api.post('/api/threads', { source: params.source, target: params.target })
      .catch(err => {
        console.error("Thread create failed", err);
        setErrorToast(err);
        setTimeout(() => setErrorToast(null), 5000);
      });
  }, [setEdges]);

  const onNodeResizeStop = useCallback((event, params) => {
    // Note: older signature support or different library version might need adjustment
  }, []);

  // Simplified collision detection (only envelope checks)
  useEffect(() => {
    const interval = setInterval(() => {
      setNodes((nds) => {
        return nds.map((node) => {
          if (node.type === 'envelope') return node;

          let hasConflict = false;
          const r1 = {
            x: node.position.x, y: node.position.y,
            w: node.width || 250, h: node.height || 150
          };

          // 1. Node-Node
          for (const other of nds) {
            if (node.id === other.id) continue;
            if (other.type === 'envelope') continue;

            const r2 = {
              x: other.position.x, y: other.position.y,
              w: other.width || 250, h: other.height || 150
            };
            if (r1.x < r2.x + r2.w && r1.x + r1.w > r2.x && r1.y < r2.y + r2.h && r1.y + r1.h > r2.y) {
              hasConflict = true; break;
            }
          }

          // 2. Envelope Policy
          if (!hasConflict) {
            const cx = r1.x + r1.w / 2;
            const cy = r1.y + r1.h / 2;

            for (const env of nds) {
              if (env.type !== 'envelope') continue;

              // Use env.style.width/height or measured
              const ew = parseInt(env.style.width) || env.measured?.width || 100;
              const eh = parseInt(env.style.height) || env.measured?.height || 100;

              if (cx >= env.position.x && cx <= env.position.x + ew &&
                cy >= env.position.y && cy <= env.position.y + eh) {

                const nodeDomain = node.data.domain || 'generic';
                const envDomain = env.data.domain || 'generic';

                if (nodeDomain !== envDomain) {
                  hasConflict = true;
                }
              }
            }
          }

          if (hasConflict && !node.className?.includes('conflict-fold')) {
            return { ...node, style: { ...node.style, zIndex: 999, boxShadow: '0 0 20px 5px rgba(255, 69, 0, 0.7)', border: '2px solid red' }, className: 'conflict-fold' };
          } else if (!hasConflict && node.className?.includes('conflict-fold')) {
            const newStyle = { ...node.style };
            delete newStyle.zIndex; delete newStyle.boxShadow; delete newStyle.border;
            return { ...node, style: newStyle, className: '' };
          }
          return node;
        });
      });
    }, 500);
    return () => clearInterval(interval);
  }, [setNodes]);

  const handleShatter = async (e) => {
    e.preventDefault();
    if (!shatterPath) return;
    try {
      await api.post('/api/shatter', { path: shatterPath, content: shatterContent || undefined });
      setShatterPath(''); setShatterContent('');
    } catch (err) {
      console.error("Shatter Error:", err);
      setErrorToast(err);
      setTimeout(() => setErrorToast(null), 5000);
    }
  };

  const handleNewEnvelope = async () => {
    const id = prompt("Envelope ID (unique):", `env-${Date.now()}`);
    if (!id) return;
    try {
      await api.post('/api/envelopes', {
        id,
        domain: 'generic',
        x: 100, y: 100, w: 300, h: 300
      });
    } catch (err) {
      setErrorToast(err);
      setTimeout(() => setErrorToast(null), 5000);
    }
  };

  return (
    <div className="w-screen h-screen bg-[#050505] text-white overflow-hidden flex flex-col font-sans relative">
      <ConnectionStatus status={status} workspace={workspace} />

      {/* Error Toast */}
      {errorToast && (
        <div className="absolute top-16 left-1/2 transform -translate-x-1/2 z-[100] bg-red-900/90 border border-red-500 text-white px-6 py-3 rounded-lg shadow-2xl backdrop-blur animate-in fade-in slide-in-from-top-4">
          <div className="font-bold text-sm mb-1">
            {errorToast.code || "ERROR"}
          </div>
          <div className="text-xs opacity-90">
            {errorToast.message}
          </div>
        </div>
      )}

      <SpatiaLogo className="absolute top-6 right-6 w-12 h-12 z-50 opacity-50 hover:opacity-100 transition-opacity cursor-pointer" theme="dark" />
      <WorkspaceSelector />

      {/* Tools Bar */}
      <div className="absolute top-6 right-24 z-50 flex gap-2">
        <button
          onClick={handleNewEnvelope}
          className="bg-green-900/50 hover:bg-green-700/50 text-green-300 px-3 py-1 rounded text-xs font-mono border border-green-700/50 backdrop-blur"
        >
          + BOUNDARY
        </button>
      </div>

      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden"></div>

      <div className="absolute top-4 left-4 z-50 bg-gray-900/80 backdrop-blur border border-gray-700 shadow-2xl rounded-xl p-4 w-80 transition-opacity hover:opacity-100 opacity-80">
        <h2 className="text-xs font-bold mb-3 text-blue-400 uppercase tracking-widest flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
          Shatter Portal
        </h2>
        <form onSubmit={handleShatter} className="space-y-3">
          {/* Same form content ... */}
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
          <button type="submit" disabled={status !== 'connected'} className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg py-2 text-xs font-bold tracking-wide transition-all shadow-lg shadow-blue-900/20">
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
        onConnect={onConnect}
        onNodeResizeStop={(event, type, node) => {
          if (node?.type === 'envelope') {
            // ...
          }
        }}
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

