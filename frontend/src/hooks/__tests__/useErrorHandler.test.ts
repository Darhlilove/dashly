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
});

afterEach(() => {
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

describe("useErrorHandler", () => {
  it("should initialize with no error", () => {
    const { result } = renderHook(() => useErrorHandler());

    expect(result.current.error).toBeNull();
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.retryCount).toBe(0);
    expect(result.current.canRetry).toBe(true);
  });

  it("should handle errors correctly", () => {
    const mockOnError = vi.fn();
    const { result } = renderHook(() =>
      useErrorHandler({ onError: mockOnError })
    );

    const testError: ApiError = {
      message: "Test error",
      code: "TEST_ERROR",
    };

    act(() => {
      result.current.handleError(testError);
    });

    expect(result.current.error).toEqual(testError);
    expect(result.current.isRetrying).toBe(false);
    expect(mockOnError).toHaveBeenCalledWith(testError);
    expect(console.error).toHaveBeenCalledWith("Error handled:", testError);
  });

  it("should clear errors correctly", () => {
    const { result } = renderHook(() => useErrorHandler());

    const testError: ApiError = {
      message: "Test error",
      code: "TEST_ERROR",
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
  });

  it("should handle retry logic correctly", async () => {
    const { result } = renderHook(() =>
      useErrorHandler({ maxRetries: 2, retryDelay: 10 })
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
  });

  it("should handle failed retries correctly", async () => {
    const { result } = renderHook(() =>
      useErrorHandler({ maxRetries: 1, retryDelay: 10 })
    );

    const retryError: ApiError = {
      message: "Retry failed",
      code: "RETRY_ERROR",
    };

    const mockRetryFn = vi.fn().mockRejectedValue(retryError);

    await act(async () => {
      await result.current.retry(mockRetryFn);
    });

    expect(result.current.retryCount).toBe(1);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.error).toEqual(retryError);
    expect(mockRetryFn).toHaveBeenCalled();
  });

  it("should respect max retry limit", async () => {
    const { result } = renderHook(() =>
      useErrorHandler({ maxRetries: 1, retryDelay: 10 })
    );

    // Set initial error
    act(() => {
      result.current.handleError({ message: "Initial error", code: "INITIAL" });
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
      result.current.handleError({ message: "Test", code: "TEST" });
    });

    expect(result.current.canRetry).toBe(true);
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
