import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConversationInterface from "../ConversationInterface";
import MessageRenderer, { ChatMessage } from "../MessageRenderer";

import { vi } from "vitest";

// Mock the useChat hook
vi.mock("../../hooks/useChat", () => ({
  useChat: () => ({
    messages: [],
    isProcessing: false,
    isLoadingHistory: false,
    sendMessage: vi.fn(),
  }),
}));

// Mock the useKeyboardShortcuts hook
vi.mock("../../hooks/useKeyboardShortcuts", () => ({
  useKeyboardShortcuts: vi.fn(),
}));

describe("Chat Interface Accessibility", () => {
  const mockOnSendMessage = vi.fn();
  const mockOnFollowUpClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("ConversationInterface Accessibility", () => {
    it("should render without errors", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
          suggestedQuestions={["What is the total revenue?"]}
        />
      );

      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have proper ARIA labels and semantic HTML", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
          suggestedQuestions={["What is the total revenue?"]}
        />
      );

      // Check main chat area
      expect(screen.getByRole("log")).toHaveAttribute(
        "aria-label",
        "Chat conversation"
      );
      expect(screen.getByRole("log")).toHaveAttribute("aria-live", "polite");

      // Check input area
      expect(screen.getByRole("search")).toBeInTheDocument();
      expect(
        screen.getByLabelText("Ask a question about your data")
      ).toBeInTheDocument();

      // Check suggested questions
      expect(screen.getByRole("list")).toBeInTheDocument();
      expect(screen.getByRole("listitem")).toBeInTheDocument();
    });

    it("should support keyboard navigation for suggested questions", async () => {
      const user = userEvent.setup();

      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
          suggestedQuestions={[
            "What is the total revenue?",
            "Show me sales by region",
            "What are the top products?",
          ]}
        />
      );

      const firstSuggestion = screen.getByText('"What is the total revenue?"');

      // Focus first suggestion
      await user.click(firstSuggestion);
      expect(firstSuggestion).toHaveFocus();

      // Test Enter key
      await user.keyboard("{Enter}");
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        "What is the total revenue?"
      );
    });

    it("should have proper focus management", async () => {
      const user = userEvent.setup();

      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
        />
      );

      const input = screen.getByLabelText("Ask a question about your data");

      // Input should be focused on mount
      expect(input).toHaveFocus();

      // Test form submission
      await user.type(input, "test question");
      await user.keyboard("{Enter}");

      expect(mockOnSendMessage).toHaveBeenCalledWith("test question");
    });

    it("should provide proper status updates for screen readers", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={true}
        />
      );

      // Check processing status
      expect(
        screen.getByText("Processing your question, please wait...")
      ).toHaveClass("sr-only");
      expect(
        screen.getByText("Processing your question, please wait...")
      ).toHaveAttribute("aria-live", "polite");

      // Check typing indicator
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should be responsive on mobile devices", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
        />
      );

      const sendButton = screen.getByRole("button", { name: /send message/i });

      // Check mobile-specific classes and attributes
      expect(sendButton).toHaveClass("min-w-[80px]", "sm:min-w-[100px]");
    });
  });

  describe("MessageRenderer Accessibility", () => {
    const mockMessage: ChatMessage = {
      id: "1",
      type: "assistant",
      content: "Here are your sales results.",
      timestamp: new Date("2024-01-01T12:00:00Z"),
      metadata: {
        insights: ["Revenue increased by 15%", "Top region is North America"],
        followUpQuestions: ["What about last quarter?", "Show me by product"],
        dashboardUpdated: true,
        chartConfig: {
          type: "bar",
          title: "Sales by Region",
          xAxis: { field: "region", label: "Region" },
          yAxis: { field: "sales", label: "Sales" },
        },
        chartData: {
          columns: ["region", "sales"],
          rows: [
            ["North", 1000],
            ["South", 800],
          ],
        },
      },
    };

    it("should render message with proper semantic structure", () => {
      render(
        <MessageRenderer
          message={mockMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      // Check article structure
      expect(screen.getByRole("article")).toBeInTheDocument();
      expect(screen.getByRole("article")).toHaveAttribute("aria-label");

      // Check timestamp
      expect(screen.getByRole("time")).toBeInTheDocument();
      expect(screen.getByRole("time")).toHaveAttribute("datetime");

      // Check sections
      expect(screen.getByText("Key Insights")).toBeInTheDocument();
      expect(screen.getByText("You might also ask")).toBeInTheDocument();
    });

    it("should have proper ARIA labels for interactive elements", () => {
      render(
        <MessageRenderer
          message={mockMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      // Check follow-up questions
      const followUpButtons = screen.getAllByRole("listitem");
      followUpButtons.forEach((button) => {
        const buttonElement = button.querySelector("button");
        if (buttonElement) {
          expect(buttonElement).toHaveAttribute("aria-label");
        }
      });
    });

    it("should support keyboard navigation for follow-up questions", async () => {
      const user = userEvent.setup();

      render(
        <MessageRenderer
          message={mockMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      const firstFollowUp = screen.getByText('"What about last quarter?"');

      await user.click(firstFollowUp);
      await user.keyboard("{Enter}");

      expect(mockOnFollowUpClick).toHaveBeenCalledWith(
        "What about last quarter?"
      );
    });

    it("should provide proper status updates", () => {
      render(
        <MessageRenderer
          message={mockMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      // Check dashboard update status
      const statusElement = screen
        .getByText("Dashboard automatically updated")
        .closest("div");
      expect(statusElement).toHaveAttribute("role", "status");
      expect(statusElement).toHaveAttribute("aria-live", "polite");
    });

    it("should handle chart accessibility", () => {
      render(
        <MessageRenderer
          message={mockMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      // Check chart container
      const chartContainer = screen.getByRole("img");
      expect(chartContainer).toHaveAttribute("aria-label");
      expect(chartContainer.getAttribute("aria-label")).toContain("chart");
    });
  });

  describe("Keyboard Navigation", () => {
    it("should support tab navigation through all interactive elements", async () => {
      const user = userEvent.setup();

      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
          suggestedQuestions={["Question 1", "Question 2"]}
        />
      );

      // Tab through elements
      await user.tab();
      expect(
        screen.getByLabelText("Ask a question about your data")
      ).toHaveFocus();

      await user.tab();
      expect(
        screen.getByRole("button", { name: /send message/i })
      ).toHaveFocus();
    });
  });

  describe("Screen Reader Support", () => {
    it("should provide skip links", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
        />
      );

      const skipLink = screen.getByText("Skip to chat input");
      expect(skipLink).toHaveClass("skip-link");
      expect(skipLink).toHaveAttribute("href", "#chat-input");
    });

    it("should have proper live regions", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
        />
      );

      const chatLog = screen.getByRole("log");
      expect(chatLog).toHaveAttribute("aria-live", "polite");
    });

    it("should announce loading states", () => {
      render(
        <ConversationInterface
          onSendMessage={mockOnSendMessage}
          messages={[]}
          isProcessing={false}
          isLoadingHistory={true}
        />
      );

      const loadingStatus = screen.getByRole("status");
      expect(loadingStatus).toHaveAttribute("aria-live", "polite");
    });
  });
});
