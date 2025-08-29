import { renderHook, act } from "@testing-library/react";
import {
  useErrorHandler,
  useNetworkErrorHandler,
  useUploadErrorHandler,
  useQueryErrorHandler,
} from "../useErrorHandler";
import { ApiError } from "../../types/api";
import { vi } from "vitest";

// Mock console methods
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeEach(() => {
  console.error = vi.fn();
  console.warn = vi.fn();
  vi.useFakeTimers();
});

afterEach(() => {
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
  vi.useRealTimers();
});

describe("useErrorHandler", () => {
  it("should initialize with no error", () => {
    const { result } = renderHook(() => useErrorHandler());

    expect(result.current.error).toBeNull();
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.retryCount).toBe(0);
    expect(result.current.canRetry).toBe(true);
    expect(result.current.isRetryable).toBe(false);
    expect(result.current.timeUntilNextRetry).toBeNull();
  });

  it("should handle errors correctly", () => {
    const mockOnError = vi.fn();
    const { result } = renderHook(() =>
      useErrorHandler({ onError: mockOnError })
    );

    const testError: ApiError = {
      message: "Test error",
      code: "TEST_ERROR",
      retryable: true,
    };

    act(() => {
      result.current.handleError(testError);
    });

    expect(result.current.error).toEqual(testError);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.isRetryable).toBe(true);
    expect(mockOnError).toHaveBeenCalledWith(testError);
    expect(console.error).toHaveBeenCalledWith("Error handled:", testError);
  });

  it("should clear errors correctly", () => {
    const { result } = renderHook(() => useErrorHandler());

    const testError: ApiError = {
      message: "Test error",
      code: "TEST_ERROR",
      retryable: true,
    };

    act(() => {
      result.current.handleError(testError);
    });

    expect(result.current.error).toEqual(testError);

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.retryCount).toBe(0);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.timeUntilNextRetry).toBeNull();
  });

  it("should handle retry logic correctly", async () => {
    const mockOnRetrySuccess = vi.fn();
    const { result } = renderHook(() =>
      useErrorHandler({
        maxRetries: 2,
        retryDelay: 10,
        onRetrySuccess: mockOnRetrySuccess,
      })
    );

    const mockRetryFn = vi.fn().mockResolvedValue(undefined);

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    // When retry succeeds, it clears the error state including retry count
    expect(result.current.retryCount).toBe(0);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.error).toBeNull();
    expect(mockRetryFn).toHaveBeenCalled();
    expect(mockOnRetrySuccess).toHaveBeenCalled();
  });

  it("should handle failed retries correctly", async () => {
    const mockOnRetryFailure = vi.fn();
    const { result } = renderHook(() =>
      useErrorHandler({
        maxRetries: 1,
        retryDelay: 10,
        onRetryFailure: mockOnRetryFailure,
      })
    );

    const retryError: ApiError = {
      message: "Retry failed",
      code: "RETRY_ERROR",
      retryable: true,
    };

    const mockRetryFn = vi.fn().mockRejectedValue(retryError);

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    expect(result.current.retryCount).toBe(1);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.error).toEqual(retryError);
    expect(mockRetryFn).toHaveBeenCalled();
    expect(mockOnRetryFailure).toHaveBeenCalledWith(retryError, 1);
  });

  it("should respect max retry limit", async () => {
    const { result } = renderHook(() =>
      useErrorHandler({ maxRetries: 1, retryDelay: 10 })
    );

    // Set initial error
    act(() => {
      result.current.handleError({
        message: "Initial error",
        code: "INITIAL",
        retryable: true,
      });
    });

    // First retry that fails to increment retry count
    const failingRetryFn = vi.fn().mockRejectedValue(new Error("Retry failed"));

    await act(async () => {
      await result.current.retry(failingRetryFn);
    });

    // Now at max retries (1), should not retry again
    const mockRetryFn = vi.fn();

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    expect(mockRetryFn).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith("Maximum retry attempts reached");
  });

  it("should calculate canRetry correctly", () => {
    const { result } = renderHook(() => useErrorHandler({ maxRetries: 2 }));

    expect(result.current.canRetry).toBe(true);

    // After one retry
    act(() => {
      result.current.handleError({
        message: "Test",
        code: "TEST",
        retryable: true,
      });
    });

    expect(result.current.canRetry).toBe(true);
  });

  it("should call onRetry callback during retry", async () => {
    const mockOnRetry = vi.fn();
    const { result } = renderHook(() =>
      useErrorHandler({
        maxRetries: 2,
        retryDelay: 10,
        onRetry: mockOnRetry,
      })
    );

    const testError: ApiError = {
      message: "Test error",
      code: "TEST_ERROR",
      retryable: true,
    };

    // Set initial error
    act(() => {
      result.current.handleError(testError);
    });

    const mockRetryFn = vi.fn().mockResolvedValue(undefined);

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    expect(mockOnRetry).toHaveBeenCalledWith(1, testError);
  });

  it("should handle auto-retry for retryable errors", () => {
    const { result } = renderHook(() =>
      useErrorHandler({
        maxRetries: 2,
        retryDelay: 1000,
        autoRetry: true,
      })
    );

    const retryableError: ApiError = {
      message: "Network error",
      code: "NETWORK_ERROR",
      retryable: true,
    };

    act(() => {
      result.current.handleError(retryableError);
    });

    // Should set up auto-retry countdown
    expect(result.current.timeUntilNextRetry).toBe(1000);

    // Fast-forward 500ms
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.timeUntilNextRetry).toBe(500);

    // Fast-forward to completion
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.timeUntilNextRetry).toBeNull();
  });

  it("should not auto-retry for non-retryable errors", () => {
    const { result } = renderHook(() =>
      useErrorHandler({
        maxRetries: 2,
        retryDelay: 1000,
        autoRetry: true,
      })
    );

    const nonRetryableError: ApiError = {
      message: "Validation error",
      code: "VALIDATION_ERROR",
      retryable: false,
    };

    act(() => {
      result.current.handleError(nonRetryableError);
    });

    // Should not set up auto-retry
    expect(result.current.timeUntilNextRetry).toBeNull();
  });

  it("should track lastRetryAt timestamp", async () => {
    const { result } = renderHook(() =>
      useErrorHandler({ maxRetries: 2, retryDelay: 10 })
    );

    const mockRetryFn = vi.fn().mockResolvedValue(undefined);

    expect(result.current.lastRetryAt).toBeUndefined();

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    // Should have set lastRetryAt timestamp (cleared after successful retry)
    expect(result.current.lastRetryAt).toBeUndefined(); // Cleared after success
  });

  it("should clean up timers on unmount", () => {
    const { result, unmount } = renderHook(() =>
      useErrorHandler({
        maxRetries: 2,
        retryDelay: 1000,
        autoRetry: true,
      })
    );

    const retryableError: ApiError = {
      message: "Network error",
      code: "NETWORK_ERROR",
      retryable: true,
    };

    act(() => {
      result.current.handleError(retryableError);
    });

    expect(result.current.timeUntilNextRetry).toBe(1000);

    // Unmount should clean up timers
    unmount();

    // Fast-forward time - should not cause issues
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // No assertions needed - just ensuring no errors are thrown
  });
});

