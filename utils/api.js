// API utility for handling HTTP requests
const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Custom API Error class to provide more information about API errors
 */
export class APIError extends Error {
  constructor(message, status, data = null) {
    super(message || 'API request failed');
    this.name = 'APIError';
    this.status = status;
    this.data = data;
    this.timestamp = new Date();
  }
}

/**
 * Core request function that handles all API calls
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
 * @param {object} data - Request data (for POST/PUT)
 * @param {boolean} requiresAuth - Whether the request requires authentication
 * @param {object} customConfig - Additional fetch configuration
 * @returns {Promise<any>} Response data
 * @throws {APIError} On API error
 */
async function apiRequest(endpoint, method, data, requiresAuth = true, customConfig = {}) {
  // Construct the full URL
  const url = `${BASE_API_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  
  // Get the auth token from localStorage
  const token = localStorage.getItem('authToken');
  
  // Prepare headers
  const headers = {
    'Content-Type': 'application/json',
    ...customConfig.headers,
  };
  
  // Add auth token if required and available
  if (requiresAuth && token) {
    headers.Authorization = `Bearer ${token}`;
  }
  
  // Prepare request config
  const config = {
    method,
    headers,
    ...customConfig,
  };
  
  // Add body for POST/PUT requests
  if (data && (method === 'POST' || method === 'PUT')) {
    config.body = JSON.stringify(data);
  }
  
  try {
    // Make the request
    const response = await fetch(url, config);
    
    // Handle different response statuses
    if (response.status === 204) {
      // No content - return success but no data
      return { success: true };
    }
    
    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    
    // Parse the response
    let responseData;
    if (isJson) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }
    
    // Handle error responses
    if (!response.ok) {
      // Handle specific error cases
      if (response.status === 401) {
        // Authentication error - clear token and notify
        localStorage.removeItem('authToken');
        throw new APIError('Unauthorized: Please log in again', 401, responseData);
      } else if (response.status === 403) {
        throw new APIError('Forbidden: You do not have permission', 403, responseData);
      } else if (response.status === 404) {
        throw new APIError('Not found: The requested resource does not exist', 404, responseData);
      } else if (response.status === 429) {
        throw new APIError('Too many requests: Please try again later', 429, responseData);
      } else {
        // General error
        const errorMessage = isJson && responseData.message 
          ? responseData.message 
          : 'An error occurred with the API request';
        throw new APIError(errorMessage, response.status, responseData);
      }
    }
    
    return responseData;
  } catch (error) {
    // Re-throw API errors
    if (error instanceof APIError) {
      throw error;
    }
    
    // Handle network/fetch errors
    console.error('API request failed:', error);
    throw new APIError('Network error: Could not connect to the server', 0);
  }
}

// Authentication API functions
export const authAPI = {
  /**
   * Log in a user with email and password
   * @param {object} credentials - {email, password}
   */
  login: (credentials) => apiRequest('auth/login', 'POST', credentials, false),
  
  /**
   * Register a new user
   * @param {object} userData - User registration data
   */
  register: (userData) => apiRequest('auth/register', 'POST', userData, false),
  
  /**
   * Log out the current user
   */
  logout: () => apiRequest('auth/logout', 'POST', null),
  
  /**
   * Get the current authenticated user
   */
  getCurrentUser: () => apiRequest('auth/me', 'GET', null),
  
  /**
   * Update user profile information
   * @param {object} profileData - Profile data to update
   */
  updateProfile: (profileData) => apiRequest('auth/profile', 'PUT', profileData),
  
  /**
   * Request a password reset email
   * @param {string} email - User's email
   */
  forgotPassword: (email) => apiRequest('auth/forgot-password', 'POST', { email }, false),
  
  /**
   * Reset password using a token
   * @param {string} token - Reset token
   * @param {string} newPassword - New password
   */
  resetPassword: (token, newPassword) => apiRequest('auth/reset-password', 'POST', { token, newPassword }, false),
  
  /**
   * Verify email using a token
   * @param {string} token - Verification token
   */
  verifyEmail: (token) => apiRequest('auth/verify-email', 'POST', { token }, false),
  
  /**
   * Change password for authenticated user
   * @param {string} currentPassword - Current password
   * @param {string} newPassword - New password
   */
  changePassword: (currentPassword, newPassword) => apiRequest('auth/change-password', 'POST', { currentPassword, newPassword })
};

// User API functions
export const userAPI = {
  /**
   * Update user profile
   * @param {object} profileData - Profile data to update
   */
  updateProfile: (profileData) => apiRequest('users/profile', 'PUT', profileData),
  
  /**
   * Get user dashboard statistics
   */
  getDashboardStats: () => apiRequest('users/dashboard-stats', 'GET', null),
  
  /**
   * Update user settings
   * @param {object} settings - User settings
   */
  updateSettings: (settings) => apiRequest('users/settings', 'PUT', settings),
  
  /**
   * Get user activity history
   * @param {object} params - Query parameters
   */
  getActivityHistory: (params) => apiRequest('users/activity', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  })
};

// Text processing API functions
export const textAPI = {
  /**
   * Process text with AI
   * @param {object} data - Text data to process
   */
  processText: (data) => apiRequest('text/process', 'POST', data),
  
  /**
   * Get text processing history
   * @param {object} params - Query parameters
   */
  getHistory: (params) => apiRequest('text/history', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  }),
  
  /**
   * Get a specific processed text by ID
   * @param {string} id - Processed text ID
   */
  getById: (id) => apiRequest(`text/${id}`, 'GET', null),
  
  /**
   * Save a processed text
   * @param {object} data - Processed text data
   */
  saveProcessed: (data) => apiRequest('text/save', 'POST', data),
  
  /**
   * Upload audio for transcription
   * @param {File} audioFile - Audio file to transcribe
   */
  transcribeAudio: (audioFile) => {
    const formData = new FormData();
    formData.append('audio', audioFile);
    
    return apiRequest('text/transcribe', 'POST', null, true, {
      headers: {
        // No Content-Type header for FormData
      },
      body: formData
    });
  }
};

// AR Experience API functions
export const arAPI = {
  /**
   * Get all available AR scenes
   * @param {object} params - Query parameters
   */
  getScenes: (params) => apiRequest('ar/scenes', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  }),
  
  /**
   * Get a specific AR scene by ID
   * @param {string} id - Scene ID
   */
  getSceneById: (id) => apiRequest(`ar/scenes/${id}`, 'GET', null),
  
  /**
   * Launch an AR scene
   * @param {string} sceneId - Scene ID
   * @param {object} options - Scene launch options
   */
  launchScene: (sceneId, options) => apiRequest('ar/launch', 'POST', { sceneId, ...options }),
  
  /**
   * Save a custom AR scene
   * @param {object} sceneData - Scene data
   */
  saveScene: (sceneData) => apiRequest('ar/scenes', 'POST', sceneData),
  
  /**
   * Update an existing AR scene
   * @param {string} id - Scene ID
   * @param {object} sceneData - Scene data
   */
  updateScene: (id, sceneData) => apiRequest(`ar/scenes/${id}`, 'PUT', sceneData),
  
  /**
   * Delete an AR scene
   * @param {string} id - Scene ID
   */
  deleteScene: (id) => apiRequest(`ar/scenes/${id}`, 'DELETE', null),
  
  /**
   * Get user AR preferences
   */
  getPreferences: () => apiRequest('ar/preferences', 'GET', null),
  
  /**
   * Update user AR preferences
   * @param {object} preferences - AR preferences
   */
  updatePreferences: (preferences) => apiRequest('ar/preferences', 'PUT', preferences)
};

// Feedback API functions
export const feedbackAPI = {
  /**
   * Submit user feedback
   * @param {object} feedback - Feedback data
   */
  submitFeedback: (feedback) => apiRequest('feedback', 'POST', feedback),
  
  /**
   * Get feedback history
   * @param {object} params - Query parameters
   */
  getFeedbackHistory: (params) => apiRequest('feedback/history', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  }),
  
  /**
   * Get a specific feedback by ID
   * @param {string} id - Feedback ID
   */
  getFeedbackById: (id) => apiRequest(`feedback/${id}`, 'GET', null),
  
  /**
   * Update a feedback entry
   * @param {string} id - Feedback ID
   * @param {object} feedbackData - Updated feedback data
   */
  updateFeedback: (id, feedbackData) => apiRequest(`feedback/${id}`, 'PUT', feedbackData),
  
  /**
   * Delete feedback
   * @param {string} id - Feedback ID
   */
  deleteFeedback: (id) => apiRequest(`feedback/${id}`, 'DELETE', null)
};

// Notification API functions
export const notificationAPI = {
  /**
   * Get user notifications
   * @param {object} params - Query parameters
   */
  getNotifications: (params) => apiRequest('notifications', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  }),
  
  /**
   * Mark notification as read
   * @param {string} id - Notification ID
   */
  markAsRead: (id) => apiRequest(`notifications/${id}/read`, 'POST', null),
  
  /**
   * Mark all notifications as read
   */
  markAllAsRead: () => apiRequest('notifications/read-all', 'POST', null),
  
  /**
   * Delete a notification
   * @param {string} id - Notification ID
   */
  deleteNotification: (id) => apiRequest(`notifications/${id}`, 'DELETE', null),
  
  /**
   * Update notification preferences
   * @param {object} preferences - Notification preferences
   */
  updatePreferences: (preferences) => apiRequest('notifications/preferences', 'PUT', preferences)
};

// Analytics API functions
export const analyticsAPI = {
  /**
   * Get user usage analytics
   * @param {object} params - Query parameters (timeframe, etc.)
   */
  getUserAnalytics: (params) => apiRequest('analytics/user', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  }),
  
  /**
   * Track an event
   * @param {object} eventData - Event data
   */
  trackEvent: (eventData) => apiRequest('analytics/track', 'POST', eventData),
  
  /**
   * Get performance metrics
   * @param {object} params - Query parameters
   */
  getPerformanceMetrics: (params) => apiRequest('analytics/performance', 'GET', null, true, { 
    headers: {},
    // Convert params object to URL query string
    ...params && { url: new URLSearchParams(params) }
  })
};

// Export all API functions as a combined object
export const api = {
  auth: authAPI,
  user: userAPI,
  text: textAPI,
  ar: arAPI,
  feedback: feedbackAPI,
  notification: notificationAPI,
  analytics: analyticsAPI
};

export default api; 