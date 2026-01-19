import React from 'react';
import { PrismAsyncLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const ContentModal = ({ isOpen, onClose, content, language = 'python', title }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            ></div>

            {/* Modal Content */}
            <div className="relative bg-[#1e1e1e] border border-gray-700 w-[90vw] h-[90vh] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex justify-between items-center px-4 py-3 border-b border-gray-700 bg-[#252526]">
                    <div className="flex items-center gap-3">
                        <h3 className="font-mono text-sm font-bold text-gray-200">{title || 'Content Viewer'}</h3>
                        <span className="text-[10px] uppercase bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded border border-blue-800">
                            {language}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => {
                                navigator.clipboard.writeText(content);
                            }}
                            className="bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-1 rounded text-xs font-medium transition-colors border border-gray-600"
                        >
                            Copy
                        </button>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-white hover:bg-red-900/50 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
                        >
                            ✕
                        </button>
                    </div>
                </div>

                {/* Code Area */}
                <div className="flex-1 overflow-auto bg-[#1e1e1e] p-0 custom-scrollbar">
                    <SyntaxHighlighter
                        language={language}
                        style={vscDarkPlus}
                        customStyle={{ margin: 0, padding: '1.5rem', background: 'transparent', fontSize: '14px' }}
                        showLineNumbers={true}
                        wrapLines={false} // Better for reading code usually, horizontal scroll
                    >
                        {content}
                    </SyntaxHighlighter>
                </div>

                {/* Status Bar */}
                <div className="px-4 py-1 border-t border-gray-800 bg-[#007acc] text-white text-[10px] flex justify-between items-center">
                    <span>Spaces: 4</span>
                    <span>UTF-8</span>
                </div>
            </div>
        </div>
    );
};

export default ContentModal;
