import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { authAPI } from './api';
import { APIError } from './api';

// Define the auth context type for better type checking
export const AuthContext = createContext(null);

// Path patterns that require authentication - now empty to bypass auth
const PROTECTED_PATHS = [];

// Helper to check if a path requires authentication
const isProtectedPath = (path) => {
  // Always return false to bypass protection
  return false;
};

// Auth provider component
export function AuthProvider({ children }) {
  const [user, setUser] = useState({
    id: "dummy_user_id",
    email: "user@example.com",
    username: "demouser",
    fullName: "Demo User",
    isActive: true,
    isAdmin: true,
    preferences: {
      theme: "dark"
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isInitialized, setIsInitialized] = useState(true);
  const router = useRouter();

  // Skip auth check on initial load - provide dummy user immediately
  useEffect(() => {
    setIsInitialized(true);
    setLoading(false);
  }, []);

  // No redirects for protected routes - all are accessible
  useEffect(() => {
    // Intentionally empty - no redirect logic
  }, [isInitialized, loading, user, router]);

  // Login function - automatically succeeds
  const login = useCallback(async (email, password) => {
    // No actual login, just return success
    return true;
  }, [router]);

  // Register function - automatically succeeds
  const register = useCallback(async (userData) => {
    // No actual registration, just return success
    return true;
  }, [router]);

  // Logout function - does nothing
  const logout = useCallback(async () => {
    // No actual logout needed
    console.log("Logout called but ignored in bypass mode");
  }, [router]);

  // Update user profile - automatically succeeds
  const updateUserProfile = useCallback(async (profileData) => {
    // No actual update, just return success
    return true;
  }, []);

  // Request password reset - automatically succeeds
  const forgotPassword = useCallback(async (email) => {
    // No actual password reset, just return success
    return true;
  }, []);

  // Reset password with token - automatically succeeds
  const resetPassword = useCallback(async (token, newPassword) => {
    // No actual password reset, just return success
    return true;
  }, [router]);

  // Auth context value
  const contextValue = {
    user,
    loading,
    error,
    isInitialized,
    login,
    register,
    logout,
    updateUserProfile,
    forgotPassword,
    resetPassword,
    isAuthenticated: true // Always authenticated
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 