import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import api from '../utils/api';

const HEALTH_CHECK_INTERVAL = 2000;
const MAX_FAILURES = 3;

/**
 * useSpatiaConnection Hook
 * 
 * Manages:
 * 1. Heartbeat (polling /api/health)
 * 2. SSE Connection (auto-reconnect on health recovery)
 * 3. Global Connection State (connected, disconnected, reconnecting)
 * 4. Workspace Sync (refetching on reconnect)
 */
import { SYNC_EVENTS } from '../utils/constants';

export function useSpatiaConnection(onSyncRequired, onEvent) {
    const [status, setStatus] = useState('connecting'); // connecting, connected, disconnected
    const [workspace, setWorkspace] = useState(null);
    const [error, setError] = useState(null);

    const failuresRef = useRef(0);
    const sseRef = useRef(null);
    const timerRef = useRef(null);

    // 1. Heartbeat Function
    const checkHealth = useCallback(async () => {
        try {
            const res = await axios.get('/api/health', { timeout: 1500 });
            if (res.data.status === 'ok') {
                failuresRef.current = 0;
                setWorkspace(res.data.workspace);

                if (status === 'disconnected') {
                    console.log("Backend recovered!");
                    setStatus('recovered'); // Transient state to trigger re-sync
                    api.setConnectionStatus('recovered');
                } else if (status === 'connecting') {
                    setStatus('connected');
                    api.setConnectionStatus('connected');
                }
            }
        } catch (err) {
            console.warn("Heartbeat failed:", err.message);
            failuresRef.current += 1;
            if (failuresRef.current >= MAX_FAILURES) {
                setStatus('disconnected');
                api.setConnectionStatus('disconnected');
                if (sseRef.current) {
                    console.log("Closing SSE due to health failure");
                    sseRef.current.close();
                    sseRef.current = null;
                }
            }
        }
    }, [status]);

    // 2. Poll Loop
    useEffect(() => {
        const startPolling = () => {
            timerRef.current = setInterval(checkHealth, HEALTH_CHECK_INTERVAL);
        };
        startPolling();
        return () => clearInterval(timerRef.current);
    }, [checkHealth]);

    // 3. SSE Manager
    useEffect(() => {
        // Only connect SSE if we think we are healthy (connected or recovered)
        if (status === 'connected' || status === 'recovered') {
            if (!sseRef.current) {
                console.log("Initializing SSE...");
                const es = new EventSource('/api/events');

                es.onopen = () => {
                    console.log("SSE Open");
                    // If we were recovering, trigger sync
                    if (onSyncRequired) onSyncRequired();
                    if (status === 'recovered') {
                        setStatus('connected');
                        api.setConnectionStatus('connected');
                    }
                };

                es.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        // Forward all events for observability
                        if (onEvent) onEvent(data);

                        if (SYNC_EVENTS.includes(data.type)) {
                            if (onSyncRequired) onSyncRequired();
                        }
                    } catch (e) {
                        console.error("SSE Parse Error", e);
                    }
                };

                es.onerror = (e) => {
                    console.error("SSE Error", e);
                    es.close();
                    sseRef.current = null;
                    // We don't necessarily set disconnected here, let heartbeat decide if backend is truly dead
                    // But typically SSE error means connection fetch failure.
                };

                sseRef.current = es;
            }
        }

        return () => {
            // Cleanup on unmount or if status changes to disconnected
            if (status === 'disconnected' && sseRef.current) {
                sseRef.current.close();
                sseRef.current = null;
            }
        };
    }, [status, onSyncRequired, onEvent]);

    return { status, workspace, error };
}
