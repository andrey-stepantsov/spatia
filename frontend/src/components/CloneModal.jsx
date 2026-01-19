import React, { useState, useEffect } from 'react';

export default function CloneModal({ isOpen, onClose, onClone, initialName }) {
    const [cloneName, setCloneName] = useState('');

    useEffect(() => {
        if (isOpen) {
            setCloneName(initialName ? `${initialName}-copy` : '');
        }
    }, [isOpen, initialName]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (cloneName.trim()) {
            onClone(cloneName);
            setCloneName('');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center">
            <div className="bg-gray-900 border border-gray-700 rounded-2xl w-96 p-6 shadow-2xl">
                <h2 className="text-xl font-bold text-white mb-4">Clone Workspace</h2>
                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label className="block text-xs uppercase font-bold text-gray-500 mb-2">New Workspace Name</label>
                        <input
                            autoFocus
                            type="text"
                            className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono focus:border-blue-500 focus:outline-none"
                            value={cloneName}
                            onChange={(e) => setCloneName(e.target.value)}
                            placeholder="my-workspace-copy"
                        />
                    </div>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 rounded-lg text-gray-400 hover:text-white text-sm"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!cloneName.trim()}
                            className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Clone
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
