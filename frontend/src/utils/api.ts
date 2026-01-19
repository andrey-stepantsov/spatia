import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Create base axios instance
const axiosInstance: AxiosInstance = axios.create({
    baseURL: '', // Relative path proxy
    timeout: 10000,
});

export interface ConnectionAwareConfig extends AxiosRequestConfig {
    // timestamp logic handled by caller
}

export interface BackendError {
    status: string;
    error: {
        message: string;
        code: string;
        type: string;
        details: any;
    }
}

// Response Interceptor
axiosInstance.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        // Check if it's a structured error from our backend exception handler
        if (error.response && error.response.data && error.response.data.status === 'error') {
            const backendError = error.response.data.error;
            // Transform into a consistent Error object that frontend components can consume
            const enhancedError = new Error(backendError.message || "Unknown Backend Error") as any;
            enhancedError.code = backendError.code;
            enhancedError.type = backendError.type;
            enhancedError.details = backendError.details;
            enhancedError.original = error;
            return Promise.reject(enhancedError);
        }

        // Check for Network Error (Connection Refused)
        if (!error.response) {
            const netError = new Error("Network Error: Could not reach backend") as any;
            netError.code = "NETWORK_ERROR";
            return Promise.reject(netError);
        }

        // Standard Axios error
        return Promise.reject(error);
    }
);

interface QueuedRequest {
    config: AxiosRequestConfig;
    resolve: (value: any) => void;
    reject: (reason?: any) => void;
    timeoutId: any;
}

/**
 * ConnectionAwareAPI
 * 
 * Wraps axios to queue API requests until SSE connection is established.
 * This prevents race conditions where the app tries to fetch data before
 * the connection is ready, which can cause tests to hang.
 */
class ConnectionAwareAPI {
    private axios: AxiosInstance;
    private status: 'connecting' | 'connected' | 'disconnected' | 'recovered';
    private queue: QueuedRequest[];
    private maxQueueSize: number;
    private requestTimeout: number;

    constructor(instance: AxiosInstance) {
        this.axios = instance;
        this.status = 'connecting';
        this.queue = [];
        this.maxQueueSize = 50; // Prevent unbounded queue growth
        this.requestTimeout = 30000; // Timeout for queued requests
    }

    /**
     * Update connection status and flush queue if connected.
     * Should be called by useSpatiaConnection hook.
     */
    setConnectionStatus(status: 'connecting' | 'connected' | 'disconnected' | 'recovered') {
        console.log(`[API] Connection status: ${this.status} -> ${status}`);
        this.status = status;

        if (status === 'connected' || status === 'recovered') {
            this.flushQueue();
        } else if (status === 'disconnected') {
            // Optionally clear queue on disconnect, or wait for reconnection
            // For now, keep queue to retry when reconnected
        }
    }

    /**
     * Execute a request immediately or queue it if not connected.
     */
    request<T = any>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return new Promise((resolve, reject) => {
            // console.log(`[API-DEBUG] request() called for ${config.method} ${config.url}. Status: ${this.status}`);
            if (this.status === 'connected' || this.status === 'recovered') {
                // Connection ready - send immediately
                // console.log(`[API-DEBUG] Sending immediately via axios`);
                this.axios.request < T > (config).then(resolve).catch(reject);
            } else {
                // Not connected - queue the request
                console.log(`[API] Queueing request: ${config.method} ${config.url}`);

                // Check queue size limit
                if (this.queue.length >= this.maxQueueSize) {
                    const error = new Error('Request queue is full. Too many pending requests.') as any;
                    error.code = 'QUEUE_FULL';
                    reject(error);
                    return;
                }

                // Add timeout for queued request
                const timeoutId = setTimeout(() => {
                    // Remove from queue
                    const index = this.queue.findIndex(item => item.timeoutId === timeoutId);
                    if (index !== -1) {
                        this.queue.splice(index, 1);
                        const error = new Error('Request timed out while waiting for connection') as any;
                        error.code = 'QUEUE_TIMEOUT';
                        reject(error);
                    }
                }, this.requestTimeout);

                this.queue.push({ config, resolve, reject, timeoutId });
            }
        });
    }

    /**
     * Flush all queued requests when connection is established.
     */
    flushQueue() {
        console.log(`[API] Flushing ${this.queue.length} queued requests`);

        while (this.queue.length > 0) {
            const item = this.queue.shift();
            if (item) {
                const { config, resolve, reject, timeoutId } = item;
                clearTimeout(timeoutId);
                this.axios.request(config).then(resolve).catch(reject);
            }
        }
    }

    /**
     * Proxy methods for convenience
     */
    get<T = any>(url: string, config: AxiosRequestConfig = {}) {
        return this.request < T > ({ ...config, method: 'get', url });
    }

    post<T = any>(url: string, data?: any, config: AxiosRequestConfig = {}) {
        return this.request < T > ({ ...config, method: 'post', url, data });
    }

    put<T = any>(url: string, data?: any, config: AxiosRequestConfig = {}) {
        return this.request < T > ({ ...config, method: 'put', url, data });
    }

    delete<T = any>(url: string, config: AxiosRequestConfig = {}) {
        return this.request < T > ({ ...config, method: 'delete', url });
    }

    patch<T = any>(url: string, data?: any, config: AxiosRequestConfig = {}) {
        return this.request < T > ({ ...config, method: 'patch', url, data });
    }
}

// Create singleton instance
const api = new ConnectionAwareAPI(axiosInstance);

export default api;

