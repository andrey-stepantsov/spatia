import React from 'react';

export default function ConfirmationModal({ isOpen, onClose, onConfirm, title, message, confirmLabel = 'Confirm', variant = 'danger' }) {
    if (!isOpen) return null;

    const isDanger = variant === 'danger';
    const buttonBaseClass = isDanger
        ? "bg-red-900/80 hover:bg-red-800 text-red-100 border-red-700 shadow-red-900/20"
        : "bg-blue-900/80 hover:bg-blue-800 text-blue-100 border-blue-700 shadow-blue-900/20";

    const titleClass = isDanger ? "text-red-400" : "text-blue-400";
    const borderClass = isDanger ? "border-red-900/50" : "border-blue-900/50";

    return (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div role="dialog" aria-modal="true" className={`w-96 bg-gray-900 border ${borderClass} rounded-xl shadow-2xl p-6 transform transition-all scale-100 animate-in zoom-in-95 duration-200`}>
                <h2 className={`text-xl font-bold mb-2 ${titleClass}`}>{title || 'Confirm Action'}</h2>
                <p className="text-sm text-gray-300 mb-6">{message || 'Are you sure?'}</p>

                <div className="flex justify-end gap-3 pt-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-xs font-bold text-gray-400 hover:text-white transition-colors uppercase tracking-wide"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className={`${buttonBaseClass} border rounded-lg px-6 py-2 text-xs font-bold uppercase tracking-wide shadow-lg transition-all active:scale-95`}
                    >
                        {confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    );
}
