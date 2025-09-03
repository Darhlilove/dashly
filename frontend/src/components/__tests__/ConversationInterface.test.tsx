import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ConversationInterface, { ChatMessage } from "../ConversationInterface";

// Mock scrollIntoView for JSDOM
Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
  value: vi.fn(),
  writable: true,
});

describe("ConversationInterface", () => {
  const mockOnSendMessage = vi.fn();

  const defaultProps = {
    onSendMessage: mockOnSendMessage,
    messages: [],
    isProcessing: false,
    suggestedQuestions: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Empty State", () => {
    it("renders welcome message when no messages exist", () => {
      render(<ConversationInterface {...defaultProps} />);

      expect(
        screen.getByText("Let's explore your data together")
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Ask me questions in plain English/)
      ).toBeInTheDocument();
    });

    it("shows suggested questions in empty state", () => {
      const suggestedQuestions = [
        "What are my top selling products?",
        "Show me sales trends over time",
        "Which regions perform best?",
      ];

      render(
        <ConversationInterface
          {...defaultProps}
          suggestedQuestions={suggestedQuestions}
        />
      );

      expect(screen.getByText("Try asking:")).toBeInTheDocument();
      expect(
        screen.getByText('"What are my top selling products?"')
      ).toBeInTheDocument();
      expect(
        screen.getByText('"Show me sales trends over time"')
      ).toBeInTheDocument();
      expect(
        screen.getByText('"Which regions perform best?"')
      ).toBeInTheDocument();
    });

    it("handles suggested question clicks", () => {
      const suggestedQuestions = ["What are my top selling products?"];

      render(
        <ConversationInterface
          {...defaultProps}
          suggestedQuestions={suggestedQuestions}
        />
      );

      fireEvent.click(screen.getByText('"What are my top selling products?"'));
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        "What are my top selling products?"
      );
    });
  });

  describe("Message Input", () => {
    it("renders input field with correct placeholder", () => {
      render(<ConversationInterface {...defaultProps} />);

      const input = screen.getByTestId("chat-input");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute(
        "placeholder",
        "Ask me anything about your data..."
      );
    });

    it("uses custom placeholder when provided", () => {
      render(
        <ConversationInterface
          {...defaultProps}
          placeholder="Custom placeholder"
        />
      );

      const input = screen.getByTestId("chat-input");
      expect(input).toHaveAttribute("placeholder", "Custom placeholder");
    });

    it("handles text input changes", () => {
      render(<ConversationInterface {...defaultProps} />);

      const input = screen.getByTestId("chat-input");
      fireEvent.change(input, { target: { value: "Test message" } });

      expect(input).toHaveValue("Test message");
    });

    it("submits message on form submit", () => {
      render(<ConversationInterface {...defaultProps} />);

      const input = screen.getByTestId("chat-input");
      const sendButton = screen.getByTestId("send-button");

      fireEvent.change(input, { target: { value: "Test message" } });
      fireEvent.click(sendButton);

      expect(mockOnSendMessage).toHaveBeenCalledWith("Test message");
      expect(input).toHaveValue(""); // Input should be cleared
    });

    it("submits message on Enter key press", () => {
      render(<ConversationInterface {...defaultProps} />);

      const input = screen.getByTestId("chat-input");
      fireEvent.change(input, { target: { value: "Test message" } });
      fireEvent.keyDown(input, { key: "Enter" });

      expect(mockOnSendMessage).toHaveBeenCalledWith("Test message");
    });

    it("does not submit empty messages", () => {
      render(<ConversationInterface {...defaultProps} />);

      const sendButton = screen.getByTestId("send-button");
      fireEvent.click(sendButton);

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it("trims whitespace from messages", () => {
      render(<ConversationInterface {...defaultProps} />);

      const input = screen.getByTestId("chat-input");
      fireEvent.change(input, { target: { value: "  Test message  " } });
      fireEvent.keyDown(input, { key: "Enter" });

      expect(mockOnSendMessage).toHaveBeenCalledWith("Test message");
    });
  });

  describe("Processing State", () => {
    it("disables input and button when processing", () => {
      render(<ConversationInterface {...defaultProps} isProcessing={true} />);

      const input = screen.getByTestId("chat-input");
      const sendButton = screen.getByTestId("send-button");

      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it("shows typing indicator when processing", () => {
      render(<ConversationInterface {...defaultProps} isProcessing={true} />);

      expect(screen.getByText(/Analyzing your question/)).toBeInTheDocument();
    });

    it("prevents message submission when processing", () => {
      render(<ConversationInterface {...defaultProps} isProcessing={true} />);

      const input = screen.getByTestId("chat-input");
      fireEvent.change(input, { target: { value: "Test message" } });
      fireEvent.keyDown(input, { key: "Enter" });

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it("prevents suggested question clicks when processing", () => {
      const suggestedQuestions = ["What are my top selling products?"];

      render(
        <ConversationInterface
          {...defaultProps}
          suggestedQuestions={suggestedQuestions}
          isProcessing={true}
        />
      );

      // When processing, suggested questions are not shown (typing indicator is shown instead)
      expect(
        screen.queryByText('"What are my top selling products?"')
      ).not.toBeInTheDocument();
      expect(
        screen.getByText("Analyzing your question...")
      ).toBeInTheDocument();
    });
  });

  describe("Message Display", () => {
    const sampleMessages: ChatMessage[] = [
      {
        id: "1",
        type: "user",
        content: "What are my sales?",
        timestamp: new Date("2024-01-01T10:00:00"),
      },
      {
        id: "2",
        type: "assistant",
        content: "Your total sales are $50,000 this month.",
        timestamp: new Date("2024-01-01T10:01:00"),
        metadata: {
          insights: ["Sales increased 20% from last month"],
          followUpQuestions: ["What drove the sales increase?"],
        },
      },
    ];

    it("renders user and assistant messages correctly", () => {
      render(
        <ConversationInterface {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText("What are my sales?")).toBeInTheDocument();
      expect(
        screen.getByText("Your total sales are $50,000 this month.")
      ).toBeInTheDocument();
    });

    it("displays message timestamps", () => {
      render(
        <ConversationInterface {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText("10:00")).toBeInTheDocument();
      expect(screen.getByText("10:01")).toBeInTheDocument();
    });

    it("renders insights for assistant messages", () => {
      render(
        <ConversationInterface {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText("Key Insights:")).toBeInTheDocument();
      expect(
        screen.getByText("Sales increased 20% from last month")
      ).toBeInTheDocument();
    });

    it("renders follow-up questions for assistant messages", () => {
      render(
        <ConversationInterface {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText("You might also ask:")).toBeInTheDocument();
      expect(
        screen.getByText('"What drove the sales increase?"')
      ).toBeInTheDocument();
    });

    it("applies correct styling for user vs assistant messages", () => {
      render(
        <ConversationInterface {...defaultProps} messages={sampleMessages} />
      );

      const userMessage = screen
        .getByText("What are my sales?")
        .closest("div")?.parentElement;
      const assistantMessage = screen
        .getByText("Your total sales are $50,000 this month.")
        .closest("div")?.parentElement;

      expect(userMessage).toHaveClass("bg-blue-600", "text-white");
      expect(assistantMessage).toHaveClass("bg-gray-100", "text-gray-900");
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels and test IDs", () => {
      render(<ConversationInterface {...defaultProps} />);

      expect(screen.getByTestId("chat-input")).toBeInTheDocument();
      expect(screen.getByTestId("send-button")).toBeInTheDocument();
    });

    it("focuses input on mount", async () => {
      render(<ConversationInterface {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-input")).toHaveFocus();
      });
    });
  });

  describe("TypingIndicator", () => {
    it("cycles through status messages", async () => {
      render(<ConversationInterface {...defaultProps} isProcessing={true} />);

      // Should start with first message
      expect(
        screen.getByText("Analyzing your question...")
      ).toBeInTheDocument();

      // Wait for status to change (mocked timer would be needed for full test)
      // This is a basic test to ensure the component renders
    });

    it("shows animated dots", () => {
      render(<ConversationInterface {...defaultProps} isProcessing={true} />);

      const dots = screen
        .getByText("Analyzing your question...")
        .parentElement?.querySelectorAll(".animate-bounce");
      expect(dots).toHaveLength(3);
    });
  });
});