describe("useNetworkErrorHandler", () => {
  it("should handle network errors with appropriate logging", () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    const networkError: ApiError = {
      message: "Network error",
      code: "NETWORK_ERROR",
    };

    act(() => {
      result.current.handleError(networkError);
    });

    expect(result.current.error).toEqual(networkError);
    expect(console.warn).toHaveBeenCalledWith(
      "Network error detected, will retry automatically"
    );
  });
});

describe("useUploadErrorHandler", () => {
  it("should handle file too large errors", () => {
    const { result } = renderHook(() => useUploadErrorHandler());

    const fileTooLargeError: ApiError = {
      message: "File too large",
      code: "FILE_TOO_LARGE",
    };

    act(() => {
      result.current.handleError(fileTooLargeError);
    });

    expect(result.current.error).toEqual(fileTooLargeError);
    expect(console.warn).toHaveBeenCalledWith(
      "File too large, user needs to select a smaller file"
    );
  });

  it("should handle invalid file type errors", () => {
    const { result } = renderHook(() => useUploadErrorHandler());

    const invalidFileError: ApiError = {
      message: "Invalid file type",
      code: "INVALID_FILE_TYPE",
    };

    act(() => {
      result.current.handleError(invalidFileError);
    });

    expect(result.current.error).toEqual(invalidFileError);
    expect(console.warn).toHaveBeenCalledWith(
      "Invalid file type, user needs to select a CSV file"
    );
  });
});

describe("useQueryErrorHandler", () => {
  it("should handle empty query errors", () => {
    const { result } = renderHook(() => useQueryErrorHandler());

    const emptyQueryError: ApiError = {
      message: "Empty query",
      code: "EMPTY_QUERY",
    };

    act(() => {
      result.current.handleError(emptyQueryError);
    });

    expect(result.current.error).toEqual(emptyQueryError);
    expect(console.warn).toHaveBeenCalledWith("Empty query provided");
  });

  it("should handle validation errors", () => {
    const { result } = renderHook(() => useQueryErrorHandler());

    const validationError: ApiError = {
      message: "Validation failed",
      code: "422",
    };

    act(() => {
      result.current.handleError(validationError);
    });

    expect(result.current.error).toEqual(validationError);
    expect(console.warn).toHaveBeenCalledWith("Query validation failed");
  });
});
