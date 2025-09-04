import { useState, useEffect } from "react";
import {
  loadingStateManager,
  LoadingStates,
  LoadingState,
} from "../services/loadingStateManager";

/**
 * Hook to use the centralized loading state manager
 * Provides reactive access to loading states across the application
 */
export function useLoadingState() {
  const [states, setStates] = useState<LoadingStates>(
    loadingStateManager.getStates()
  );

  useEffect(() => {
    const unsubscribe = loadingStateManager.subscribe(setStates);
    return unsubscribe;
  }, []);

  return {
    // Current states
    states,

    // Individual state getters
    dataUpload: states.dataUpload,
    dataProcessing: states.dataProcessing,
    queryExecution: states.queryExecution,
    chartGeneration: states.chartGeneration,
    viewTransition: states.viewTransition,
    dashboardUpdate: states.dashboardUpdate,

    // Utility functions
    isAnyLoading: loadingStateManager.isAnyLoading(),

    // State management functions
    startDataUpload: (fileName?: string) =>
      loadingStateManager.startDataUpload(fileName),
    updateDataUploadStage: (
      stage: "validating" | "uploading" | "processing" | "complete",
      progress?: number,
      fileName?: string
    ) => loadingStateManager.updateDataUploadStage(stage, progress, fileName),

    startQueryExecution: (queryText?: string) =>
      loadingStateManager.startQueryExecution(queryText),
    updateQueryExecutionStage: (
      stage: "translating" | "executing" | "generating_chart" | "complete",
      progress?: number,
      queryText?: string
    ) =>
      loadingStateManager.updateQueryExecutionStage(stage, progress, queryText),

    startViewTransition: (fromView: string, toView: string) =>
      loadingStateManager.startViewTransition(fromView, toView),
    completeViewTransition: () => loadingStateManager.completeViewTransition(),

    startDashboardUpdate: () => loadingStateManager.startDashboardUpdate(),
    completeDashboardUpdate: () =>
      loadingStateManager.completeDashboardUpdate(),

    setError: (key: keyof LoadingStates, error: string) =>
      loadingStateManager.setError(key, error),

    clearAll: () => loadingStateManager.clearAll(),
  };
}

/**
 * Hook to use a specific loading state
 */
export function useSpecificLoadingState(
  key: keyof LoadingStates
): LoadingState & {
  elapsedTime: number;
  estimatedRemainingTime: number | null;
} {
  const [state, setState] = useState<LoadingState>(
    loadingStateManager.getState(key)
  );
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    const unsubscribe = loadingStateManager.subscribe((states) => {
      setState(states[key]);
    });
    return unsubscribe;
  }, [key]);

  // Update elapsed time for active loading states
  useEffect(() => {
    if (!state.isLoading) {
      setElapsedTime(0);
      return;
    }

    const interval = setInterval(() => {
      setElapsedTime(loadingStateManager.getElapsedTime(key));
    }, 100);

    return () => clearInterval(interval);
  }, [state.isLoading, key]);

  return {
    ...state,
    elapsedTime,
    estimatedRemainingTime: loadingStateManager.getEstimatedRemainingTime(key),
  };
}

/**
 * Hook for smooth loading transitions with automatic cleanup
 */
export function useLoadingTransition(
  key: keyof LoadingStates,
  options: {
    minDisplayTime?: number; // Minimum time to show loading state (prevents flashing)
    fadeOutDuration?: number; // Time to fade out after completion
  } = {}
) {
  const { minDisplayTime = 300, fadeOutDuration = 200 } = options;
  const [displayState, setDisplayState] = useState<LoadingState>({
    isLoading: false,
  });
  const [isVisible, setIsVisible] = useState(false);

  const actualState = useSpecificLoadingState(key);

  useEffect(() => {
    if (actualState.isLoading) {
      // Show loading immediately
      setDisplayState(actualState);
      setIsVisible(true);
    } else if (displayState.isLoading) {
      // Loading just finished - apply minimum display time and fade out
      const displayDuration = actualState.elapsedTime;

      if (displayDuration < minDisplayTime) {
        // Wait for minimum display time
        const remainingTime = minDisplayTime - displayDuration;
        setTimeout(() => {
          setDisplayState({ ...actualState, isLoading: false });
          // Start fade out
          setTimeout(() => {
            setIsVisible(false);
          }, fadeOutDuration);
        }, remainingTime);
      } else {
        // Can hide immediately
        setDisplayState({ ...actualState, isLoading: false });
        setTimeout(() => {
          setIsVisible(false);
        }, fadeOutDuration);
      }
    }
  }, [actualState, displayState.isLoading, minDisplayTime, fadeOutDuration]);

  return {
    ...displayState,
    isVisible,
    elapsedTime: actualState.elapsedTime,
    estimatedRemainingTime: actualState.estimatedRemainingTime,
  };
}

export default useLoadingState;
