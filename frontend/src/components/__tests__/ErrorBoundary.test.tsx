import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorBoundary from "../ErrorBoundary";
import { vi } from "vitest";

// Mock console methods
const originalConsoleError = console.error;

beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

// Test component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({
  shouldThrow = true,
}) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>No error</div>;
};

describe("ErrorBoundary", () => {
  it("should render children when there is no error", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText("No error")).toBeInTheDocument();
  });

  it("should render error UI when there is an error (page level)", () => {
    render(
      <ErrorBoundary level="page">
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText("Oops! Something went wrong")).toBeInTheDocument();
    // Check for the main error message (not in technical details)
    const errorMessages = screen.getAllByText("Test error");
    expect(errorMessages.length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", { name: /try again/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /refresh page/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /go to home/i })
    ).toBeInTheDocument();
  });

  it("should render component-level error UI when level is component", () => {
    render(
      <ErrorBoundary level="component">
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText("Component Error")).toBeInTheDocument();
    expect(screen.getByText("Test error")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /try again/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /refresh page/i })
    ).toBeInTheDocument();
  });

  it("should render custom fallback when provided", () => {
    const customFallback = <div>Custom error message</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom error message")).toBeInTheDocument();
  });

  it("should call onError callback when error occurs", () => {
    const mockOnError = vi.fn();

    render(
      <ErrorBoundary onError={mockOnError}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(mockOnError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it("should handle retry functionality", () => {
    render(
      <ErrorBoundary level="page">
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText("Oops! Something went wrong")).toBeInTheDocument();

    const retryButton = screen.getByRole("button", {
      name: /try again.*3 attempts left/i,
    });
    fireEvent.click(retryButton);

    // After retry, should show the component again (but it will still throw)
    expect(screen.getByText("Oops! Something went wrong")).toBeInTheDocument();

    // Should now show 2 attempts left
    expect(
      screen.getByRole("button", { name: /try again.*2 attempts left/i })
    ).toBeInTheDocument();
  });

  it("should disable retry after max attempts", () => {
    render(
      <ErrorBoundary level="page">
        <ThrowError />
      </ErrorBoundary>
    );

    // Click retry 3 times to exhaust attempts
    const retryButton1 = screen.getByRole("button", {
      name: /try again.*3 attempts left/i,
    });
    fireEvent.click(retryButton1);

    const retryButton2 = screen.getByRole("button", {
      name: /try again.*2 attempts left/i,
    });
    fireEvent.click(retryButton2);

    const retryButton3 = screen.getByRole("button", {
      name: /try again.*1 attempts left/i,
    });
    fireEvent.click(retryButton3);

    // Should no longer show retry button
    expect(
      screen.queryByRole("button", { name: /try again/i })
    ).not.toBeInTheDocument();
  });

  it("should provide user-friendly error messages for common errors", () => {
    const ChunkLoadError: React.FC = () => {
      throw new Error("ChunkLoadError: Loading chunk failed");
    };

    render(
      <ErrorBoundary level="page">
        <ChunkLoadError />
      </ErrorBoundary>
    );

    expect(
      screen.getByText(
        "Failed to load application resources. Please refresh the page."
      )
    ).toBeInTheDocument();
  });

  it("should handle network errors with appropriate message", () => {
    const NetworkError: React.FC = () => {
      throw new Error("Network Error: Failed to fetch");
    };

    render(
      <ErrorBoundary level="page">
        <NetworkError />
      </ErrorBoundary>
    );

    expect(
      screen.getByText(
        "Network connection error. Please check your internet connection."
      )
    ).toBeInTheDocument();
  });

  it("should handle TypeError with generic message", () => {
    const TypeErrorComponent: React.FC = () => {
      throw new TypeError("Cannot read property of undefined");
    };

    render(
      <ErrorBoundary level="page">
        <TypeErrorComponent />
      </ErrorBoundary>
    );

    expect(
      screen.getByText(
        "A technical error occurred. Our team has been notified."
      )
    ).toBeInTheDocument();
  });

  it("should show technical details when expanded", () => {
    render(
      <ErrorBoundary level="page">
        <ThrowError />
      </ErrorBoundary>
    );

    const detailsButton = screen.getByText("Show technical details");
    fireEvent.click(detailsButton);

    expect(screen.getByText("Retry Count:")).toBeInTheDocument();
    expect(screen.getByText("Stack Trace:")).toBeInTheDocument();
    expect(screen.getByText("Component Stack:")).toBeInTheDocument();
  });

  it("should log error details to console", () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(console.error).toHaveBeenCalledWith(
      "ErrorBoundary caught an error:",
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );

    expect(console.error).toHaveBeenCalledWith(
      "Error Report:",
      expect.objectContaining({
        message: "Test error",
        timestamp: expect.any(String),
        userAgent: expect.any(String),
        url: expect.any(String),
      })
    );
  });
});
