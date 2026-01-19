import React, { useState, useEffect } from 'react';

export default function CreateEnvelopeModal({ isOpen, onClose, onCreate }) {
    const [id, setId] = useState('');
    const [domain, setDomain] = useState('generic');

    // Reset/Auto-generate ID when opened
    useEffect(() => {
        if (isOpen) {
            setId(`env-${Date.now()}`);
            setDomain('generic');
        }
    }, [isOpen]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (id.trim()) {
            onCreate({ id, domain });
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div role="dialog" aria-modal="true" className="w-96 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl p-6 transform transition-all scale-100 animate-in zoom-in-95 duration-200">
                <h2 className="text-xl font-bold text-white mb-1">Create Boundary</h2>
                <p className="text-xs text-gray-400 mb-6 uppercase tracking-wider font-mono">Spatial Envelope</p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Envelope ID</label>
                        <input
                            type="text"
                            value={id}
                            onChange={(e) => setId(e.target.value)}
                            className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-sm text-green-400 font-mono placeholder-gray-600 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-all"
                            placeholder="env-..."
                            autoFocus
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Domain</label>
                        <input
                            type="text"
                            value={domain}
                            onChange={(e) => setDomain(e.target.value)}
                            className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-gray-600 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-all"
                            placeholder="generic"
                        />
                    </div>

                    <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-800">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-xs font-bold text-gray-400 hover:text-white transition-colors uppercase tracking-wide"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="bg-green-600 hover:bg-green-500 text-white rounded-lg px-6 py-2 text-xs font-bold uppercase tracking-wide shadow-lg shadow-green-900/20 transition-all active:scale-95"
                        >
                            Create
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
