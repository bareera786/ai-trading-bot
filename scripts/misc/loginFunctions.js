// Login component
const login = async (username, password, remember = false) => {
    try {
        const response = await axios.post('/auth/login', {
            username,
            password,
            remember
        });

        // Store user data if needed
        localStorage.setItem('user', JSON.stringify(response.data.user));

        return response.data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

// Logout function
const logout = async () => {
    try {
        await axios.post('/auth/logout');
        // Clear local storage
        localStorage.clear();
        sessionStorage.clear();
        // Redirect to login
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        // Still redirect even on error
        window.location.href = '/login';
    }
};