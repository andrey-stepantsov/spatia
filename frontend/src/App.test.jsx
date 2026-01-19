import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import App from './App';
import api from './utils/api';

// Mock API
vi.mock('./utils/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    }
}));

// Mock ReactFlow components and hooks
vi.mock('@xyflow/react', () => ({
    ReactFlow: ({ nodes }) => <div data-testid="react-flow">{nodes?.length} nodes</div>,
    Background: () => <div>Background</div>,
    Controls: () => <div>Controls</div>,
    // Simple state implementation for hooks
    useNodesState: (initial) => {
        const [nodes, setNodes] = React.useState(initial);
        return [nodes, setNodes, vi.fn()];
    },
    useEdgesState: (initial) => {
        const [edges, setEdges] = React.useState(initial);
        return [edges, setEdges, vi.fn()];
    },
    Handle: () => <div>Handle</div>,
    Position: { Top: 'top', Bottom: 'bottom' },
    ReactFlowProvider: ({ children }) => <div>{children}</div>,
}));

// Mock custom hooks
vi.mock('./hooks/useSpatiaConnection', () => ({
    useSpatiaConnection: () => ({ status: 'connected', workspace: 'default' })
}));

// Mock Canvas to avoid complex rendering
vi.mock('./components/SpatiaCanvas', () => ({
    default: () => <div data-testid="spatia-canvas">Canvas</div>
}));

describe('App Shatter Editor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default API mocks
        (api.get).mockResolvedValue({ data: [] });
    });

    it('opens fullscreen editor when maximize button is clicked', async () => {
        render(<App />);

        // Find the maximize button in Shatter Portal
        const maximizeBtn = screen.getByTitle('Fullscreen Editor');
        fireEvent.click(maximizeBtn);

        // Check if editor appears
        expect(screen.getByText('Shatter Intent Editor')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Describe your intent or construct here...')).toBeInTheDocument();
    });

    it('updates content in fullscreen editor and reflects in main state', async () => {
        render(<App />);

        // Open Editor
        fireEvent.click(screen.getByTitle('Fullscreen Editor'));

        // Type in textarea
        const textarea = screen.getByPlaceholderText('Describe your intent or construct here...');
        fireEvent.change(textarea, { target: { value: 'New Intent Content' } });

        // Close Editor
        const doneBtn = screen.getByText('DONE');
        fireEvent.click(doneBtn);

        // Check if modal is gone
        expect(screen.queryByText('Shatter Intent Editor')).not.toBeInTheDocument();

        // Check if content persisted in the small text area (we can find it by value or querying the textarea)
        // Since we have multiple textareas (one in main UI, one in modal), verifying display value after modal close is good.
        expect(screen.getByDisplayValue('New Intent Content')).toBeInTheDocument();
    });
});
