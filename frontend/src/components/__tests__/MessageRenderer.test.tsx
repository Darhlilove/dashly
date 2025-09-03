import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MessageRenderer, { ChatMessage } from "../MessageRenderer";

// Mock ChartRenderer component
vi.mock("../ChartRenderer", () => ({
  ChartRenderer: ({ data, config }: any) => (
    <div data-testid="chart-renderer">
      Chart: {config.type} with {data.rows.length} rows
    </div>
  ),
}));

describe("MessageRenderer", () => {
  const mockOnFollowUpClick = vi.fn();

  beforeEach(() => {
    mockOnFollowUpClick.mockClear();
  });

  describe("User Messages", () => {
    it("renders user message with correct styling", () => {
      const timestamp = new Date("2024-01-01T10:00:00Z");
      const userMessage: ChatMessage = {
        id: "1",
        type: "user",
        content: "What is the total revenue?",
        timestamp,
      };

      render(<MessageRenderer message={userMessage} />);

      const messageElement = screen.getByTestId("message-user");
      expect(messageElement).toBeInTheDocument();
      expect(messageElement).toHaveClass("justify-end");

      expect(
        screen.getByText("What is the total revenue?")
      ).toBeInTheDocument();

      // Check for the formatted time (accounting for timezone)
      const expectedTime = timestamp.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      expect(screen.getByText(expectedTime)).toBeInTheDocument();
    });

    it("does not show insights or follow-up questions for user messages", () => {
      const userMessage: ChatMessage = {
        id: "1",
        type: "user",
        content: "Test message",
        timestamp: new Date(),
        metadata: {
          insights: ["This should not appear"],
          followUpQuestions: ["This should not appear either"],
        },
      };

      render(<MessageRenderer message={userMessage} />);

      expect(screen.queryByText("Key Insights")).not.toBeInTheDocument();
      expect(screen.queryByText("You might also ask")).not.toBeInTheDocument();
    });
  });

  describe("Assistant Messages", () => {
    it("renders assistant message with correct styling", () => {
      const timestamp = new Date("2024-01-01T10:01:00Z");
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "The total revenue is $1,234,567.",
        timestamp,
      };

      render(<MessageRenderer message={assistantMessage} />);

      const messageElement = screen.getByTestId("message-assistant");
      expect(messageElement).toBeInTheDocument();
      expect(messageElement).toHaveClass("justify-start");

      expect(
        screen.getByText("The total revenue is $1,234,567.")
      ).toBeInTheDocument();

      // Check for the formatted time (accounting for timezone)
      const expectedTime = timestamp.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      expect(screen.getByText(expectedTime)).toBeInTheDocument();
    });

    it("displays insights when provided", () => {
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Here's your revenue analysis.",
        timestamp: new Date(),
        metadata: {
          insights: [
            "Revenue increased by 15% this quarter",
            "Q4 was the strongest performing quarter",
          ],
        },
      };

      render(<MessageRenderer message={assistantMessage} />);

      expect(screen.getByText("Key Insights")).toBeInTheDocument();
      expect(
        screen.getByText("Revenue increased by 15% this quarter")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Q4 was the strongest performing quarter")
      ).toBeInTheDocument();
    });

    it("displays follow-up questions as clickable buttons", () => {
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Here's your analysis.",
        timestamp: new Date(),
        metadata: {
          followUpQuestions: [
            "What about last year's revenue?",
            "Show me revenue by region",
            "How does this compare to competitors?",
            "This fourth question should not appear", // Should be limited to 3
          ],
        },
      };

      render(
        <MessageRenderer
          message={assistantMessage}
          onFollowUpClick={mockOnFollowUpClick}
        />
      );

      expect(screen.getByText("You might also ask")).toBeInTheDocument();

      const followUpButtons = screen.getAllByTestId(/follow-up-\d+/);
      expect(followUpButtons).toHaveLength(3); // Should limit to 3 questions

      // Test clicking on follow-up question
      fireEvent.click(followUpButtons[0]);
      expect(mockOnFollowUpClick).toHaveBeenCalledWith(
        "What about last year's revenue?"
      );
    });

    it("renders embedded chart when chart data is provided", () => {
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Here's your revenue chart.",
        timestamp: new Date(),
        metadata: {
          chartConfig: {
            type: "bar",
            x: "month",
            y: "revenue",
          },
          chartData: {
            columns: ["month", "revenue"],
            rows: [
              ["Jan", 1000],
              ["Feb", 1200],
              ["Mar", 1100],
            ],
          },
        },
      };

      render(<MessageRenderer message={assistantMessage} />);

      expect(screen.getByText("Visualization")).toBeInTheDocument();
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      expect(screen.getByText("Chart: bar with 3 rows")).toBeInTheDocument();
    });

    it("does not render chart section when chart data is missing", () => {
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Here's your analysis.",
        timestamp: new Date(),
        metadata: {
          chartConfig: {
            type: "bar",
            x: "month",
            y: "revenue",
          },
          // chartData is missing
        },
      };

      render(<MessageRenderer message={assistantMessage} />);

      expect(screen.queryByText("Visualization")).not.toBeInTheDocument();
      expect(screen.queryByTestId("chart-renderer")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper test ids for different message types", () => {
      const userMessage: ChatMessage = {
        id: "1",
        type: "user",
        content: "Test",
        timestamp: new Date(),
      };

      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Test response",
        timestamp: new Date(),
      };

      const { rerender } = render(<MessageRenderer message={userMessage} />);
      expect(screen.getByTestId("message-user")).toBeInTheDocument();

      rerender(<MessageRenderer message={assistantMessage} />);
      expect(screen.getByTestId("message-assistant")).toBeInTheDocument();
    });

    it("follow-up buttons have proper test ids", () => {
      const assistantMessage: ChatMessage = {
        id: "2",
        type: "assistant",
        content: "Test",
        timestamp: new Date(),
        metadata: {
          followUpQuestions: ["Question 1", "Question 2"],
        },
      };

      render(<MessageRenderer message={assistantMessage} />);

      expect(screen.getByTestId("follow-up-0")).toBeInTheDocument();
      expect(screen.getByTestId("follow-up-1")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles message without metadata", () => {
      const message: ChatMessage = {
        id: "1",
        type: "assistant",
        content: "Simple message",
        timestamp: new Date(),
        // No metadata
      };

      render(<MessageRenderer message={message} />);

      expect(screen.getByText("Simple message")).toBeInTheDocument();
      expect(screen.queryByText("Key Insights")).not.toBeInTheDocument();
      expect(screen.queryByText("You might also ask")).not.toBeInTheDocument();
    });

    it("handles empty insights and follow-up questions arrays", () => {
      const message: ChatMessage = {
        id: "1",
        type: "assistant",
        content: "Message with empty arrays",
        timestamp: new Date(),
        metadata: {
          insights: [],
          followUpQuestions: [],
        },
      };

      render(<MessageRenderer message={message} />);

      expect(screen.getByText("Message with empty arrays")).toBeInTheDocument();
      expect(screen.queryByText("Key Insights")).not.toBeInTheDocument();
      expect(screen.queryByText("You might also ask")).not.toBeInTheDocument();
    });

    it("handles long content with proper text wrapping", () => {
      const longContent =
        "This is a very long message that should wrap properly across multiple lines and maintain good readability even when the content is extensive and detailed.";

      const message: ChatMessage = {
        id: "1",
        type: "assistant",
        content: longContent,
        timestamp: new Date(),
      };

      render(<MessageRenderer message={message} />);

      expect(screen.getByText(longContent)).toBeInTheDocument();
    });
  });
});
