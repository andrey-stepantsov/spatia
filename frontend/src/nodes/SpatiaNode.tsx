import React, { memo, useState, useCallback } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import api from '../utils/api';

// Define Props Interface
interface SpatiaNodeData extends Record<string, unknown> {
    id: string;
    content: string;
    status: number; // 0: Shadow, 1: Claim, 2: Witnessed, 3: Endorsed, 4: Fossil
    domain?: string;
    onError?: (msg: string) => void;
    onSummon?: (id: string, model: string) => void;
    onRevive?: (id: string) => void;
}

const SpatiaNode: React.FC<NodeProps<SpatiaNodeData>> = ({ data }) => {
    const { content, status, domain, id } = data;
    const [showLogs, setShowLogs] = useState(false);
    const [logs, setLogs] = useState<string | null>(null);
    const [showPortals, setShowPortals] = useState(false);
    const [portals, setPortals] = useState<any[]>([]);
    const [newPortal, setNewPortal] = useState('');
    const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");

    const fetchPortals = useCallback(() => {
        api.get(`/api/portals/${id}`)
            .then(res => setPortals(res.data))
            .catch(console.error);
    }, [id]);

    const addPortal = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        if (!newPortal) return;
        api.post('/api/portals', { atom_id: id, path: newPortal })
            .then(() => {
                setNewPortal('');
                fetchPortals();
            })
            .catch((err: any) => {
                if (data.onError) data.onError("Failed to add portal: " + err.message);
            });
    }, [id, newPortal, fetchPortals, data]);

    const handleWitness = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        api.post('/api/witness', { atom_id: id }).catch(console.error);
    }, [id]);

    const toggleLogs = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        if (!showLogs) {
            setShowLogs(true);
            setLogs(null);
            api.get(`/api/atoms/${id}/logs`)
                .then(res => setLogs(res.data.logs))
                .catch(() => setLogs("No logs available or failed to fetch."));
        } else {
            setShowLogs(false);
        }
    }, [showLogs, id]);

    // Status styling
    const getGlow = (s: number | string) => {
        switch (parseInt(s.toString())) {
            case 0: return 'shadow-[0_0_20px_rgba(59,130,246,0.5)] border-blue-500'; // Shadow
            case 1: return 'shadow-[0_0_20px_rgba(234,179,8,0.5)] border-yellow-500'; // Claim
            case 2: return 'shadow-[0_0_20px_rgba(168,85,247,0.5)] border-purple-500 animate-pulse'; // Witnessing
            case 3: return 'shadow-[0_0_20px_rgba(34,197,94,0.5)] border-green-500'; // Endorsed
            case 4: return 'shadow-none border-dashed border-gray-600 opacity-50'; // Fossil
            default: return 'shadow-[0_0_15px_rgba(107,114,128,0.3)] border-gray-500';
        }
    };

    const getDomainColor = (d?: string) => {
        const ld = d?.toLowerCase() || 'generic';
        if (ld === 'software') return 'bg-blue-900/30 text-blue-300 border border-blue-700/50';
        if (ld === 'legal') return 'bg-red-900/30 text-red-300 border border-red-700/50';
        return 'bg-gray-800 text-gray-400 border border-gray-700';
    };

    const statusInt = parseInt(status.toString());

    return (
        <div className={`rounded-xl border bg-gray-900/90 backdrop-blur-md min-w-[320px] transition-all duration-300 flex flex-col overflow-hidden ${getGlow(status)}`}>
            {/* Input Handle */}
            <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-gray-400 !border-2 !border-gray-800 transition-colors hover:!bg-white" />

            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
                <span className="font-bold text-sm text-gray-100 tracking-tight font-mono truncate max-w-[180px]" title={id}>
                    {id || 'Unknown Atom'}
                </span>
                <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-medium ${getDomainColor(domain)}`}>
                    {domain || 'GENERIC'}
                </span>
            </div>

            {/* Content Body */}
            <div className="relative group">
                <div className="p-4 max-h-64 overflow-y-auto font-mono text-xs leading-relaxed text-gray-300 bg-[#1e1e1e] scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                    <pre className="whitespace-pre-wrap break-all">{content || '(Empty Content)'}</pre>
                </div>
            </div>

            {/* Logs Overlay */}
            {showLogs && (
                <div className="p-4 border-t border-gray-800 bg-black/50 overflow-x-auto">
                    <h4 className="text-[10px] uppercase text-gray-500 font-bold mb-2">Verification Logs</h4>
                    {logs ? (
                        <pre className="text-[10px] text-gray-400 font-mono whitespace-pre-wrap">{logs}</pre>
                    ) : (
                        <span className="text-[10px] text-gray-600 italic">Loading logs...</span>
                    )}
                </div>
            )}

            {/* Actions / Portals Area (Visible for Shadow/Draft) */}
            {statusInt === 0 && (
                <div className="px-4 py-2 border-t border-gray-800 bg-gray-900/40">
                    <div
                        data-testid="portals-toggle"
                        className="flex justify-between items-center mb-2 cursor-pointer select-none"
                        onClick={() => {
                            setShowPortals(!showPortals);
                            if (!showPortals && portals.length === 0) fetchPortals();
                        }}
                    >
                        <h4 className="text-[10px] uppercase text-blue-400 font-bold tracking-wider flex items-center gap-2">
                            <span className="text-gray-500">Portals</span>
                            {portals.length > 0 && <span className="bg-blue-900/50 text-blue-200 px-1 rounded">{portals.length}</span>}
                        </h4>
                        <span className="text-xs text-gray-600">{showPortals ? '▼' : '▶'}</span>
                    </div>

                    {/* Model Selector (Only needed for summoning) */}
                    <div className="mb-2 flex items-center gap-2">
                        <label className="text-[10px] text-gray-500 font-bold uppercase">Model:</label>
                        <select
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="bg-black/50 border border-gray-700 rounded text-[10px] text-gray-300 px-1 py-0.5 outline-none focus:border-blue-500"
                        >
                            <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                            <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                            <option value="gemini-3-flash">Gemini 3 Flash</option>
                        </select>
                    </div>

                    {showPortals && (
                        <div className="space-y-2">
                            <ul className="space-y-1 mb-2">
                                {portals.map((p: any) => (
                                    <li key={p.id} className="text-[10px] text-gray-300 bg-black/30 px-2 py-1 rounded border border-gray-800 flex justify-between">
                                        <span className="truncate">{p.path}</span>
                                    </li>
                                ))}
                                {portals.length === 0 && <li className="text-[10px] text-gray-600 italic">No portals linked.</li>}
                            </ul>

                            <form onSubmit={addPortal} className="flex gap-1">
                                <input
                                    data-testid="portal-input"
                                    type="text"
                                    placeholder="/path/to/truth"
                                    value={newPortal}
                                    onChange={(e) => setNewPortal(e.target.value)}
                                    className="flex-1 bg-black/50 border border-gray-700 rounded px-2 py-1 text-[10px] text-white focus:border-blue-500 outline-none"
                                />
                                <button type="submit" data-testid="add-portal-btn" className="bg-blue-900/30 text-blue-400 border border-blue-800 p-1 rounded hover:bg-blue-800/30 transition-colors">
                                    +
                                </button>
                            </form>
                        </div>
                    )}
                </div>
            )}

            {/* Footer Buttons */}
            <div className="px-4 py-2 border-t border-gray-800 bg-gray-900/50 flex justify-between items-center gap-2">
                <button
                    onClick={toggleLogs}
                    className="text-gray-500 hover:text-gray-300 text-[10px] uppercase tracking-wider font-bold transition-colors"
                >
                    {showLogs ? 'Hide Logs' : 'Logs'}
                </button>

                {/* Witness Button (Status 0 or 1) */}
                {(statusInt === 1 || statusInt === 0) && (
                    <button
                        onClick={handleWitness}
                        className="bg-yellow-600/20 hover:bg-yellow-600/40 text-yellow-500 hover:text-yellow-300 border border-yellow-600/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors"
                    >
                        Witness
                    </button>
                )}

                {/* Summon Button (Status 0) */}
                {statusInt === 0 && (
                    <button
                        data-testid="summon-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (data.onSummon) {
                                data.onSummon(id, selectedModel);
                            }
                        }}
                        className="bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 hover:text-blue-300 border border-blue-600/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors shadow-[0_0_10px_rgba(59,130,246,0.2)]"
                    >
                        Summon
                    </button>
                )}

                {/* Revive Button (Status 4) */}
                {statusInt === 4 && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (data.onRevive) {
                                data.onRevive(id);
                            }
                        }}
                        className="bg-purple-900/30 hover:bg-purple-900/50 text-purple-400 hover:text-purple-300 border border-purple-800/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors"
                    >
                        Revive
                    </button>
                )}
            </div>

            {/* Output Handle */}
            <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-gray-400 !border-2 !border-gray-800 transition-colors hover:!bg-white" />
        </div>
    );
};

export default memo(SpatiaNode);
