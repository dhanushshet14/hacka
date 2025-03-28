import React, { createContext, useContext, useState, useCallback, useRef, useReducer, useEffect } from 'react';

/**
 * Creates a context-based state management system
 * @param {string} name - Name of the context (for debugging)
 * @param {object} initialState - Initial state object
 * @param {object} actions - Object containing action creators
 * @param {function} reducer - Optional reducer function for complex state logic
 * @returns {object} The created context provider and hooks
 */
export function createStateContext(name, initialState = {}, actions = {}, reducer = null) {
  // Create the context
  const StateContext = createContext(null);
  const DispatchContext = createContext(null);
  
  // Flag to track if provider is mounted
  const isMounted = useRef(false);
  
  // Create default reducer if none provided
  const defaultReducer = (state, action) => {
    if (action.type === 'SET_STATE') {
      return { ...state, ...action.payload };
    }
    return state;
  };
  
  // Use provided reducer or default
  const stateReducer = reducer || defaultReducer;
  
  // Create the provider component
  const StateProvider = ({ children, overrideInitialState }) => {
    // Warning for duplicate providers
    useEffect(() => {
      if (process.env.NODE_ENV !== 'production') {
        if (isMounted.current) {
          console.warn(`Duplicate ${name} context provider detected. This may cause unexpected behavior.`);
        }
        isMounted.current = true;
        
        return () => {
          isMounted.current = false;
        };
      }
    }, []);
    
    // Initialize the state with override if provided
    const [state, dispatch] = useReducer(
      stateReducer, 
      overrideInitialState || initialState
    );
    
    // Create action dispatcher
    const boundActions = {};
    
    // Bind action creators to dispatch
    for (const [actionName, actionCreator] of Object.entries(actions)) {
      boundActions[actionName] = useCallback(
        (...args) => {
          const action = actionCreator(...args);
          dispatch(action);
          return action;
        },
        [dispatch]
      );
    }
    
    // Add setState utility function
    const setState = useCallback(
      (newState) => {
        dispatch({ type: 'SET_STATE', payload: newState });
      },
      [dispatch]
    );
    
    // Reset state utility function
    const resetState = useCallback(
      () => {
        dispatch({ type: 'SET_STATE', payload: overrideInitialState || initialState });
      },
      [dispatch, overrideInitialState]
    );
    
    // Add debugging helper in development
    const getState = useCallback(() => state, [state]);
    
    // Build context value
    const contextValue = {
      state,
      ...boundActions,
      setState,
      resetState,
      getState
    };
    
    return (
      <DispatchContext.Provider value={dispatch}>
        <StateContext.Provider value={contextValue}>
          {children}
        </StateContext.Provider>
      </DispatchContext.Provider>
    );
  };
  
  // Create hook to use the context
  const useState = () => {
    const context = useContext(StateContext);
    
    if (!context) {
      throw new Error(`use${name}State must be used within a ${name}Provider`);
    }
    
    return context;
  };
  
  // Create hook to use dispatch directly
  const useDispatch = () => {
    const dispatch = useContext(DispatchContext);
    
    if (!dispatch) {
      throw new Error(`use${name}Dispatch must be used within a ${name}Provider`);
    }
    
    return dispatch;
  };
  
  // Create a selector hook
  const useSelector = (selector) => {
    const { state } = useState();
    return selector(state);
  };
  
  return {
    Provider: StateProvider,
    useState,
    useDispatch,
    useSelector,
    Context: StateContext,
    DispatchContext
  };
}

/**
 * Create a simple key-value store with localStorage persistence
 * @param {string} storageKey - Key for localStorage
 * @param {object} initialData - Initial data
 * @returns {object} Store provider and hooks
 */
export function createPersistedStore(storageKey, initialData = {}) {
  // Create context
  const StoreContext = createContext(null);
  
  // Create provider component
  const StoreProvider = ({ children }) => {
    // Load initial state from localStorage if available
    const loadInitialState = () => {
      if (typeof window === 'undefined') return initialData;
      
      try {
        const storedData = localStorage.getItem(storageKey);
        return storedData ? JSON.parse(storedData) : initialData;
      } catch (err) {
        console.error('Failed to load persisted store:', err);
        return initialData;
      }
    };
    
    const [store, setStore] = useState(loadInitialState);
    
    // Persist to localStorage when store changes
    useEffect(() => {
      if (typeof window === 'undefined') return;
      
      try {
        localStorage.setItem(storageKey, JSON.stringify(store));
      } catch (err) {
        console.error('Failed to persist store:', err);
      }
    }, [store]);
    
    // Get a value from the store
    const getValue = useCallback(
      (key) => store[key],
      [store]
    );
    
    // Set a value in the store
    const setValue = useCallback(
      (key, value) => {
        setStore(prevStore => ({
          ...prevStore,
          [key]: value
        }));
      },
      []
    );
    
    // Remove a value from the store
    const removeValue = useCallback(
      (key) => {
        setStore(prevStore => {
          const newStore = { ...prevStore };
          delete newStore[key];
          return newStore;
        });
      },
      []
    );
    
    // Clear the entire store
    const clearStore = useCallback(
      () => {
        setStore(initialData);
      },
      []
    );
    
    // Check if a key exists
    const hasKey = useCallback(
      (key) => Object.prototype.hasOwnProperty.call(store, key),
      [store]
    );
    
    // Get all keys
    const getKeys = useCallback(
      () => Object.keys(store),
      [store]
    );
    
    // Get entire store
    const getAll = useCallback(
      () => ({ ...store }),
      [store]
    );
    
    const contextValue = {
      store,
      getValue,
      setValue,
      removeValue,
      clearStore,
      hasKey,
      getKeys,
      getAll
    };
    
    return (
      <StoreContext.Provider value={contextValue}>
        {children}
      </StoreContext.Provider>
    );
  };
  
  // Hook to use the store
  const useStore = () => {
    const context = useContext(StoreContext);
    
    if (!context) {
      throw new Error('useStore must be used within a StoreProvider');
    }
    
    return context;
  };
  
  return {
    Provider: StoreProvider,
    useStore,
    Context: StoreContext
  };
}

export default createStateContext; 