import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock ResizeObserver (Required for React Flow)
// Mock ResizeObserver (Required for React Flow)
global.ResizeObserver = class ResizeObserver {
    constructor(callback) {
        this.callback = callback;
    }
    observe(target) {
        this.callback([{
            target,
            contentRect: {
                width: 800,
                height: 600,
                top: 0,
                left: 0,
                bottom: 600,
                right: 800,
                x: 0,
                y: 0,
            }
        }]);
    }
    unobserve() { }
    disconnect() { }
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});
// Mock EventSource
global.EventSource = class EventSource {
    constructor(url) {
        this.url = url;
        this.readyState = 0; // CONNECTING
        setTimeout(() => {
            this.readyState = 1; // OPEN
            if (this.onopen) this.onopen();
        }, 0);
    }
    close() {
        this.readyState = 2; // CLOSED
    }
    addEventListener(type, listener) {
        // Simple mock
    }
    removeEventListener(type, listener) {
        // Simple mock
    }
};
