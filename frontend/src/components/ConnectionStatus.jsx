import React from 'react';

export default function ConnectionStatus({ status, workspace }) {
    if (status === 'connected') return null;

    return (
        <div className="absolute top-0 left-0 w-full z-[100] pointer-events-none flex justify-center pt-2">
            {status === 'connecting' && (
                <div className="bg-blue-600/90 text-white px-4 py-1 rounded-full shadow-lg text-xs font-bold animate-pulse backdrop-blur">
                    CONNECTING...
                </div>
            )}
            {status === 'disconnected' && (
                <div className="bg-red-600/90 text-white px-4 py-1 rounded-full shadow-lg text-xs font-bold animate-pulse backdrop-blur flex items-center gap-2">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    CONNECTION LOST — RECONNECTING
                </div>
            )}
        </div>
    );
}
