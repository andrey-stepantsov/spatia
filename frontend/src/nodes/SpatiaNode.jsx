import React, { memo, useState } from 'react';
import { Handle, Position } from '@xyflow/react';

import axios from 'axios';

const SpatiaNode = ({ data }) => {
    const { content, status, domain, id } = data;
    const [showLogs, setShowLogs] = useState(false);
    const [logs, setLogs] = useState(null);
    const [showPortals, setShowPortals] = useState(false);
    const [portals, setPortals] = useState([]);
    const [newPortal, setNewPortal] = useState('');
    const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");

    const fetchPortals = () => {
        axios.get(`/api/portals/${id}`)
            .then(res => setPortals(res.data))
            .catch(console.error);
    };

    const addPortal = (e) => {
        e.preventDefault();
        if (!newPortal) return;
        axios.post('/api/portals', { atom_id: id, path: newPortal })
            .then(() => {
                setNewPortal('');
                fetchPortals();
            })
            .catch(err => alert("Failed to add portal: " + err.message));
    };

    // Status mapping
    // 0: Shadow (Blue)
    // 1: Claim (Yellow)
    // 2: Witnessed (Purple Pulse)
    // 3: Endorsed (Green)

    const getGlow = (s) => {
        switch (parseInt(s)) {
            case 0: return 'shadow-[0_0_20px_rgba(59,130,246,0.5)] border-blue-500';
            case 1: return 'shadow-[0_0_20px_rgba(234,179,8,0.5)] border-yellow-500';
            case 2: return 'shadow-[0_0_20px_rgba(168,85,247,0.5)] border-purple-500 animate-pulse';
            case 3: return 'shadow-[0_0_20px_rgba(34,197,94,0.5)] border-green-500';
            case 4: return 'shadow-none border-dashed border-gray-600 opacity-50';
            default: return 'shadow-[0_0_15px_rgba(107,114,128,0.3)] border-gray-500';
        }
    };

    const getDomainColor = (d) => {
        const ld = d?.toLowerCase() || 'generic';
        if (ld === 'software') return 'bg-blue-900/30 text-blue-300 border border-blue-700/50';
        if (ld === 'legal') return 'bg-red-900/30 text-red-300 border border-red-700/50';
        return 'bg-gray-800 text-gray-400 border border-gray-700';
    };

    return (
        <div className={`rounded-xl border bg-gray-900/90 backdrop-blur-md min-w-[320px] transition-all duration-300 flex flex-col overflow-hidden ${getGlow(status)}`}>
            <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-gray-400 !border-2 !border-gray-800 transition-colors hover:!bg-white" />

            <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
                <span className="font-bold text-sm text-gray-100 tracking-tight font-mono truncate max-w-[180px]" title={id}>
                    {id || 'Unknown Atom'}
                </span>
                <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-medium ${getDomainColor(domain)}`}>
                    {domain || 'GENERIC'}
                </span>
            </div>

            <div className="relative group">
                <div className="p-4 max-h-64 overflow-y-auto font-mono text-xs leading-relaxed text-gray-300 bg-[#1e1e1e] scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                    <pre className="whitespace-pre-wrap break-all">{content || '(Empty Content)'}</pre>
                </div>
            </div>

            {/* Log Viewer */}
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

            {/* Portals Section */}
            {parseInt(status) === 0 && (
                <div className="px-4 py-2 border-t border-gray-800 bg-gray-900/40">
                    <div
                        data-testid="portals-toggle"
                        className="flex justify-between items-center mb-2 cursor-pointer"
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

                    {/* Model Selector */}
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
                            {/* List */}
                            <ul className="space-y-1 mb-2">
                                {portals.map(p => (
                                    <li key={p.id} className="text-[10px] text-gray-300 bg-black/30 px-2 py-1 rounded border border-gray-800 flex justify-between">
                                        <span className="truncate">{p.path}</span>
                                    </li>
                                ))}
                                {portals.length === 0 && <li className="text-[10px] text-gray-600 italic">No portals linked.</li>}
                            </ul>

                            {/* Add Form */}
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

            <div className="px-4 py-2 border-t border-gray-800 bg-gray-900/50 flex justify-between items-center gap-2">
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        // Toggle Logs
                        if (!showLogs) {
                            setShowLogs(true);
                            setLogs(null);
                            axios.get(`/api/atoms/${id}/logs`)
                                .then(res => setLogs(res.data.logs))
                                .catch(err => setLogs("No logs available or failed to fetch."));
                        } else {
                            setShowLogs(false);
                        }
                    }}
                    className="text-gray-500 hover:text-gray-300 text-[10px] uppercase tracking-wider font-bold transition-colors"
                >
                    {showLogs ? 'Hide Logs' : 'Logs'}
                </button>

                {(parseInt(status) === 1 || parseInt(status) === 0) && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            axios.post('/api/witness', { atom_id: id }).catch(console.error);
                        }}
                        className="bg-yellow-600/20 hover:bg-yellow-600/40 text-yellow-500 hover:text-yellow-300 border border-yellow-600/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors"
                    >
                        Witness
                    </button>
                )}

                {parseInt(status) === 0 && (
                    <button
                        data-testid="summon-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Summon AI to implement this Hollow construct?")) {
                                axios.post('/api/summon', { atom_id: id, model: selectedModel }).catch(err => alert(err.message));
                            }
                        }}
                        className="bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 hover:text-blue-300 border border-blue-600/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors shadow-[0_0_10px_rgba(59,130,246,0.2)]"
                    >
                        Summon
                    </button>
                )}

                {parseInt(status) === 4 && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Revive this fossil? The current version will be archived.")) {
                                axios.post('/api/revive', { fossil_id: id }).catch(err => alert(err.message));
                            }
                        }}
                        className="bg-purple-900/30 hover:bg-purple-900/50 text-purple-400 hover:text-purple-300 border border-purple-800/50 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded transition-colors"
                    >
                        Revive
                    </button>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-gray-400 !border-2 !border-gray-800 transition-colors hover:!bg-white" />
        </div>
    );
};

export default memo(SpatiaNode);
