/**
 * Loading State Manager
 * Centralized management of loading states and user feedback across the application
 * Requirements: 1.5, 5.1, 5.2, 5.3 - Proper loading indicators, progress feedback, smooth transitions
 */

export interface LoadingState {
  isLoading: boolean;
  stage?: string;
  progress?: number;
  message?: string;
  startTime?: number;
  estimatedDuration?: number;
  error?: string;
}

export interface LoadingStates {
  dataUpload: LoadingState;
  dataProcessing: LoadingState;
  queryExecution: LoadingState;
  chartGeneration: LoadingState;
  viewTransition: LoadingState;
  dashboardUpdate: LoadingState;
}

type LoadingStateKey = keyof LoadingStates;
type LoadingStateListener = (states: LoadingStates) => void;

class LoadingStateManager {
  private states: LoadingStates = {
    dataUpload: { isLoading: false },
    dataProcessing: { isLoading: false },
    queryExecution: { isLoading: false },
    chartGeneration: { isLoading: false },
    viewTransition: { isLoading: false },
    dashboardUpdate: { isLoading: false },
  };

  private listeners: Set<LoadingStateListener> = new Set();

  /**
   * Subscribe to loading state changes
   */
  subscribe(listener: LoadingStateListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify all listeners of state changes
   */
  private notify(): void {
    this.listeners.forEach((listener) => listener({ ...this.states }));
  }

  /**
   * Get current loading states
   */
  getStates(): LoadingStates {
    return { ...this.states };
  }

  /**
   * Get specific loading state
   */
  getState(key: LoadingStateKey): LoadingState {
    return { ...this.states[key] };
  }

  /**
   * Set loading state for a specific operation
   */
  setLoadingState(key: LoadingStateKey, state: Partial<LoadingState>): void {
    const currentState = this.states[key];

    // If starting a new loading operation, record start time
    if (state.isLoading && !currentState.isLoading) {
      state.startTime = Date.now();
    }

    // If stopping loading, clear transient state
    if (state.isLoading === false) {
      this.states[key] = {
        isLoading: false,
        stage: undefined,
        progress: undefined,
        message: undefined,
        startTime: undefined,
        estimatedDuration: undefined,
        error: state.error,
      };
    } else {
      this.states[key] = {
        ...currentState,
        ...state,
      };
    }

    this.notify();
  }

  /**
   * Start loading for a specific operation
   */
  startLoading(
    key: LoadingStateKey,
    options: {
      stage?: string;
      message?: string;
      estimatedDuration?: number;
    } = {}
  ): void {
    this.setLoadingState(key, {
      isLoading: true,
      stage: options.stage,
      message: options.message,
      estimatedDuration: options.estimatedDuration,
      progress: 0,
      error: undefined,
    });
  }

  /**
   * Update loading progress
   */
  updateProgress(
    key: LoadingStateKey,
    progress: number,
    stage?: string,
    message?: string
  ): void {
    const currentState = this.states[key];
    if (!currentState.isLoading) return;

    this.setLoadingState(key, {
      progress: Math.max(0, Math.min(100, progress)),
      stage: stage || currentState.stage,
      message: message || currentState.message,
    });
  }

  /**
   * Update loading stage
   */
  updateStage(
    key: LoadingStateKey,
    stage: string,
    message?: string,
    progress?: number
  ): void {
    const currentState = this.states[key];
    if (!currentState.isLoading) return;

    this.setLoadingState(key, {
      stage,
      message: message || currentState.message,
      progress: progress !== undefined ? progress : currentState.progress,
    });
  }

  /**
   * Complete loading operation
   */
  completeLoading(key: LoadingStateKey, message?: string): void {
    this.setLoadingState(key, {
      isLoading: false,
      progress: 100,
      message,
    });
  }

  /**
   * Set loading error
   */
  setError(key: LoadingStateKey, error: string): void {
    this.setLoadingState(key, {
      isLoading: false,
      error,
    });
  }

  /**
   * Clear all loading states
   */
  clearAll(): void {
    Object.keys(this.states).forEach((key) => {
      this.states[key as LoadingStateKey] = { isLoading: false };
    });
    this.notify();
  }

  /**
   * Check if any operation is loading
   */
  isAnyLoading(): boolean {
    return Object.values(this.states).some((state) => state.isLoading);
  }

  /**
   * Get elapsed time for a loading operation
   */
  getElapsedTime(key: LoadingStateKey): number {
    const state = this.states[key];
    if (!state.isLoading || !state.startTime) return 0;
    return Date.now() - state.startTime;
  }

  /**
   * Get estimated remaining time for a loading operation
   */
  getEstimatedRemainingTime(key: LoadingStateKey): number | null {
    const state = this.states[key];
    if (!state.isLoading || !state.estimatedDuration || !state.startTime) {
      return null;
    }

    const elapsed = this.getElapsedTime(key);
    const remaining = state.estimatedDuration - elapsed;
    return Math.max(0, remaining);
  }

  /**
   * Data Upload Operations
   */
  startDataUpload(fileName?: string): void {
    this.startLoading("dataUpload", {
      stage: "validating",
      message: fileName ? `Validating ${fileName}...` : "Validating file...",
      estimatedDuration: 8000, // 8 seconds estimated
    });
  }

  updateDataUploadStage(
    stage: "validating" | "uploading" | "processing" | "complete",
    progress?: number,
    fileName?: string
  ): void {
    const messages = {
      validating: fileName ? `Validating ${fileName}...` : "Validating file...",
      uploading: fileName ? `Uploading ${fileName}...` : "Uploading file...",
      processing: fileName ? `Processing ${fileName}...` : "Processing file...",
      complete: fileName
        ? `${fileName} uploaded successfully!`
        : "File uploaded successfully!",
    };

    if (stage === "complete") {
      this.completeLoading("dataUpload", messages[stage]);
    } else {
      this.updateStage("dataUpload", stage, messages[stage], progress);
    }
  }

  /**
   * Query Execution Operations
   */
  startQueryExecution(queryText?: string): void {
    this.startLoading("queryExecution", {
      stage: "translating",
      message: queryText
        ? `Understanding: "${queryText.substring(0, 50)}${
            queryText.length > 50 ? "..." : ""
          }"`
        : "Converting your question to SQL...",
      estimatedDuration: 6500, // 6.5 seconds estimated
    });
  }

  updateQueryExecutionStage(
    stage: "translating" | "executing" | "generating_chart" | "complete",
    progress?: number,
    queryText?: string
  ): void {
    const messages = {
      translating: queryText
        ? `Understanding: "${queryText.substring(0, 50)}${
            queryText.length > 50 ? "..." : ""
          }"`
        : "Converting your question to SQL...",
      executing: "Running your query...",
      generating_chart: "Creating visualization...",
      complete: "Query completed successfully!",
    };

    if (stage === "complete") {
      this.completeLoading("queryExecution", messages[stage]);
    } else {
      this.updateStage("queryExecution", stage, messages[stage], progress);
    }
  }

  /**
   * View Transition Operations
   */
  startViewTransition(fromView: string, toView: string): void {
    this.startLoading("viewTransition", {
      stage: "transitioning",
      message: `Switching from ${fromView} to ${toView} view...`,
      estimatedDuration: 500, // 500ms for smooth transitions
    });
  }

  completeViewTransition(): void {
    this.completeLoading("viewTransition", "View transition complete");
  }

  /**
   * Dashboard Update Operations
   */
  startDashboardUpdate(): void {
    this.startLoading("dashboardUpdate", {
      stage: "updating",
      message: "Updating dashboard with new visualization...",
      estimatedDuration: 1000, // 1 second estimated
    });
  }

  completeDashboardUpdate(): void {
    this.completeLoading("dashboardUpdate", "Dashboard updated successfully");
  }
}

// Export singleton instance
export const loadingStateManager = new LoadingStateManager();
export default loadingStateManager;
