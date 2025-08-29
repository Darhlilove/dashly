import { useCallback, useState } from "react";
import { ApiError } from "../types/api";

interface ErrorState {
  error: ApiError | null;
  isRetrying: boolean;
  retryCount: number;
}

interface UseErrorHandlerOptions {
  maxRetries?: number;
  retryDelay?: number;
  onError?: (error: ApiError) => void;
  showToast?: boolean;
}

interface UseErrorHandlerReturn {
  error: ApiError | null;
  isRetrying: boolean;
  retryCount: number;
  handleError: (error: ApiError) => void;
  clearError: () => void;
  retry: (retryFn: () => Promise<void>) => Promise<void>;
  canRetry: boolean;
}

export const useErrorHandler = (
  options: UseErrorHandlerOptions = {}
): UseErrorHandlerReturn => {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    onError,
    showToast = true,
  } = options;

  const [errorState, setErrorState] = useState<ErrorState>({
    error: null,
    isRetrying: false,
    retryCount: 0,
  });

  const handleError = useCallback(
    (error: ApiError) => {
      console.error("Error handled:", error);

      setErrorState((prev) => ({
        ...prev,
        error,
        isRetrying: false,
      }));

      // Call custom error handler if provided
      onError?.(error);

      // Show toast notification if enabled
      if (showToast && typeof window !== "undefined") {
        // This would integrate with your toast system
        // For now, we'll just log it
        console.warn("Toast notification:", error.message);
      }
    },
    [onError, showToast]
  );

  const clearError = useCallback(() => {
    setErrorState({
      error: null,
      isRetrying: false,
      retryCount: 0,
    });
  }, []);

  const retry = useCallback(
    async (retryFn: () => Promise<void>) => {
      if (errorState.retryCount >= maxRetries) {
        console.warn("Maximum retry attempts reached");
        return;
      }

      const newRetryCount = errorState.retryCount + 1;

      setErrorState((prev) => ({
        ...prev,
        isRetrying: true,
        retryCount: newRetryCount,
      }));

      try {
        // Wait before retrying with exponential backoff
        const delay = retryDelay * Math.pow(2, errorState.retryCount);
        await new Promise((resolve) => setTimeout(resolve, delay));

        await retryFn();

        // Success - clear error state
        clearError();
      } catch (error) {
        console.error("Retry failed:", error);
        setErrorState((prev) => ({
          ...prev,
          isRetrying: false,
          error: error as ApiError,
        }));
      }
    },
    [errorState.retryCount, maxRetries, retryDelay, handleError, clearError]
  );

  const canRetry = errorState.retryCount < maxRetries && !errorState.isRetrying;

  return {
    error: errorState.error,
    isRetrying: errorState.isRetrying,
    retryCount: errorState.retryCount,
    handleError,
    clearError,
    retry,
    canRetry,
  };
};

// Specialized error handlers for different error types
export const useNetworkErrorHandler = () => {
  return useErrorHandler({
    maxRetries: 3,
    retryDelay: 1000,
    onError: (error) => {
      if (error.code === "NETWORK_ERROR") {
        console.warn("Network error detected, will retry automatically");
      }
    },
  });
};

export const useUploadErrorHandler = () => {
  return useErrorHandler({
    maxRetries: 2, // Fewer retries for uploads
    retryDelay: 2000, // Longer delay for uploads
    onError: (error) => {
      if (error.code === "FILE_TOO_LARGE") {
        console.warn("File too large, user needs to select a smaller file");
      } else if (error.code === "INVALID_FILE_TYPE") {
        console.warn("Invalid file type, user needs to select a CSV file");
      }
    },
  });
};

export const useQueryErrorHandler = () => {
  return useErrorHandler({
    maxRetries: 2,
    retryDelay: 1500,
    onError: (error) => {
      if (error.code === "EMPTY_QUERY") {
        console.warn("Empty query provided");
      } else if (error.code === "422") {
        console.warn("Query validation failed");
      }
    },
  });
};

export default useErrorHandler;
