import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();
    const location = useLocation();

    // On mount, check if user is already logged in via cookie
    useEffect(() => {
        checkAuthStatus();
    }, []);

    const checkAuthStatus = async () => {
        try {
            const response = await fetch('/api/auth/me');
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                // If 401/403, we are not logged in.
                // If we get here, it means backend didn't auto-redirect or we are just verifying session.
                setUser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    const login = async (username, password) => {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            if (response.ok) {
                const data = await response.json();
                await checkAuthStatus(); // Refresh user data

                // Navigate to where they came from, or dashboard
                const origin = location.state?.from?.pathname || '/';
                navigate(origin);
                return { success: true };
            } else {
                const errorData = await response.json();
                return { success: false, error: errorData.detail || 'Login failed' };
            }
        } catch (error) {
            return { success: false, error: 'Network error' };
        }
    };

    const logout = async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            setUser(null);
            navigate('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    const value = {
        user,
        loading,
        login,
        logout,
        checkAuthStatus
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    return useContext(AuthContext);
};

// Component to protect routes
export const RequireAuth = ({ children }) => {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="flex h-screen w-screen items-center justify-center bg-gray-900 text-white">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
            </div>
        );
    }

    if (!user) {
        // Redirect to login page, but save the current location to redirect back after login
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children;
};

// Helper for redirect (imported from rrd usually, but defined here for context usage)
import { Navigate } from 'react-router-dom';
