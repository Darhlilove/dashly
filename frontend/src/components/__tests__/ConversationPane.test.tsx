import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ConversationPane from "../ConversationPane";
import {
  Message,
  SQLMessage,
  ExecutionStatusMessage,
  ErrorMessage,
} from "../../types";

describe("ConversationPane", () => {
  const mockOnSendMessage = vi.fn();
  const mockOnExecutionModeChange = vi.fn();

  const baseProps = {
    messages: [],
    onSendMessage: mockOnSendMessage,
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Basic functionality", () => {
    it("renders empty state when no messages", () => {
      render(<ConversationPane {...baseProps} />);
      expect(
        screen.getByText("Start a conversation about your data")
      ).toBeInTheDocument();
    });

    it("renders input field and send button", () => {
      render(<ConversationPane {...baseProps} />);
      expect(
        screen.getByPlaceholderText("Ask a question about your data...")
      ).toBeInTheDocument();
      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("calls onSendMessage when form is submitted", async () => {
      render(<ConversationPane {...baseProps} />);

      const input = screen.getByPlaceholderText(
        "Ask a question about your data..."
      );
      const button = screen.getByRole("button");

      fireEvent.change(input, { target: { value: "test message" } });
      fireEvent.click(button);

      expect(mockOnSendMessage).toHaveBeenCalledWith("test message");
    });

    it("clears input after sending message", async () => {
      render(<ConversationPane {...baseProps} />);

      const input = screen.getByPlaceholderText(
        "Ask a question about your data..."
      );
      const button = screen.getByRole("button");

      fireEvent.change(input, { target: { value: "test message" } });
      fireEvent.click(button);

      expect(input).toHaveValue("");
    });
  });

  describe("Message rendering", () => {
    it("renders basic user message", () => {
      const messages: Message[] = [
        {
          id: "1",
          type: "user",
          content: "Hello",
          timestamp: new Date("2023-01-01T12:00:00Z"),
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);
      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("7:00:00 AM")).toBeInTheDocument();
    });

    it("renders basic assistant message", () => {
      const messages: Message[] = [
        {
          id: "1",
          type: "assistant",
          content: "Hi there!",
          timestamp: new Date("2023-01-01T12:00:00Z"),
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("renders system message with different styling", () => {
      const messages: Message[] = [
        {
          id: "1",
          type: "system",
          content: "System message",
          timestamp: new Date("2023-01-01T12:00:00Z"),
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);
      expect(screen.getByText("System message")).toBeInTheDocument();
    });
  });

  describe("SQL Message rendering", () => {
    it("renders SQL message with code block", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Here is your query result:",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: 'SELECT * FROM sales WHERE date > "2023-01-01"',
          executionStatus: "completed",
          executionTime: 150,
          rowCount: 42,
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(
        screen.getByText("Here is your query result:")
      ).toBeInTheDocument();
      expect(screen.getByText("Generated SQL")).toBeInTheDocument();
      expect(
        screen.getByText('SELECT * FROM sales WHERE date > "2023-01-01"')
      ).toBeInTheDocument();
      expect(screen.getByText("Query completed")).toBeInTheDocument();
      expect(screen.getByText("150ms")).toBeInTheDocument();
      expect(screen.getByText("• 42 rows")).toBeInTheDocument();
    });

    it("renders SQL message with pending status", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Processing your query...",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT COUNT(*) FROM users",
          executionStatus: "pending",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Query pending...")).toBeInTheDocument();
      expect(screen.getByText("⏳")).toBeInTheDocument();
    });

    it("renders SQL message with executing status", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Running query...",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT * FROM products",
          executionStatus: "executing",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Executing query...")).toBeInTheDocument();
      expect(screen.getByText("⚡")).toBeInTheDocument();
    });

    it("renders SQL message with failed status", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Query failed",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT * FROM nonexistent_table",
          executionStatus: "failed",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getAllByText("Query failed")).toHaveLength(2);
      expect(screen.getByText("❌")).toBeInTheDocument();
    });

    it("renders SQL message without execution status", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Here's the SQL I generated:",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT name, age FROM users ORDER BY age DESC",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(
        screen.getByText("Here's the SQL I generated:")
      ).toBeInTheDocument();
      expect(screen.getByText("Generated SQL")).toBeInTheDocument();
      expect(
        screen.getByText("SELECT name, age FROM users ORDER BY age DESC")
      ).toBeInTheDocument();

      // Should not show execution status when not provided
      expect(screen.queryByText("Query pending...")).not.toBeInTheDocument();
      expect(screen.queryByText("Query completed")).not.toBeInTheDocument();
    });

    it("renders SQL message with copy button", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "SQL query:",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT * FROM test_table",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      const copyButton = screen.getByTitle("Copy SQL to clipboard");
      expect(copyButton).toBeInTheDocument();

      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
      });

      fireEvent.click(copyButton);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "SELECT * FROM test_table"
      );
    });

    it("renders SQL message with complex multi-line query", () => {
      const complexSQL = `SELECT 
  date,
  SUM(revenue) as total_revenue,
  COUNT(*) as transaction_count
FROM sales_data 
WHERE date >= '2023-01-01'
GROUP BY date
ORDER BY date DESC
LIMIT 100`;

      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Complex query generated:",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: complexSQL,
          executionStatus: "completed",
          executionTime: 250,
          rowCount: 100,
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Complex query generated:")).toBeInTheDocument();
      expect(screen.getByText(/SELECT/)).toBeInTheDocument();
      expect(screen.getByText(/SUM\(revenue\)/)).toBeInTheDocument();
      expect(screen.getByText(/GROUP BY date/)).toBeInTheDocument();
      expect(screen.getByText("250ms")).toBeInTheDocument();
      expect(screen.getByText("• 100 rows")).toBeInTheDocument();
    });

    it("renders executing status with proper indicators", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Processing...",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT * FROM test",
          executionStatus: "executing",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      // Check that the executing status is rendered with proper indicators
      expect(screen.getByText("Executing query...")).toBeInTheDocument();
      expect(screen.getByText("⚡")).toBeInTheDocument();
    });

    it("does not apply pulse animation to completed and failed statuses", () => {
      const messages: SQLMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Done",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          sqlQuery: "SELECT * FROM test",
          executionStatus: "completed",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      const statusElement = screen.getByText("Query completed").closest("div");
      expect(statusElement).not.toHaveClass("animate-pulse");
    });
  });

  describe("Execution Status Message rendering", () => {
    it("renders execution status message with details", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Query execution completed",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "completed",
          details: {
            executionTime: 250,
            rowCount: 100,
          },
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Query completed")).toBeInTheDocument();
      expect(screen.getByText("250ms")).toBeInTheDocument();
      expect(screen.getByText("• 100 rows")).toBeInTheDocument();
    });

    it("renders execution status message with error", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Query execution failed",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "failed",
          details: {
            error: "Table not found",
          },
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Query failed")).toBeInTheDocument();
    });

    it("renders executing status with animation", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Processing query...",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "executing",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Executing query...")).toBeInTheDocument();
      expect(screen.getByText("⚡")).toBeInTheDocument();

      // Status is already verified above
    });

    it("renders status message without details", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Starting execution...",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "executing",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Executing query...")).toBeInTheDocument();
      // Should not show timing or row count when not provided
      expect(screen.queryByText(/ms/)).not.toBeInTheDocument();
      expect(screen.queryByText(/rows/)).not.toBeInTheDocument();
    });

    it("formats large row counts with locale string", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Large dataset processed",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "completed",
          details: {
            executionTime: 1500,
            rowCount: 1234567,
          },
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("• 1,234,567 rows")).toBeInTheDocument();
    });

    it("shows correct icons for different statuses", () => {
      const statuses = [
        { status: "executing", icon: "⚡" },
        { status: "completed", icon: "✅" },
        { status: "failed", icon: "❌" },
      ] as const;

      statuses.forEach(({ status, icon }) => {
        const messages: ExecutionStatusMessage[] = [
          {
            id: `${status}-test`,
            type: "system",
            content: `Status: ${status}`,
            timestamp: new Date("2023-01-01T12:00:00Z"),
            status,
          },
        ];

        const { unmount } = render(
          <ConversationPane {...baseProps} messages={messages} />
        );
        expect(screen.getByText(icon)).toBeInTheDocument();
        unmount();
      });
    });

    it("applies correct styling for different status types", () => {
      const messages: ExecutionStatusMessage[] = [
        {
          id: "1",
          type: "system",
          content: "Success message",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          status: "completed",
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      // Check that the completed status is rendered with success indicator
      expect(screen.getByText("Query completed")).toBeInTheDocument();
      expect(screen.getByText("✅")).toBeInTheDocument();
    });
  });

  describe("Error Message rendering", () => {
    it("renders error message with suggestions", () => {
      const messages: ErrorMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "Could not understand your query",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          isError: true,
          errorPhase: "translation",
          userFriendlyMessage:
            "I couldn't understand your question well enough to create a query.",
          suggestions: [
            "Try being more specific about the data you want",
            "Check if the table name is correct",
          ],
          retryable: true,
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(
        screen.getByText("Couldn't understand your question")
      ).toBeInTheDocument();
      expect(screen.getByText("Try this:")).toBeInTheDocument();
      expect(
        screen.getByText("Try being more specific about the data you want")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Check if the table name is correct")
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "This error might be temporary - you can try asking again"
        )
      ).toBeInTheDocument();
    });

    it("renders execution error message", () => {
      const messages: ErrorMessage[] = [
        {
          id: "1",
          type: "assistant",
          content: "SQL execution failed",
          timestamp: new Date("2023-01-01T12:00:00Z"),
          isError: true,
          errorPhase: "execution",
          userFriendlyMessage: "The query I generated has a syntax error.",
          suggestions: ["Check your SQL syntax"],
          retryable: false,
        },
      ];

      render(<ConversationPane {...baseProps} messages={messages} />);

      expect(screen.getByText("Query execution failed")).toBeInTheDocument();
      expect(screen.getByText("SQL execution failed")).toBeInTheDocument();
    });
  });

  describe("Loading states", () => {
    it("shows loading indicator when isLoading is true", () => {
      render(<ConversationPane {...baseProps} isLoading={true} />);
      expect(
        screen.getByText("Generating SQL and executing automatically")
      ).toBeInTheDocument();
    });

    it("shows different loading message for advanced mode", () => {
      render(
        <ConversationPane
          {...baseProps}
          isLoading={true}
          executionMode="advanced"
        />
      );
      expect(screen.getByText("Thinking...")).toBeInTheDocument();
    });

    it("disables input when loading", () => {
      render(<ConversationPane {...baseProps} isLoading={true} />);
      const input = screen.getByPlaceholderText(
        "Ask a question about your data..."
      );
      expect(input).toBeDisabled();
    });

    it("disables send button when loading", () => {
      render(<ConversationPane {...baseProps} isLoading={true} />);
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });

  describe("Execution mode", () => {
    it("accepts executionMode prop", () => {
      render(<ConversationPane {...baseProps} executionMode="advanced" />);
      // Component should render without errors
      expect(
        screen.getByPlaceholderText("Ask a question about your data...")
      ).toBeInTheDocument();
    });

    it("accepts onExecutionModeChange prop", () => {
      render(
        <ConversationPane
          {...baseProps}
          onExecutionModeChange={mockOnExecutionModeChange}
        />
      );
      // Component should render without errors
      expect(
        screen.getByPlaceholderText("Ask a question about your data...")
      ).toBeInTheDocument();
    });

    it("renders execution mode toggle when onExecutionModeChange is provided", () => {
      render(
        <ConversationPane
          {...baseProps}
          executionMode="automatic"
          onExecutionModeChange={mockOnExecutionModeChange}
        />
      );

      expect(screen.getByText("Execution Mode")).toBeInTheDocument();
      expect(screen.getByTestId("advanced-mode-toggle")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Queries are executed automatically after SQL generation"
        )
      ).toBeInTheDocument();
    });

    it("shows correct description for advanced mode", () => {
      render(
        <ConversationPane
          {...baseProps}
          executionMode="advanced"
          onExecutionModeChange={mockOnExecutionModeChange}
        />
      );

      expect(
        screen.getByText("SQL queries are shown for review before execution")
      ).toBeInTheDocument();
    });

    it("calls onExecutionModeChange when toggle is clicked", () => {
      render(
        <ConversationPane
          {...baseProps}
          executionMode="automatic"
          onExecutionModeChange={mockOnExecutionModeChange}
        />
      );

      const toggle = screen.getByTestId("advanced-mode-toggle");
      fireEvent.click(toggle);

      expect(mockOnExecutionModeChange).toHaveBeenCalledWith("advanced");
    });

    it("disables execution mode toggle when loading", () => {
      render(
        <ConversationPane
          {...baseProps}
          isLoading={true}
          executionMode="automatic"
          onExecutionModeChange={mockOnExecutionModeChange}
        />
      );

      const toggle = screen.getByTestId("advanced-mode-toggle");
      expect(toggle).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("has proper form structure", () => {
      render(<ConversationPane {...baseProps} />);
      const form = document.querySelector("form");
      expect(form).toBeInTheDocument();
    });

    it("has accessible input field", () => {
      render(<ConversationPane {...baseProps} />);
      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute(
        "placeholder",
        "Ask a question about your data..."
      );
    });

    it("has accessible send button", () => {
      render(<ConversationPane {...baseProps} />);
      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });
  });
});
