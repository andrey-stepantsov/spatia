import React, { useEffect, useRef } from 'react';

export default function EventLogPanel({ logs, isOpen, onClose, onClear }) {
    const scrollRef = useRef(null);

    // Auto-scroll to bottom on new logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed bottom-4 left-4 z-[999] w-96 max-h-[50vh] bg-black/90 border border-gray-700 rounded-lg shadow-2xl flex flex-col backdrop-blur-md overflow-hidden animate-in fade-in slide-in-from-bottom-4">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-800">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    Event Stream
                </h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onClear}
                        className="text-[10px] text-gray-500 hover:text-white uppercase transition-colors"
                    >
                        Clear
                    </button>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-white transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>
            </div>

            {/* Log Body */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-[10px] scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent"
            >
                {logs.length === 0 && (
                    <div className="text-gray-600 text-center py-4 italic">No events received...</div>
                )}

                {logs.map((log, i) => (
                    <div key={i} className="group hover:bg-white/5 p-1 rounded transition-colors break-all">
                        <span className="text-gray-500 mr-2">[{log.timestamp}]</span>
                        <span className={`font-bold mr-2 ${getEventTypeColor(log.data.type)}`}>
                            {log.data.type || 'UNKNOWN'}
                        </span>
                        <span className="text-gray-300">
                            {JSON.stringify(omit(log.data, ['type']))}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function getEventTypeColor(type) {
    switch (type) {
        case 'update': return 'text-blue-400';
        case 'db_update': return 'text-yellow-400';
        case 'thread_new': return 'text-purple-400';
        case 'world_reset': return 'text-red-400';
        case 'envelope_update': return 'text-green-400';
        case 'error': return 'text-red-500';
        default: return 'text-gray-400';
    }
}

function omit(obj, keys) {
    const newObj = { ...obj };
    keys.forEach(k => delete newObj[k]);
    return newObj;
}
