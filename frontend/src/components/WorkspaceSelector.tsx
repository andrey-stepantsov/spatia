
import React, { useEffect, useState, useRef } from 'react';
import api from '../utils/api';

import CloneModal from './CloneModal';

interface WorkspaceSelectorProps {
    onError: (msg: string) => void;
    onSuccess: (msg: string) => void;
}

export default function WorkspaceSelector({ onError, onSuccess }: WorkspaceSelectorProps) {
    const [workspaces, setWorkspaces] = useState<string[]>([]);
    const [currentWorkspace, setCurrentWorkspace] = useState<string>('default');
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    // Creator Modal State
    const [isCreatorOpen, setIsCreatorOpen] = useState(false);
    const [newWsName, setNewWsName] = useState('');

    // Eject Modal State
    const [isEjectOpen, setIsEjectOpen] = useState(false);
    const [ejectTarget, setEjectTarget] = useState<string | null>(null);
    const [ejectConfirmName, setEjectConfirmName] = useState('');

    // Clone Modal State
    const [isCloneOpen, setIsCloneOpen] = useState(false);
    const [cloneTarget, setCloneTarget] = useState<string | null>(null);

    // Context Menu State
    const [activeContext, setActiveContext] = useState<string | null>(null); // name of ws
    const [contextMenuPos, setContextMenuPos] = useState<{ x: number, y: number } | null>(null);

    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchWorkspaces();
        // Close menus on click outside
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsMenuOpen(false);
                setActiveContext(null);
                setContextMenuPos(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchWorkspaces = async () => {
        try {
            const res = await api.get('/api/workspaces');
            setWorkspaces(res.data);
        } catch (err: any) {
            console.error("Failed to fetch workspaces", err);
        }
    };

    const handleSwitch = async (name: string) => {
        setIsMenuOpen(false);
        try {
            await api.post('/api/workspace/switch', { name });
            setCurrentWorkspace(name);
        } catch (err: any) {
            onError("Failed to switch: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/api/workspaces', { name: newWsName });

            // Auto-switch to the new workspace
            await handleSwitch(newWsName);

            setNewWsName('');
            setIsCreatorOpen(false);
            fetchWorkspaces();
            onSuccess(`Created workspace ${newWsName}`);
        } catch (err: any) {
            onError("Create failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleSnapshot = async (name: string) => {
        setActiveContext(null);
        try {
            await api.post(`/api/workspaces/${name}/snapshot`);
            onSuccess(`Snapshot created for ${name}`);
        } catch (err: any) {
            onError("Snapshot failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const openCloneModal = (name: string) => {
        setActiveContext(null);
        setCloneTarget(name);
        setIsCloneOpen(true);
    };

    const handleClone = async (newName: string) => {
        if (!cloneTarget) return;
        try {
            await api.post(`/api/workspaces/${cloneTarget}/clone`, { new_name: newName });
            fetchWorkspaces();
            setIsCloneOpen(false);
            setCloneTarget(null);
            onSuccess(`Cloned ${cloneTarget} to ${newName}`);
        } catch (err: any) {
            onError("Clone failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const openEjectModal = (name: string) => {
        setActiveContext(null);
        setEjectTarget(name);
        setEjectConfirmName('');
        setIsEjectOpen(true);
    };

    const handleEject = async () => {
        if (ejectConfirmName !== ejectTarget) return;

        try {
            await api.post(`/api/workspaces/${ejectTarget}/eject`);
            setIsEjectOpen(false);
            setEjectTarget(null);

            // If we ejected current, switch to default? 
            // The backend broadcast world_ejected, App.jsx refreshes.
            // But we might be in a broken state if we don't switch logic.
            // Let's force switch to default if current.
            if (currentWorkspace === ejectTarget) {
                // Try switch to default, ignoring error (if default is broken, we are stuck anyway)
                handleSwitch('default');
            }

            fetchWorkspaces();
        } catch (err: any) {
            alert("Eject failed: " + err.message);
        }
    };

    return (
        <div data-testid="workspace-selector" className="absolute top-4 left-96 z-50 flex items-center gap-3">
            <div className="relative" ref={menuRef}>
                {/* Main Trigger */}
                <button
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    className="bg-gray-900/80 backdrop-blur border border-gray-700 shadow-2xl rounded-xl px-3 py-2 flex items-center gap-2 hover:border-blue-500 transition-colors"
                >
                    <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">World</span>
                    <span className="text-sm font-mono text-white font-bold">{currentWorkspace}</span>
                    <span className="text-sm font-mono text-gray-400">▼</span>
                </button>

                {/* Dropdown Menu */}
                {isMenuOpen && (
                    <div className="absolute top-full left-0 mt-2 w-64 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden flex flex-col z-[60]">
                        <div className="p-2 border-b border-gray-800">
                            <span className="text-[10px] text-gray-500 uppercase font-bold px-2">Available Worlds</span>
                        </div>
                        <div
                            className="max-h-60 overflow-y-auto"
                        >
                            {workspaces.map(ws => (
                                <div key={ws} className="group flex items-center justify-between hover:bg-gray-800 px-3 py-2 cursor-pointer relative">
                                    <div className="flex-1" onClick={() => handleSwitch(ws)}>
                                        <div className={`text-sm font-mono ${ws === currentWorkspace ? 'text-blue-400 font-bold' : 'text-gray-300'}`}>
                                            {ws}
                                        </div>
                                    </div>

                                    {/* Meatball Menu Trigger */}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (activeContext === ws) {
                                                setActiveContext(null);
                                                setContextMenuPos(null);
                                            } else {
                                                const rect = e.currentTarget.getBoundingClientRect();
                                                setActiveContext(ws);
                                                // Position: Right align to button, slightly down
                                                // We actuaally want it distinct.
                                                setContextMenuPos({ x: rect.left, y: rect.bottom + 4 });
                                            }
                                        }}
                                        className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white rounded hover:bg-gray-700 ml-2"
                                    >
                                        ⋮
                                    </button>
                                </div>
                            ))}
                        </div>
                        <div className="p-2 border-t border-gray-800 bg-gray-900">
                            <button
                                onClick={() => { setIsMenuOpen(false); setIsCreatorOpen(true); }}
                                className="w-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 rounded flex items-center justify-center gap-2"
                            >
                                <span>+</span> Create New World
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Creator Modal */}
            {isCreatorOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center">
                    <div className="bg-gray-900 border border-gray-700 rounded-2xl w-96 p-6 shadow-2xl">
                        <h2 className="text-xl font-bold text-white mb-4">Create New World</h2>
                        <form onSubmit={handleCreate}>
                            <div className="mb-4">
                                <label className="block text-xs uppercase font-bold text-gray-500 mb-2">Workspace Name</label>
                                <input
                                    autoFocus
                                    type="text"
                                    className="w-full bg-black/50 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono focus:border-blue-500 focus:outline-none"
                                    value={newWsName}
                                    onChange={e => setNewWsName(e.target.value)}
                                    placeholder="my-new-world"
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setIsCreatorOpen(false)}
                                    className="px-4 py-2 rounded-lg text-gray-400 hover:text-white text-sm"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={!newWsName.trim()}
                                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Create World
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Eject Confirmation Modal */}
            {isEjectOpen && (
                <div className="fixed inset-0 bg-red-900/40 backdrop-blur-md z-[100] flex items-center justify-center">
                    <div className="bg-gray-900 border-2 border-red-600 rounded-2xl w-[450px] p-0 shadow-2xl overflow-hidden">
                        <div className="bg-red-600 px-6 py-4 flex items-center gap-3">
                            <div className="text-2xl">⚠️</div>
                            <h2 className="text-lg font-bold text-white uppercase tracking-wide">Critical Action: Ejecting World</h2>
                        </div>

                        <div className="p-6">
                            <p className="text-gray-300 text-sm leading-relaxed mb-6">
                                This operation will <strong>permanently remove the Spatia Metadata</strong> (.spatia directory) and replace all symlinks with physical file copies.
                                <br /><br />
                                The workspace <span className="text-white font-mono bg-gray-800 px-1 py-0.5 rounded">{ejectTarget}</span> will become a standalone folder and will no longer be managed by the Universal Semantic Graph.
                            </p>

                            <div className="bg-black/30 rounded-lg p-4 mb-6 border border-red-900/50">
                                <label className="block text-[10px] uppercase font-bold text-red-400 mb-2 tracking-wider">
                                    Type "{ejectTarget}" to confirm
                                </label>
                                <input
                                    type="text"
                                    className="w-full bg-black/50 border border-red-900/50 rounded px-3 py-2 text-white font-mono focus:border-red-500 focus:outline-none"
                                    value={ejectConfirmName}
                                    onChange={e => setEjectConfirmName(e.target.value)}
                                    placeholder={ejectTarget || undefined}
                                />
                            </div>

                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    onClick={() => setIsEjectOpen(false)}
                                    className="px-5 py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleEject}
                                    disabled={ejectConfirmName !== ejectTarget}
                                    className="px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-bold shadow-lg shadow-red-900/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                >
                                    Final Eject
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <CloneModal
                isOpen={isCloneOpen}
                onClose={() => setIsCloneOpen(false)}
                onClone={handleClone}
                initialName={cloneTarget}
            />

            {/* Global Context Menu (Fixed) */}
            {activeContext && contextMenuPos && (
                <div
                    className="fixed w-32 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-[100] flex flex-col py-1"
                    style={{ top: contextMenuPos.y, left: contextMenuPos.x }}
                >
                    <button
                        onClick={() => {
                            console.log("JSX: Snapshot Clicked");
                            if (activeContext) handleSnapshot(activeContext);
                            else console.error("JSX: activeContext is null!");
                        }}
                        className="text-left px-3 py-1.5 text-xs text-blue-300 hover:bg-gray-700"
                    >
                        Snapshot
                    </button>
                    <button
                        onClick={() => openCloneModal(activeContext)}
                        className="text-left px-3 py-1.5 text-xs text-green-300 hover:bg-gray-700"
                    >
                        Clone
                    </button>
                    <div className="h-px bg-gray-700 my-1"></div>
                    <button
                        onClick={() => openEjectModal(activeContext)}
                        className="text-left px-3 py-1.5 text-xs text-red-400 hover:bg-gray-700 font-bold"
                    >
                        Eject
                    </button>
                </div>
            )}
        </div>
    );
}
