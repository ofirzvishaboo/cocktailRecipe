import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 10000, // 10 second timeout
})

// Add request interceptor for debugging
api.interceptors.request.use(
    (config) => {
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

export default api