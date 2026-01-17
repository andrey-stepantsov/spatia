
import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function WorkspaceSelector() {
    const [workspaces, setWorkspaces] = useState([]);
    const [currentWorkspace, setCurrentWorkspace] = useState('default');

    useEffect(() => {
        // Fetch available workspaces
        axios.get('/api/workspaces')
            .then(res => {
                setWorkspaces(res.data);
                // Heuristic: Try to determine current. 
                // Ideally backend returns it, but for now we default or let user pick.
                // We could maybe persist it in local storage or ask backend.
                // For this MVP, we just list them.
            })
            .catch(err => console.error("Failed to fetch workspaces", err));
    }, []);

    const handleSwitch = async (e) => {
        const target = e.target.value;
        if (!target) return;

        try {
            await axios.post('/api/workspace/switch', { name: target });
            setCurrentWorkspace(target);
            // The SSE broadcast will reload the atoms, so we don't need to do much else.
            // But maybe we want to show a toast?
            console.log(`Switched to workspace: ${target}`);
        } catch (err) {
            alert("Failed to switch workspace: " + err.message);
        }
    };

    return (
        <div className="absolute top-4 left-96 z-50 bg-gray-900/80 backdrop-blur border border-gray-700 shadow-2xl rounded-xl p-2 flex items-center gap-3">
            <label className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">World Link</label>
            <select
                value={currentWorkspace}
                onChange={handleSwitch}
                className="bg-black/50 border border-gray-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-purple-500 font-mono"
            >
                {workspaces.map(ws => (
                    <option key={ws} value={ws}>{ws}</option>
                ))}
            </select>
        </div>
    );
}
