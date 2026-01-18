import React, { memo, useState } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';
import api from '../utils/api';

export default memo(({ data, id, selected }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [domain, setDomain] = useState(data.domain || 'generic');

    const handleDomainChange = (e) => {
        setDomain(e.target.value);
    };

    const submitDomain = async () => {
        setIsEditing(false);
        try {
            await api.put(`/api/envelopes/${id}`, { domain });
        } catch (err) {
            console.error("Failed to update domain", err);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            submitDomain();
        }
    };

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <NodeResizer
                minWidth={100}
                minHeight={100}
                isVisible={selected}
                lineClassName="border-blue-500"
                handleClassName="h-3 w-3 bg-white border-2 border-blue-500 rounded"
            />

            <div
                className="w-full h-full border-2 border-dashed border-green-500/50 bg-green-500/10 rounded-lg relative group transition-colors hover:border-green-500 hover:bg-green-500/20"
                onDoubleClick={() => setIsEditing(true)}
            >
                <div className="absolute top-0 left-0 bg-green-900/80 text-green-300 text-[10px] px-2 py-0.5 rounded-tl-md rounded-br-md font-mono uppercase tracking-widest border-r border-b border-green-700/50">
                    {isEditing ? (
                        <input
                            autoFocus
                            value={domain}
                            onChange={handleDomainChange}
                            onBlur={submitDomain}
                            onKeyDown={handleKeyDown}
                            className="bg-black/80 text-white outline-none w-20 px-1"
                        />
                    ) : (
                        domain
                    )}
                </div>

                {/* Helper text only visible on hover/selected */}
                {selected && (
                    <div className="absolute bottom-1 right-1 text-[8px] text-green-500/50">
                        {id}
                    </div>
                )}
            </div>

            {/* Hidden handles to allow connecting if we ever want threads to envelopes, but strictly optional */}
            {/* For now, no handles on envelopes to keep them as pure containers */}

        </div>
    );
});
