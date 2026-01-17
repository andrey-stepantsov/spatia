import React, { memo, useState } from 'react';
import { Handle, Position } from '@xyflow/react';

import axios from 'axios';

const SpatiaNode = ({ data }) => {
    const { content, status, domain, id } = data;
    const [showLogs, setShowLogs] = useState(false);
    const [logs, setLogs] = useState(null);

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

                {parseInt(status) === 1 && (
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
            </div>

            <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-gray-400 !border-2 !border-gray-800 transition-colors hover:!bg-white" />
        </div>
    );
};

export default memo(SpatiaNode);
