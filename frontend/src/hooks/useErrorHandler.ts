import { useCallback, useState, useRef } from "react";
import { ApiError } from "../types/api";

interface ErrorState {
  error: ApiError | null;
  isRetrying: boolean;
  retryCount: number;
  lastRetryAt?: Date;
}

interface UseErrorHandlerOptions {
  maxRetries?: number;
  retryDelay?: number;
  onError?: (error: ApiError) => void;
  onRetry?: (attempt: number, error: ApiError) => void;
  onRetrySuccess?: () => void;
  onRetryFailure?: (error: ApiError, attempt: number) => void;
  showToast?: boolean;
  autoRetry?: boolean;
}

interface UseErrorHandlerReturn {
  error: ApiError | null;
  isRetrying: boolean;
  retryCount: number;
  lastRetryAt?: Date;
  handleError: (error: ApiError) => void;
  clearError: () => void;
  retry: (retryFn: () => Promise<void>) => Promise<void>;
  canRetry: boolean;
  isRetryable: boolean;
  timeUntilNextRetry: number | null;
}

export const useErrorHandler = (
  options: UseErrorHandlerOptions = {}
): UseErrorHandlerReturn => {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    onError,
    onRetry,
    onRetrySuccess,
    onRetryFailure,
    showToast = true,
    autoRetry = false,
  } = options;

  const [errorState, setErrorState] = useState<ErrorState>({
    error: null,
    isRetrying: false,
    retryCount: 0,
  });

  const retryTimeoutRef = useRef<number | null>(null);
  const [timeUntilNextRetry, setTimeUntilNextRetry] = useState<number | null>(
    null
  );

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

      // Auto-retry if enabled and error is retryable
      if (autoRetry && error.retryable && errorState.retryCount < maxRetries) {
        const delay = retryDelay * Math.pow(2, errorState.retryCount);
        setTimeUntilNextRetry(delay);

        // Update countdown
        const countdownInterval = setInterval(() => {
          setTimeUntilNextRetry((prev) => {
            if (prev === null || prev <= 1000) {
              clearInterval(countdownInterval);
              return null;
            }
            return prev - 1000;
          });
        }, 1000);

        retryTimeoutRef.current = setTimeout(() => {
          clearInterval(countdownInterval);
          setTimeUntilNextRetry(null);
          // Auto-retry would happen here if we had the retry function
        }, delay);
      }
    },
    [
      onError,
      showToast,
      autoRetry,
      errorState.retryCount,
      maxRetries,
      retryDelay,
    ]
  );

  const clearError = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    setTimeUntilNextRetry(null);
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
      const currentError = errorState.error;

      setErrorState((prev) => ({
        ...prev,
        isRetrying: true,
        retryCount: newRetryCount,
        lastRetryAt: new Date(),
      }));

      // Clear any pending auto-retry
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      setTimeUntilNextRetry(null);

      // Call retry callback if provided
      if (onRetry && currentError) {
        onRetry(newRetryCount, currentError);
      }

      try {
        // Wait before retrying with exponential backoff
        const delay = retryDelay * Math.pow(2, errorState.retryCount);
        await new Promise((resolve) => setTimeout(resolve, delay));

        await retryFn();

        // Success - clear error state
        onRetrySuccess?.();
        clearError();
      } catch (error) {
        console.error("Retry failed:", error);
        const apiError = error as ApiError;

        setErrorState((prev) => ({
          ...prev,
          isRetrying: false,
          error: apiError,
        }));

        // Call retry failure callback
        onRetryFailure?.(apiError, newRetryCount);
      }
    },
    [
      errorState.retryCount,
      errorState.error,
      maxRetries,
      retryDelay,
      onRetry,
      onRetrySuccess,
      onRetryFailure,
      clearError,
    ]
  );

  const canRetry = errorState.retryCount < maxRetries && !errorState.isRetrying;
  const isRetryable = errorState.error?.retryable ?? false;

  return {
    error: errorState.error,
    isRetrying: errorState.isRetrying,
    retryCount: errorState.retryCount,
    lastRetryAt: errorState.lastRetryAt,
    handleError,
    clearError,
    retry,
    canRetry,
    isRetryable,
    timeUntilNextRetry,
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
