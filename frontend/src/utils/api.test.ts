import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import api from './api';
import axios from 'axios';

// Mock Axios
vi.mock('axios', async () => {
    const actual = await vi.importActual('axios');
    return {
        ...actual,
        default: {
            create: vi.fn(() => ({
                interceptors: {
                    response: { use: vi.fn() }
                },
                request: vi.fn()
            })),
        }
    };
});

describe('API Utils', () => {
    beforeEach(() => {
        // Reset singleton state if possible, or just mock internal state?
        // Since 'api' is a singleton instance exported, state persists.
        // We can access private fields via (api as any) if needed for testing, 
        // or rely on public methods.
        (api as any).queue = [];
        (api as any).status = 'connecting';
    });

    it('queues requests when connecting', async () => {
        const promise = api.get('/test');
        expect((api as any).queue.length).toBe(1);
        expect((api as any).status).toBe('connecting');

        // Mock axios request logic
        const mockAxios = (api as any).axios;
        mockAxios.request.mockResolvedValue({ data: 'ok' });

        // Simulate connection
        api.setConnectionStatus('connected');

        const res = await promise;
        expect(res.data).toBe('ok');
        expect((api as any).queue.length).toBe(0);
    });

    it('sends immediately when connected', async () => {
        api.setConnectionStatus('connected');
        const mockAxios = (api as any).axios;
        mockAxios.request.mockResolvedValue({ data: 'immediate' });

        const res = await api.get('/now');
        expect(res.data).toBe('immediate');
        expect((api as any).queue.length).toBe(0);
    });

    it('supports echo payload', async () => {
        api.setConnectionStatus('connected');
        const mockAxios = (api as any).axios;
        mockAxios.request.mockResolvedValue({ data: { status: 'ok' } });

        await api.post('/api/echo', { timestamp: 123, payload: 'test' });
        expect(mockAxios.request).toHaveBeenCalledWith(expect.objectContaining({
            url: '/api/echo',
            method: 'post',
            data: { timestamp: 123, payload: 'test' }
        }));
    });
});
