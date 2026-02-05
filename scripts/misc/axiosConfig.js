// axiosConfig.js
import axios from 'axios';

const instance = axios.create({
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
    withCredentials: true,  // CRITICAL: This sends cookies
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Add response interceptor for handling 401 errors
instance.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Redirect to login on 401
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default instance;