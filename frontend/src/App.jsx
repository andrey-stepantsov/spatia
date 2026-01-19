import React, { useCallback, useEffect, useState } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from '@xyflow/react';
import api from './utils/api';
import { useSpatiaConnection } from './hooks/useSpatiaConnection';
import SpatiaNode from './nodes/SpatiaNode';
import SpatiaLogo from './components/SpatiaLogo';
import WorkspaceSelector from './components/WorkspaceSelector';
import ConnectionStatus from './components/ConnectionStatus';
import CreateEnvelopeModal from './components/CreateEnvelopeModal';
import ConfirmationModal from './components/ConfirmationModal';

import SpatiaCanvas from './components/SpatiaCanvas';
import EnvelopeNode from './nodes/EnvelopeNode';

const nodeTypes = {
  spatia: SpatiaNode,
  envelope: EnvelopeNode,
};

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [envelopes, setEnvelopes] = useState([]);

  // UI States
  const [shatterPath, setShatterPath] = useState('');
  const [shatterContent, setShatterContent] = useState('');
  const [isHollow, setIsHollow] = useState(false);
  const [isGhostMode, setIsGhostMode] = useState(false);

  // Modal States
  const [showEnvelopeModal, setShowEnvelopeModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [envelopeToDelete, setEnvelopeToDelete] = useState(null);
  const [showSummonModal, setShowSummonModal] = useState(false);
  const [summonTarget, setSummonTarget] = useState(null);
  const [showReviveModal, setShowReviveModal] = useState(false);
  const [reviveTarget, setReviveTarget] = useState(null);

  // Toast State
  const [toast, setToast] = useState(null);

  // Handle Error
  const handleError = useCallback((msg) => {
    setToast({ type: 'error', message: msg, code: 'ERROR' });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const handleSuccess = useCallback((msg) => {
    setToast({ type: 'success', message: msg, code: 'SUCCESS' });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // Event Handler
  const handleEvent = useCallback((event) => {
    if (event.type === 'echo_response') {
      const now = Date.now();
      const rtt = now - event.client_timestamp;
      const msg = `RTT: ${rtt}ms | Svr: ${new Date(event.server_timestamp).toLocaleTimeString()}`;
      setToast({ type: 'info', message: msg, code: 'ECHO' });
      setTimeout(() => setToast(null), 5000);
    }
  }, []);

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

      // Handle Envelope Deletion
      const handleDeleteEnvelope = (id) => {
        setEnvelopeToDelete(id);
        setShowDeleteModal(true);
      };

      // Handle Summon
      const handleSummon = (id, model) => {
        setSummonTarget({ id, model });
        setShowSummonModal(true);
      };

      // Handle Revive
      const handleRevive = (id) => {
        setReviveTarget(id);
        setShowReviveModal(true);
      };



      const envelopeNodes = envelopesData.map(env => ({
        id: env.id,
        type: 'envelope', // Use custom node
        position: { x: env.x, y: env.y },
        style: {
          width: env.w,
          height: env.h,
          zIndex: 0,
        },
        data: {
          id: env.id,
          domain: env.domain,
          onDelete: handleDeleteEnvelope
        },
        draggable: false,
        selectable: true,
        connectable: false
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
            domain: atom.domain || 'generic',
            onSummon: handleSummon,
            onRevive: handleRevive,
            onError: handleError
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
  }, [setNodes, setEdges, isGhostMode, handleError]);

  // Use Connection Hook
  const { status, workspace } = useSpatiaConnection(fetchAtoms, handleEvent);

  // Echo Keyboard Shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd+E or Ctrl+E
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault();
        const payload = `Echo test ${Date.now()}`;
        api.post('/api/echo', { timestamp: Date.now(), payload })
          .catch(err => handleError("Echo failed: " + err.message));
        setToast({ type: 'info', message: "Sending Echo...", code: 'PING' });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleError]);

  // Initial Fetch
  useEffect(() => {
    fetchAtoms();
  }, [fetchAtoms]);

  useEffect(() => {
    if (isHollow) {
      setShatterContent(`:intent "Describe intent here"\n(defun new_construct ()\n  ...)`);
    } else {
      setShatterContent('');
    }
  }, [isHollow]);

  const onNodeDragStop = useCallback((event, node) => {
    api.post('/api/geometry', [{
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
          if (envelopes.some(e => e.id === node.id)) return node;

          let hasConflict = false;
          const r1 = {
            x: node.position.x,
            y: node.position.y,
            w: node.width || 250,
            h: node.height || 150
          };

          // Node-Node
          for (const other of nds) {
            if (node.id === other.id) continue;
            if (envelopes.some(e => e.id === other.id)) continue;

            const r2 = {
              x: other.position.x,
              y: other.position.y,
              w: other.width || 250,
              h: other.height || 150
            };

            if (r1.x < r2.x + r2.w && r1.x + r1.w > r2.x && r1.y < r2.y + r2.h && r1.y + r1.h > r2.y) {
              hasConflict = true;
              break;
            }
          }

          // Envelope Policy
          if (!hasConflict) {
            const cx = r1.x + r1.w / 2;
            const cy = r1.y + r1.h / 2;
            for (const env of envelopes) {
              if (String(node.id) === String(env.id)) continue;
              if (cx >= env.x && cx <= env.x + env.w && cy >= env.y && cy <= env.y + env.h) {
                const nodeDomain = node.data.domain || 'generic';
                const envDomain = env.domain;
                if (nodeDomain !== envDomain) hasConflict = true;
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
  }, [setNodes, envelopes]);

  const handleShatter = async (e) => {
    e.preventDefault();
    console.log('[APP-DEBUG] handleShatter called', { path: shatterPath, content: shatterContent });
    if (!shatterPath) return;
    try {
      console.log('[APP-DEBUG] Calling api.post(/api/shatter)');
      await api.post('/api/shatter', { path: shatterPath, content: shatterContent || undefined });
      console.log('[APP-DEBUG] Shatter success');
      setShatterPath(''); setShatterContent('');
      handleSuccess("Atom shattered successfully");
    } catch (err) {
      console.error('[APP-DEBUG] Shatter error', err);
      handleError("Shatter failed: " + err.message);
    }
  };

  const createEnvelope = async (data) => {
    console.log('[APP-DEBUG] createEnvelope called', data);
    try {
      await api.post('/api/envelopes', { ...data, x: 100, y: 100, w: 300, h: 300 });
      console.log('[APP-DEBUG] Envelope create success');
      fetchAtoms();
      handleSuccess("Envelope created");
    } catch (err) {
      console.error('[APP-DEBUG] Envelope create error', err);
      handleError("Failed to create envelope: " + err.message);
    }
  };

  const confirmDeleteEnvelope = async () => {
    if (envelopeToDelete) {
      try {
        await api.delete(`/api/envelopes/${envelopeToDelete}`); // Fixed string template syntax
        setEnvelopeToDelete(null);
        setShowDeleteModal(false);
        fetchAtoms();
        handleSuccess("Envelope deleted");
      } catch (err) {
        handleError("Failed to delete: " + err.message);
      }
    }
  };

  const confirmSummon = async () => {
    if (summonTarget) {
      try {
        await api.post('/api/summon', { atom_id: summonTarget.id, model: summonTarget.model });
        setSummonTarget(null);
        setShowSummonModal(false);
        handleSuccess("Summoning initiated...");
      } catch (err) {
        handleError("Summon failed: " + err.message);
      }
    }
  };

  const confirmRevive = async () => {
    if (reviveTarget) {
      try {
        await api.post('/api/revive', { fossil_id: reviveTarget });
        setReviveTarget(null);
        setShowReviveModal(false);
        handleSuccess("Revive initiated...");
      } catch (err) {
        handleError("Revive failed: " + err.message);
      }
    }
  };

  const getToastStyle = (type) => {
    switch (type) {
      case 'success': return 'bg-green-900/90 border-green-500';
      case 'info': return 'bg-blue-900/90 border-blue-500';
      default: return 'bg-red-900/90 border-red-500';
    }
  };

  return (
    <div className="w-screen h-screen bg-[#050505] text-white overflow-hidden flex flex-col font-sans relative">
      <ConnectionStatus status={status} workspace={workspace} />

      {toast && (
        <div className={`absolute top-16 left-1/2 transform -translate-x-1/2 z-[100] border text-white px-6 py-3 rounded-lg shadow-2xl backdrop-blur animate-in fade-in slide-in-from-top-4 ${getToastStyle(toast.type)}`}>
          <div className="font-bold text-sm mb-1">{toast.code || (toast.type === 'error' ? "ERROR" : "INFO")}</div>
          <div className="text-xs opacity-90">{toast.message}</div>
        </div>
      )}

      <SpatiaLogo className="absolute top-6 right-6 w-12 h-12 z-50 opacity-50 hover:opacity-100 transition-opacity cursor-pointer" theme="dark" />
      <WorkspaceSelector onError={handleError} onSuccess={handleSuccess} />

      {/* Tools Bar */}
      <div className="absolute top-6 right-24 z-50 flex gap-2">
        <button
          onClick={() => setShowEnvelopeModal(true)}
          className="bg-green-900/50 hover:bg-green-700/50 text-green-300 px-3 py-1 rounded text-xs font-mono border border-green-700/50 backdrop-blur"
        >
          + BOUNDARY
        </button>
      </div>

      {/* Background Envelopes Layer */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden"></div>

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

      <SpatiaCanvas
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
      />

      {/* Modals */}
      <CreateEnvelopeModal
        isOpen={showEnvelopeModal}
        onClose={() => setShowEnvelopeModal(false)}
        onCreate={createEnvelope}
      />

      <ConfirmationModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={confirmDeleteEnvelope}
        title="Delete Boundary"
        message={`Are you sure you want to delete boundary "${envelopeToDelete}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
      />

      <ConfirmationModal
        isOpen={showSummonModal}
        onClose={() => setShowSummonModal(false)}
        onConfirm={confirmSummon}
        title="Summon Intelligence"
        message={`This will invoke a specialized AI Agent (${summonTarget?.model}) to implement the construct. Proceed?`}
        confirmLabel="Summon"
        variant="primary"
      />

      <ConfirmationModal
        isOpen={showReviveModal}
        onClose={() => setShowReviveModal(false)}
        onConfirm={confirmRevive}
        title="Revive Fossil"
        message={`Are you sure you want to revive fossil "${reviveTarget}"? The current active version will be archived.`}
        confirmLabel="Revive"
        variant="primary"
      />
    </div>
  );
}
