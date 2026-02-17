import axios from 'axios'

function computeBaseUrl() {
    // If accessing the frontend via LAN IP (e.g. http://10.x.x.x:5173),
    // default to hitting the backend on the same host (http://10.x.x.x:8000).
    const fallback = `http://${window.location.hostname}:8000`

    const envUrl = import.meta.env.VITE_API_URL
    if (!envUrl) return fallback

    // Support same-origin deployments behind a reverse proxy (e.g. /api).
    if (typeof envUrl === 'string' && envUrl.startsWith('/')) {
        return envUrl
    }

    try {
        const host = new URL(envUrl).hostname
        // Ignore localhost-style env defaults because they break when accessed from another device
        if (host === 'localhost' || host === '127.0.0.1') return fallback
        return envUrl
    } catch {
        return fallback
    }
}

const api = axios.create({
    baseURL: computeBaseUrl(),
    timeout: 10000, // 10 second timeout
})

// Add request interceptor for debugging
api.interceptors.request.use(
    (config) => {
        // Always attach token if present (prevents "random" 401s when defaults get lost)
        const token = localStorage.getItem('token')
        if (token) {
            config.headers = config.headers || {}
            if (!config.headers.Authorization) {
                config.headers.Authorization = `Bearer ${token}`
            }
        }
        console.log(`Making ${config.method?.toUpperCase()} request to: ${config.url}`)
        return config
    },
    (error) => {
        console.error('Request error:', error)
        return Promise.reject(error)
    }
)

// Add response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
            console.error('Network error - is the backend running?', error)
        } else if (error.response) {
            console.error('API error:', error.response.status, error.response.data)
        } else {
            console.error('Request error:', error.message)
        }
        return Promise.reject(error)
    }
)

/** Base URL for API (and for image src when picture_url is relative). */
export function getApiBaseUrl() {
  return computeBaseUrl()
}

export default api