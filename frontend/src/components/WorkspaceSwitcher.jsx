import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function WorkspaceSwitcher() {
    const [workspaces, setWorkspaces] = useState([]);
    const [currentWorkspace, setCurrentWorkspace] = useState('default');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchWorkspaces();
    }, []);

    const fetchWorkspaces = async () => {
        try {
            const res = await axios.get('/api/workspaces');
            setWorkspaces(res.data);
            // Ideally we should know which one is active.
            // For now, we defaulting UI to 'default' or we could add an API to get current.
            // But since we just symlink, the backend doesn't explicitly 'store' the name persistently 
            // except as what the symlink points to.
            // A quick hack: assume default, or maybe invalid state?
            // Let's just default to 'default' or the first one if not present.
        } catch (err) {
            console.error("Failed to fetch workspaces", err);
        }
    };

    const handleSwitch = async (e) => {
        const target = e.target.value;
        if (!target) return;

        setLoading(true);
        try {
            await axios.post('/api/workspace/switch', { name: target });
            setCurrentWorkspace(target);
            // App.jsx handles the 'world_reset' event to reload data
        } catch (err) {
            alert("Failed to switch workspace: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="absolute top-4 right-20 z-50">
            <div className="flex items-center gap-2 bg-gray-900/80 backdrop-blur border border-gray-700 rounded-lg px-3 py-1.5 shadow-xl">
                <label className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">World</label>
                <select
                    value={currentWorkspace}
                    onChange={handleSwitch}
                    disabled={loading}
                    className="bg-black/50 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:border-blue-500 font-mono"
                >
                    {workspaces.map(ws => (
                        <option key={ws} value={ws}>{ws}</option>
                    ))}
                </select>
                {loading && <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />}
            </div>
        </div>
    );
}
