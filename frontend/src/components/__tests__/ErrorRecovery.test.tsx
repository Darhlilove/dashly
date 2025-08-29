import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import ErrorRecovery from "../ErrorRecovery";
import { ApiError } from "../../types/api";

describe("ErrorRecovery", () => {
  const mockOnRetry = vi.fn();
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const networkError: ApiError = {
    message: "Network connection failed",
    code: "NETWORK_ERROR",
    retryable: true,
    timestamp: "2023-01-01T00:00:00Z",
    requestId: "req_123",
  };

  const validationError: ApiError = {
    message: "Invalid file format",
    code: "VALIDATION_ERROR",
    retryable: false,
    timestamp: "2023-01-01T00:00:00Z",
    requestId: "req_456",
  };

  it("should render error information correctly", () => {
    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText("Connection Problem")).toBeInTheDocument();
    expect(screen.getByText("Network connection failed")).toBeInTheDocument();
    expect(
      screen.getByText("Check your internet connection and try again.")
    ).toBeInTheDocument();
  });

  it("should show retry button for retryable errors", () => {
    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        currentRetryCount={1}
        maxRetries={3}
      />
    );

    const retryButton = screen.getByRole("button", {
      name: /try again.*2 left/i,
    });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).not.toBeDisabled();
  });

  it("should not show retry button for non-retryable errors", () => {
    render(
      <ErrorRecovery
        error={validationError}
        onRetry={mockOnRetry}
        onDismiss={mockOnDismiss}
      />
    );

    expect(
      screen.queryByRole("button", { name: /try again/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /dismiss/i })
    ).toBeInTheDocument();
  });

  it("should disable retry button when max retries reached", () => {
    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        currentRetryCount={3}
        maxRetries={3}
      />
    );

    expect(
      screen.queryByRole("button", { name: /try again/i })
    ).not.toBeInTheDocument();
  });

  it("should call onRetry when retry button is clicked", async () => {
    mockOnRetry.mockResolvedValue(undefined);

    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        currentRetryCount={0}
        maxRetries={3}
      />
    );

    const retryButton = screen.getByRole("button", {
      name: /try again.*3 left/i,
    });
    fireEvent.click(retryButton);

    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it("should show loading state during retry", async () => {
    let resolveRetry: () => void;
    const retryPromise = new Promise<void>((resolve) => {
      resolveRetry = resolve;
    });
    mockOnRetry.mockReturnValue(retryPromise);

    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        currentRetryCount={0}
        maxRetries={3}
      />
    );

    const retryButton = screen.getByRole("button", {
      name: /try again.*3 left/i,
    });
    fireEvent.click(retryButton);

    // Should show loading state
    expect(screen.getByText("Retrying...")).toBeInTheDocument();
    expect(retryButton).toBeDisabled();

    // Resolve the retry
    resolveRetry!();
    await waitFor(() => {
      expect(screen.queryByText("Retrying...")).not.toBeInTheDocument();
    });
  });

  it("should call onDismiss when dismiss button is clicked", () => {
    render(
      <ErrorRecovery
        error={validationError}
        onRetry={mockOnRetry}
        onDismiss={mockOnDismiss}
      />
    );

    const dismissButton = screen.getByRole("button", { name: /dismiss/i });
    fireEvent.click(dismissButton);

    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("should show technical details when enabled and toggled", () => {
    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        showTechnicalDetails={true}
      />
    );

    // Initially details should be hidden
    expect(screen.queryByText("Error Code:")).not.toBeInTheDocument();

    // Click show details button
    const showDetailsButton = screen.getByRole("button", {
      name: /show details/i,
    });
    fireEvent.click(showDetailsButton);

    // Details should now be visible
    expect(screen.getByText("Error Code:")).toBeInTheDocument();
    expect(screen.getByText("NETWORK_ERROR")).toBeInTheDocument();
    expect(screen.getByText("req_123")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument(); // Retryable: Yes

    // Click hide details button
    const hideDetailsButton = screen.getByRole("button", {
      name: /hide details/i,
    });
    fireEvent.click(hideDetailsButton);

    // Details should be hidden again
    expect(screen.queryByText("Error Code:")).not.toBeInTheDocument();
  });

  it("should not show technical details button when disabled", () => {
    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        showTechnicalDetails={false}
      />
    );

    expect(
      screen.queryByRole("button", { name: /show details/i })
    ).not.toBeInTheDocument();
  });

  it("should display appropriate error titles for different error types", () => {
    const testCases = [
      {
        error: { ...networkError, code: "NETWORK_ERROR" },
        expectedTitle: "Connection Problem",
      },
      {
        error: { ...networkError, code: "TIMEOUT_ERROR" },
        expectedTitle: "Request Timeout",
      },
      {
        error: { ...networkError, code: "VALIDATION_ERROR" },
        expectedTitle: "Invalid Input",
      },
      {
        error: { ...networkError, code: "FILE_TOO_LARGE" },
        expectedTitle: "File Too Large",
      },
      {
        error: { ...networkError, code: "INVALID_FILE_TYPE" },
        expectedTitle: "Invalid File Type",
      },
      {
        error: { ...networkError, code: "SERVICE_UNAVAILABLE" },
        expectedTitle: "Service Unavailable",
      },
      {
        error: { ...networkError, code: "RATE_LIMIT_ERROR" },
        expectedTitle: "Too Many Requests",
      },
      {
        error: { ...networkError, code: "UNKNOWN_ERROR", retryable: true },
        expectedTitle: "Temporary Error",
      },
      {
        error: { ...networkError, code: "UNKNOWN_ERROR", retryable: false },
        expectedTitle: "Error",
      },
    ];

    testCases.forEach(({ error, expectedTitle }) => {
      const { unmount } = render(
        <ErrorRecovery error={error as ApiError} onRetry={mockOnRetry} />
      );

      expect(screen.getByText(expectedTitle)).toBeInTheDocument();
      unmount();
    });
  });

  it("should display appropriate suggestions for different error types", () => {
    const testCases = [
      {
        error: { ...networkError, code: "NETWORK_ERROR" },
        expectedSuggestion: "Check your internet connection and try again.",
      },
      {
        error: { ...networkError, code: "TIMEOUT_ERROR" },
        expectedSuggestion:
          "The request took too long. Try again or check your connection.",
      },
      {
        error: { ...networkError, code: "FILE_TOO_LARGE" },
        expectedSuggestion: "Please select a smaller file (under 10MB).",
      },
      {
        error: { ...networkError, code: "INVALID_FILE_TYPE" },
        expectedSuggestion: "Please select a valid CSV file.",
      },
      {
        error: { ...networkError, code: "RATE_LIMIT_ERROR" },
        expectedSuggestion: "Please wait a moment before trying again.",
      },
    ];

    testCases.forEach(({ error, expectedSuggestion }) => {
      const { unmount } = render(
        <ErrorRecovery error={error as ApiError} onRetry={mockOnRetry} />
      );

      expect(screen.getByText(expectedSuggestion)).toBeInTheDocument();
      unmount();
    });
  });

  it("should handle retry failures gracefully", async () => {
    const retryError = new Error("Retry failed");
    mockOnRetry.mockRejectedValue(retryError);

    // Mock console.error to avoid noise in test output
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorRecovery
        error={networkError}
        onRetry={mockOnRetry}
        currentRetryCount={0}
        maxRetries={3}
      />
    );

    const retryButton = screen.getByRole("button", {
      name: /try again.*3 left/i,
    });
    fireEvent.click(retryButton);

    // Wait for retry to complete
    await waitFor(() => {
      expect(screen.queryByText("Retrying...")).not.toBeInTheDocument();
    });

    expect(consoleSpy).toHaveBeenCalledWith("Retry failed:", retryError);
    consoleSpy.mockRestore();
  });
});
