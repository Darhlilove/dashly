import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import ConversationInterface from "../ConversationInterface";
import { apiService } from "../../services/api";
import { ApiError, ConversationalResponse } from "../../types/api";

// Mock the API service
vi.mock("../../services/api", () => ({
  apiService: {
    sendChatMessage: vi.fn(),
  },
}));

describe("ConversationInterface Chat Error Handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should handle chat errors gracefully", async () => {
    const mockError: ApiError = {
      message:
        "I couldn't find that information in your data. It looks like you're asking about something that might not be available in the dataset.",
      code: "COLUMN_NOT_FOUND",
      retryable: false,
    };

    // Mock API to reject with error
    vi.mocked(apiService.sendChatMessage).mockRejectedValue(mockError);

    const onError = vi.fn();

    render(
      <ConversationInterface
        useBuiltInChat={true}
        onError={onError}
        placeholder="Ask about your data..."
      />
    );

    // Type a message and send it
    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    fireEvent.change(input, {
      target: { value: "Show me invalid_column data" },
    });
    fireEvent.click(sendButton);

    // Wait for the error message to appear
    await waitFor(() => {
      expect(
        screen.getByText(/couldn't find that information/i)
      ).toBeInTheDocument();
    });

    // Verify error callback was called
    expect(onError).toHaveBeenCalledWith(mockError);

    // Verify follow-up questions are shown
    expect(
      screen.getByText(/try rephrasing your question/i)
    ).toBeInTheDocument();
  });

  it("should handle successful chat responses", async () => {
    const mockResponse: ConversationalResponse = {
      message:
        "Here's what I found in your sales data. The total revenue for last month was $125,000.",
      chart_config: {
        type: "bar",
        title: "Monthly Revenue",
      },
      insights: ["Revenue increased by 15% compared to previous month"],
      follow_up_questions: [
        "How does this compare to last year?",
        "What drove the increase?",
      ],
      processing_time_ms: 1250,
      conversation_id: "test-conv-123",
    };

    // Mock API to resolve with response
    vi.mocked(apiService.sendChatMessage).mockResolvedValue(mockResponse);

    const onSuccess = vi.fn();

    render(
      <ConversationInterface
        useBuiltInChat={true}
        onSuccess={onSuccess}
        placeholder="Ask about your data..."
      />
    );

    // Type a message and send it
    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    fireEvent.change(input, { target: { value: "Show me sales data" } });
    fireEvent.click(sendButton);

    // Wait for the response to appear
    await waitFor(() => {
      expect(
        screen.getByText(/Here's what I found in your sales data/i)
      ).toBeInTheDocument();
    });

    // Verify success callback was called
    expect(onSuccess).toHaveBeenCalledWith(mockResponse);

    // Verify insights are shown
    expect(screen.getByText(/Revenue increased by 15%/i)).toBeInTheDocument();

    // Verify follow-up questions are shown
    expect(
      screen.getByText(/How does this compare to last year/i)
    ).toBeInTheDocument();
  });

  it("should show typing indicator while processing", async () => {
    // Mock API to take some time
    vi.mocked(apiService.sendChatMessage).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                message: "Response",
                insights: [],
                follow_up_questions: [],
                processing_time_ms: 1000,
                conversation_id: "test",
              }),
            100
          )
        )
    );

    render(
      <ConversationInterface
        useBuiltInChat={true}
        placeholder="Ask about your data..."
      />
    );

    // Type a message and send it
    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    fireEvent.change(input, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    // Should show typing indicator
    await waitFor(() => {
      expect(screen.getByText(/analyzing your question/i)).toBeInTheDocument();
    });

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText("Response")).toBeInTheDocument();
    });
  });

  it("should handle network errors with appropriate messaging", async () => {
    const networkError: ApiError = {
      message:
        "I'm having trouble connecting right now. Please check your internet connection and try again.",
      code: "NETWORK_ERROR",
      retryable: true,
    };

    vi.mocked(apiService.sendChatMessage).mockRejectedValue(networkError);

    render(
      <ConversationInterface
        useBuiltInChat={true}
        placeholder="Ask about your data..."
      />
    );

    const input = screen.getByTestId("chat-input");
    const sendButton = screen.getByTestId("send-button");

    fireEvent.change(input, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/trouble connecting/i)).toBeInTheDocument();
    });

    // Should show network-specific suggestions
    expect(
      screen.getByText(/check your internet connection/i)
    ).toBeInTheDocument();
  });
});
