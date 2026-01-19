import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import SpatiaNode from './SpatiaNode';
import api from '../utils/api';
import { ReactFlowProvider } from '@xyflow/react';

// Mock API
vi.mock('../utils/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
    }
}));

// Wrapper for ReactFlow components
const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <ReactFlowProvider>{children}</ReactFlowProvider>
);

describe('SpatiaNode', () => {
    const mockData = {
        id: 'atoms/test.md',
        content: '# Test Content',
        status: 0, // Shadow
        domain: 'generic',
        onError: vi.fn(),
        onSummon: vi.fn(),
        onRevive: vi.fn(),
    };

    const createProps = (dataOverride: any = {}) => ({
        id: 'atoms/test.md',
        type: 'spatia',
        data: { ...mockData, ...dataOverride },
        selected: false,
        zIndex: 0,
        isConnectable: true,
        xPos: 0,
        yPos: 0,
        dragging: false,
    } as any);

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders atom content and ID', () => {
        render(<Wrapper><SpatiaNode {...createProps()} /></Wrapper>);
        expect(screen.getByText('atoms/test.md')).toBeInTheDocument();
        expect(screen.getByText(/generic/i)).toBeInTheDocument();
        expect(screen.getByText(/# Test Content/)).toBeInTheDocument();
    });

    it('shows witness button for status 1', () => {
        render(<Wrapper><SpatiaNode {...createProps({ status: 1 })} /></Wrapper>);
        expect(screen.getByText('Witness')).toBeInTheDocument();
    });

    it('shows summon button for status 0', () => {
        render(<Wrapper><SpatiaNode {...createProps({ status: 0 })} /></Wrapper>);
        expect(screen.getByText('Summon')).toBeInTheDocument();
    });

    it('toggles logs and fetches them', async () => {
        (api.get as any).mockResolvedValueOnce({ data: { logs: 'Log entry 1' } });
        render(<Wrapper><SpatiaNode {...createProps()} /></Wrapper>);

        const logsBtn = screen.getByText('Logs');
        fireEvent.click(logsBtn);

        expect(screen.getByText('Loading logs...')).toBeInTheDocument();
        await waitFor(() => expect(screen.getByText('Log entry 1')).toBeInTheDocument());
        expect(api.get).toHaveBeenCalledWith('/api/atoms/atoms/test.md/logs');
    });

    it('expands portals and fetches them', async () => {
        (api.get as any).mockResolvedValueOnce({ data: [{ id: 1, path: 'atoms/other.md' }] });
        render(<Wrapper><SpatiaNode {...createProps()} /></Wrapper>);

        // Status 0 shows portals section
        const toggle = screen.getByTestId('portals-toggle');
        fireEvent.click(toggle);

        await waitFor(() => expect(screen.getByText('atoms/other.md')).toBeInTheDocument());
        expect(api.get).toHaveBeenCalledWith('/api/portals/atoms/test.md');
    });

    it('handles manual witness trigger', async () => {
        (api.post as any).mockResolvedValueOnce({});
        render(<Wrapper><SpatiaNode {...createProps({ status: 1 })} /></Wrapper>);

        fireEvent.click(screen.getByText('Witness'));
        expect(api.post).toHaveBeenCalledWith('/api/witness', { atom_id: 'atoms/test.md' });
    });
});
