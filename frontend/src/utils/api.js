import axios from 'axios';

// Create instance
const api = axios.create({
    baseURL: '', // Relative path proxy
    timeout: 10000,
});

// Response Interceptor
api.interceptors.response.use(
    (response) => {
        // Success - return data directly?
        // Backend Standard Envelope: { status: "ok", ... } or raw json?
        // Current backend returns mix. 
        // New Exception Handler returns: { status: "error", error: { ... } }
        // Normal endpoints return: { ... data ... } or [ ... list ... ]
        return response;
    },
    (error) => {
        // Check if it's a structured error from our backend exception handler
        if (error.response && error.response.data && error.response.data.status === 'error') {
            const backendError = error.response.data.error;
            // Transform into a consistent Error object that frontend components can consume
            const enhancedError = new Error(backendError.message || "Unknown Backend Error");
            enhancedError.code = backendError.code;
            enhancedError.type = backendError.type;
            enhancedError.details = backendError.details;
            enhancedError.original = error;
            return Promise.reject(enhancedError);
        }

        // Check for Network Error (Connection Refused)
        if (!error.response) {
            const netError = new Error("Network Error: Could not reach backend");
            netError.code = "NETWORK_ERROR";
            return Promise.reject(netError);
        }

        // Standard Axios error
        return Promise.reject(error);
    }
);

export default api;
