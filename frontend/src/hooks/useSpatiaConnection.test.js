
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useSpatiaConnection } from './useSpatiaConnection';
import axios from 'axios';
import api from '../utils/api';

vi.mock('axios');
vi.mock('../utils/api', () => ({
    default: {
        setConnectionStatus: vi.fn(),
    }
}));



describe('useSpatiaConnection', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        axios.get.mockResolvedValue({ data: { status: 'ok', workspace: 'default' } });
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('should start in connecting state', () => {
        const { result } = renderHook(() => useSpatiaConnection());
        expect(result.current.status).toBe('connecting');
    });

    it('should transition to connected on successful health check', { timeout: 30000 }, async () => {
        const { result } = renderHook(() => useSpatiaConnection());

        // Fast-forward timer to trigger checkHealth
        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        // Critical: Flush microtasks
        await act(async () => {
            await Promise.resolve();
        });

        expect(result.current.status).toBe('connected');
        expect(result.current.workspace).toBe('default');
    });

    it('should disconnect after max failures', { timeout: 30000 }, async () => {
        axios.get.mockRejectedValue(new Error('Network Error'));
        const { result } = renderHook(() => useSpatiaConnection());

        // Fail 3 times (MAX_FAILURES)
        for (let i = 0; i < 3; i++) {
            await act(async () => {
                vi.advanceTimersByTime(2000);
            });
            // Wrap flush in act to process state updates from the promise resolution
            await act(async () => {
                await Promise.resolve();
            });
        }

        expect(result.current.status).toBe('disconnected');
    });
});
