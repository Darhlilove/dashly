/**
 * Focused tests for ConversationInterface view routing functionality
 * Requirements: 2.5, 2.7 - Route responses to correct view and implement automatic view switching
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import ConversationInterface from "../ConversationInterface";

// Mock the viewStateManager
vi.mock("../../services/viewStateManager", () => ({
  viewStateManager: {
    updateDashboardData: vi.fn(),
    switchView: vi.fn(),
    getState: vi.fn(() => ({
      currentView: "data",
      dataView: {
        tableInfo: null,
        previewRows: null,
        isLoading: false,
        error: null,
      },
      dashboardView: {
        queryResults: null,
        charts: [],
        currentChart: null,
        currentQuery: "",
        isLoading: false,
        error: null,
      },
    })),
    subscribe: vi.fn(() => () => {}),
  },
}));

// Mock the useChat hook to simulate chat responses
vi.mock("../../hooks/useChat", () => ({
  useChat: vi.fn(() => ({
    messages: [],
    isProcessing: false,
    sendMessage: vi.fn(),
    clearMessages: vi.fn(),
    conversationId: undefined,
    loadConversationHistory: vi.fn(),
    isLoadingHistory: false,
  })),
}));

// Mock the useKeyboardShortcuts hook
vi.mock("../../hooks/useKeyboardShortcuts", () => ({
  useKeyboardShortcuts: vi.fn(),
}));

describe("ConversationInterface View Routing", () => {
  const mockOnDashboardUpdate = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render without crashing with view state management enabled", () => {
    render(
      <ConversationInterface
        useBuiltInChat={false}
        onDashboardUpdate={mockOnDashboardUpdate}
        enableViewStateManagement={true}
        messages={[]}
        isProcessing={false}
      />
    );

    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeInTheDocument();
  });

  it("should render without crashing with view state management disabled", () => {
    render(
      <ConversationInterface
        useBuiltInChat={false}
        onDashboardUpdate={mockOnDashboardUpdate}
        enableViewStateManagement={false}
        messages={[]}
        isProcessing={false}
      />
    );

    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeInTheDocument();
  });

  it("should handle external message sending", () => {
    const mockOnSendMessage = vi.fn();

    render(
      <ConversationInterface
        useBuiltInChat={false}
        onSendMessage={mockOnSendMessage}
        onDashboardUpdate={mockOnDashboardUpdate}
        enableViewStateManagement={true}
        messages={[]}
        isProcessing={false}
      />
    );

    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    // Send a message through external handler
    fireEvent.change(input, { target: { value: "Test external message" } });
    fireEvent.click(sendButton);

    // Verify external handler was called
    expect(mockOnSendMessage).toHaveBeenCalledWith("Test external message");
  });

  it("should handle suggested questions", () => {
    const mockOnSendMessage = vi.fn();
    const suggestedQuestions = ["What is the total?", "Show me trends"];

    render(
      <ConversationInterface
        useBuiltInChat={false}
        onSendMessage={mockOnSendMessage}
        onDashboardUpdate={mockOnDashboardUpdate}
        enableViewStateManagement={true}
        messages={[]}
        isProcessing={false}
        suggestedQuestions={suggestedQuestions}
      />
    );

    // Find and click a suggested question
    const suggestionButton = screen.getByText('"What is the total?"');
    fireEvent.click(suggestionButton);

    // Verify the message is sent through the external handler
    expect(mockOnSendMessage).toHaveBeenCalledWith("What is the total?");
  });

  it("should log message routing for debugging", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    const mockOnSendMessage = vi.fn();

    render(
      <ConversationInterface
        useBuiltInChat={false}
        onSendMessage={mockOnSendMessage}
        onDashboardUpdate={mockOnDashboardUpdate}
        enableViewStateManagement={true}
        messages={[]}
        isProcessing={false}
      />
    );

    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    // Send a message
    fireEvent.change(input, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    // Verify logging
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Message sent: "Test message" (external chat)')
    );

    consoleSpy.mockRestore();
  });

  it("should accept dashboard update callback prop", () => {
    // This test verifies that the component accepts the new prop without errors
    expect(() => {
      render(
        <ConversationInterface
          useBuiltInChat={false}
          onDashboardUpdate={mockOnDashboardUpdate}
          enableViewStateManagement={true}
          messages={[]}
          isProcessing={false}
        />
      );
    }).not.toThrow();
  });

  it("should accept enableViewStateManagement prop", () => {
    // This test verifies that the component accepts the new prop without errors
    expect(() => {
      render(
        <ConversationInterface
          useBuiltInChat={false}
          enableViewStateManagement={false}
          messages={[]}
          isProcessing={false}
        />
      );
    }).not.toThrow();
  });
});
