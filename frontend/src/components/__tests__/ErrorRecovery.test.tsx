import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ErrorRecovery from "../ErrorRecovery";
import { ErrorMessage } from "../../types/ui";

describe("ErrorRecovery", () => {
  const mockErrorMessage: ErrorMessage = {
    id: "test-error",
    type: "assistant",
    content: "Test error occurred",
    timestamp: new Date(),
    isError: true,
    errorPhase: "translation",
    userFriendlyMessage: "I couldn't understand your question",
    suggestions: [
      "Try rephrasing your question",
      "Use simpler language",
      "Ask about one thing at a time",
    ],
    retryable: true,
    recoveryActions: [
      {
        type: "retry",
        label: "Try Again",
        description: "Retry the same query",
      },
      {
        type: "rephrase",
        label: "Rephrase Question",
        description: "Ask your question in a different way",
      },
    ],
    errorCode: "TRANSLATION_FAILED",
  };

  it("should render error message with user-friendly text", () => {
    render(<ErrorRecovery error={mockErrorMessage} />);

    expect(
      screen.getByText("Couldn't understand your question")
    ).toBeInTheDocument();
    expect(
      screen.getByText("I couldn't understand your question")
    ).toBeInTheDocument();
    expect(screen.getByText("TRANSLATION_FAILED")).toBeInTheDocument();
  });

  it("should render suggestions", () => {
    render(<ErrorRecovery error={mockErrorMessage} />);

    expect(screen.getByText("Try this:")).toBeInTheDocument();
    expect(
      screen.getByText("Try rephrasing your question")
    ).toBeInTheDocument();
    expect(screen.getByText("Use simpler language")).toBeInTheDocument();
    expect(
      screen.getByText("Ask about one thing at a time")
    ).toBeInTheDocument();
  });

  it("should render recovery actions as buttons", () => {
    render(<ErrorRecovery error={mockErrorMessage} />);

    expect(screen.getByText("What would you like to do?")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try Again" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Rephrase Question" })
    ).toBeInTheDocument();
  });

  it("should call recovery action when button is clicked", () => {
    const mockAction = vi.fn();
    const errorWithAction: ErrorMessage = {
      ...mockErrorMessage,
      recoveryActions: [
        {
          type: "retry",
          label: "Try Again",
          description: "Retry the same query",
          action: mockAction,
        },
      ],
    };

    render(<ErrorRecovery error={errorWithAction} />);

    const retryButton = screen.getByRole("button", { name: "Try Again" });
    fireEvent.click(retryButton);

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it("should call prop handlers when no action is provided", () => {
    const onRetry = vi.fn();
    const onRephrase = vi.fn();

    const errorWithoutActions: ErrorMessage = {
      ...mockErrorMessage,
      recoveryActions: [
        {
          type: "retry",
          label: "Try Again",
          description: "Retry the same query",
        },
        {
          type: "rephrase",
          label: "Rephrase Question",
          description: "Ask your question in a different way",
        },
      ],
    };

    render(
      <ErrorRecovery
        error={errorWithoutActions}
        onRetry={onRetry}
        onRephrase={onRephrase}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Try Again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Rephrase Question" }));
    expect(onRephrase).toHaveBeenCalledTimes(1);
  });

  it("should show retry hint for retryable errors", () => {
    render(<ErrorRecovery error={mockErrorMessage} />);

    expect(
      screen.getByText(/This error might be temporary/)
    ).toBeInTheDocument();
  });

  it("should not show retry hint for non-retryable errors", () => {
    const nonRetryableError: ErrorMessage = {
      ...mockErrorMessage,
      retryable: false,
    };

    render(<ErrorRecovery error={nonRetryableError} />);

    expect(
      screen.queryByText(/This error might be temporary/)
    ).not.toBeInTheDocument();
  });

  it("should show technical details in collapsible section", () => {
    const errorWithDetails: ErrorMessage = {
      ...mockErrorMessage,
      originalError: "Detailed technical error message",
    };

    render(<ErrorRecovery error={errorWithDetails} />);

    expect(screen.getByText("Technical details")).toBeInTheDocument();

    // Click to expand details
    fireEvent.click(screen.getByText("Technical details"));
    expect(
      screen.getByText("Detailed technical error message")
    ).toBeInTheDocument();
  });

  it("should render different icons and titles for different error phases", () => {
    const executionError: ErrorMessage = {
      ...mockErrorMessage,
      errorPhase: "execution",
    };

    render(<ErrorRecovery error={executionError} />);
    expect(screen.getByText("Query execution failed")).toBeInTheDocument();

    const networkError: ErrorMessage = {
      ...mockErrorMessage,
      errorPhase: "network",
    };

    render(<ErrorRecovery error={networkError} />);
    expect(screen.getByText("Connection problem")).toBeInTheDocument();
  });

  it("should limit suggestions to 3 items", () => {
    const errorWithManySuggestions: ErrorMessage = {
      ...mockErrorMessage,
      suggestions: [
        "Suggestion 1",
        "Suggestion 2",
        "Suggestion 3",
        "Suggestion 4",
        "Suggestion 5",
      ],
    };

    render(<ErrorRecovery error={errorWithManySuggestions} />);

    expect(screen.getByText("Suggestion 1")).toBeInTheDocument();
    expect(screen.getByText("Suggestion 2")).toBeInTheDocument();
    expect(screen.getByText("Suggestion 3")).toBeInTheDocument();
    expect(screen.queryByText("Suggestion 4")).not.toBeInTheDocument();
    expect(screen.queryByText("Suggestion 5")).not.toBeInTheDocument();
  });

  it("should handle contact support action", () => {
    // Mock window.open
    const mockOpen = vi.fn();
    Object.defineProperty(window, "open", {
      value: mockOpen,
      writable: true,
    });

    const errorWithSupport: ErrorMessage = {
      ...mockErrorMessage,
      recoveryActions: [
        {
          type: "contact_support",
          label: "Get Help",
          description: "Contact support for assistance",
        },
      ],
    };

    render(<ErrorRecovery error={errorWithSupport} />);

    fireEvent.click(screen.getByRole("button", { name: "Get Help" }));
    expect(mockOpen).toHaveBeenCalledWith(
      "mailto:support@dashly.com?subject=Error Report",
      "_blank"
    );
  });
});
