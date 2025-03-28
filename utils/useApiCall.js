import { useState, useCallback, useRef, useEffect } from 'react';
import { useAuth } from './AuthContext';

/**
 * Custom hook for managing API calls with loading and error states
 * @param {Function} apiFunction - The API function to call
 * @param {Object} options - Configuration options
 * @param {boolean} options.loadOnMount - Whether to load data on mount
 * @param {boolean} options.cache - Whether to cache the results
 * @param {number} options.cacheTime - How long to cache results in ms (default: 5min)
 * @param {Function} options.onSuccess - Callback on successful API call
 * @param {Function} options.onError - Callback on API call error
 * @returns {Object} API call state and control functions
 */
export function useApiCall(apiFunction, {
  loadOnMount = false,
  cache = false,
  cacheTime = 5 * 60 * 1000, // 5 minutes
  onSuccess,
  onError
} = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAuth();
  
  // Use refs for values that shouldn't trigger re-renders
  const cacheRef = useRef({
    timestamp: null,
    data: null,
    params: null
  });
  
  // Function to check if cache is valid
  const isCacheValid = useCallback((params) => {
    if (!cache) return false;
    
    const { timestamp, data, params: cachedParams } = cacheRef.current;
    if (!timestamp || !data) return false;
    
    const isExpired = Date.now() - timestamp > cacheTime;
    if (isExpired) return false;
    
    // Check if the params match (simple equality check)
    const paramsMatch = JSON.stringify(params) === JSON.stringify(cachedParams);
    return paramsMatch;
  }, [cache, cacheTime]);
  
  // Clear the cache
  const clearCache = useCallback(() => {
    cacheRef.current = {
      timestamp: null,
      data: null,
      params: null
    };
  }, []);
  
  // Main execute function
  const execute = useCallback(async (...params) => {
    // Check authentication if needed
    if (apiFunction.requiresAuth && !isAuthenticated) {
      const authError = new Error('Authentication required');
      setError(authError);
      if (onError) onError(authError);
      return;
    }
    
    // Check cache
    if (isCacheValid(params)) {
      setData(cacheRef.current.data);
      return cacheRef.current.data;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...params);
      
      // Update state with the result
      setData(result);
      
      // Cache the result if caching is enabled
      if (cache) {
        cacheRef.current = {
          timestamp: Date.now(),
          data: result,
          params
        };
      }
      
      // Call onSuccess callback if provided
      if (onSuccess) onSuccess(result);
      
      return result;
    } catch (err) {
      setError(err);
      
      // Call onError callback if provided
      if (onError) onError(err);
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, isAuthenticated, isCacheValid, cache, onSuccess, onError]);
  
  // Reset state
  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
    clearCache();
  }, [clearCache]);
  
  // Load data on mount if requested
  useEffect(() => {
    if (loadOnMount) {
      execute();
    }
  }, [loadOnMount, execute]);
  
  return {
    data,
    loading,
    error,
    execute,
    reset,
    clearCache
  };
}

/**
 * Custom hook for polling API endpoints at regular intervals
 * @param {Function} apiFunction - The API function to call
 * @param {number} interval - Polling interval in milliseconds
 * @param {Object} options - Configuration options
 * @param {boolean} options.immediate - Whether to execute immediately
 * @param {boolean} options.stopOnError - Whether to stop polling on error
 * @param {Array} options.dependencies - Dependencies that will restart polling when changed
 * @returns {Object} API call state and control functions
 */
export function useApiPolling(apiFunction, interval = 10000, {
  immediate = true,
  stopOnError = false,
  dependencies = []
} = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(immediate);
  
  const timerRef = useRef(null);
  const { isAuthenticated } = useAuth();
  
  // Clear any existing timer
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);
  
  // Execute the API call
  const executePoll = useCallback(async () => {
    // Skip if not authenticated for auth-required functions
    if (apiFunction.requiresAuth && !isAuthenticated) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction();
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      
      // Stop polling if stopOnError is true
      if (stopOnError) {
        setIsPolling(false);
        clearTimer();
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, isAuthenticated, clearTimer, stopOnError]);
  
  // Start polling
  const startPolling = useCallback(() => {
    // Don't start if already polling
    if (isPolling && timerRef.current) return;
    
    setIsPolling(true);
    
    // Execute immediately if requested
    if (immediate) {
      executePoll();
    }
    
    // Set up the interval
    timerRef.current = setInterval(executePoll, interval);
  }, [executePoll, interval, immediate, isPolling]);
  
  // Stop polling
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    clearTimer();
  }, [clearTimer]);
  
  // Set up polling when dependencies change
  useEffect(() => {
    if (isPolling) {
      clearTimer();
      startPolling();
    }
    
    return () => clearTimer();
  }, [isPolling, startPolling, clearTimer, ...dependencies]);
  
  // Clean up on unmount
  useEffect(() => {
    return () => clearTimer();
  }, [clearTimer]);
  
  return {
    data,
    loading,
    error,
    isPolling,
    startPolling,
    stopPolling,
    executePoll
  };
}

/**
 * Custom hook for handling infinite scrolling with API pagination
 * @param {Function} apiFunction - The API function to fetch paginated data
 * @param {Object} options - Configuration options
 * @param {number} options.initialPage - Initial page to fetch
 * @param {number} options.pageSize - Number of items per page
 * @param {string} options.pageParam - Name of the page parameter
 * @param {string} options.limitParam - Name of the limit parameter
 * @returns {Object} Pagination state and control functions
 */
export function useInfiniteScroll(apiFunction, {
  initialPage = 1,
  pageSize = 10,
  pageParam = 'page',
  limitParam = 'limit'
} = {}) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(initialPage);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Fetch a page of data
  const fetchPage = useCallback(async (pageNumber = page) => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Prepare params object for the API call
      const params = {
        [pageParam]: pageNumber,
        [limitParam]: pageSize
      };
      
      const response = await apiFunction(params);
      
      // Handle different API response formats
      const newItems = response.data || response.items || response.results || response;
      const total = response.total || response.totalCount || response.count;
      
      // Update state based on received data
      if (newItems && newItems.length > 0) {
        if (pageNumber === initialPage) {
          // Replace all items if it's the first page
          setItems(newItems);
        } else {
          // Append items for subsequent pages
          setItems(prev => [...prev, ...newItems]);
        }
        
        // Check if there are more items to fetch
        if (total) {
          setHasMore(items.length + newItems.length < total);
        } else {
          setHasMore(newItems.length >= pageSize);
        }
        
        // Update the page number
        setPage(pageNumber);
      } else {
        // No more items
        setHasMore(false);
      }
      
      return newItems;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, loading, hasMore, page, items.length, pageParam, limitParam, pageSize, initialPage]);
  
  // Load the next page
  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      return fetchPage(page + 1);
    }
  }, [loading, hasMore, fetchPage, page]);
  
  // Refresh data (start from first page)
  const refresh = useCallback(() => {
    setHasMore(true);
    return fetchPage(initialPage);
  }, [fetchPage, initialPage]);
  
  return {
    items,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    page
  };
}

export default useApiCall; 