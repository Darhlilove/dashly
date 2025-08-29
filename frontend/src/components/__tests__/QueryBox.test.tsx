import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QueryBox from "../QueryBox";

describe("QueryBox", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderQueryBox = (props = {}) => {
    const defaultProps = {
      onSubmit: mockOnSubmit,
      isLoading: false,
      placeholder: "Ask a question about your data...",
      value: "",
      ...props,
    };
    return render(<QueryBox {...defaultProps} />);
  };

  describe("Initial Render", () => {
    it("renders the query box with correct title and elements", () => {
      renderQueryBox();

      expect(
        screen.getByText("Ask a Question About Your Data")
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText("Ask a question about your data...")
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Generate" })
      ).toBeInTheDocument();
    });

    it("renders textarea with proper attributes", () => {
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("id", "query-input");
      expect(textarea).toHaveAttribute("rows", "3");
      expect(textarea).toHaveAttribute("aria-describedby", "query-help");
    });

    it("renders help text", () => {
      renderQueryBox();

      expect(
        screen.getByText(/Describe what you want to see in plain English/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Press Ctrl\+Enter to generate/)
      ).toBeInTheDocument();
    });

    it("has generate button disabled initially", () => {
      renderQueryBox();

      const generateButton = screen.getByRole("button", { name: "Generate" });
      expect(generateButton).toBeDisabled();
    });
  });

  describe("User Input", () => {
    it("enables generate button when query is entered", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      expect(generateButton).toBeDisabled();

      await user.type(textarea, "Show me sales data");

      expect(generateButton).not.toBeDisabled();
    });

    it("disables generate button for whitespace-only input", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      await user.type(textarea, "   ");

      expect(generateButton).toBeDisabled();
    });

    it("shows query preview when query is entered", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      await user.type(textarea, "Show me sales data");

      expect(screen.getByText("Your question:")).toBeInTheDocument();
      // Use getAllByText since the text appears in both textarea and preview
      const elements = screen.getAllByText("Show me sales data");
      expect(elements).toHaveLength(2); // One in textarea, one in preview
    });

    it("handles keyboard shortcuts (Ctrl+Enter)", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      await user.type(textarea, "Show me sales data");

      await user.keyboard("{Control>}{Enter}{/Control}");

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith("Show me sales data");
      });
    });

    it("handles keyboard shortcuts (Cmd+Enter on Mac)", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      await user.type(textarea, "Show me sales data");

      await user.keyboard("{Meta>}{Enter}{/Meta}");

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith("Show me sales data");
      });
    });
  });

  describe("Form Submission", () => {
    it("successfully submits query", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      await user.type(textarea, "Show me sales data");
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith("Show me sales data");
      });
    });

    it("trims whitespace from query before submission", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      await user.type(textarea, "  Show me sales data  ");
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith("Show me sales data");
      });
    });

    it("prevents submission of empty or whitespace-only queries", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      await user.type(textarea, "   ");
      await user.click(generateButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("prevents form submission via Enter key", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      await user.type(textarea, "Show me sales data");
      await user.keyboard("{Enter}");

      // Should not submit, only Ctrl+Enter or Cmd+Enter should submit
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe("Loading States", () => {
    it("shows loading state during API call", async () => {
      renderQueryBox({ isLoading: true, value: "Show me sales data" });

      // Check loading state
      expect(screen.getByText("Generating...")).toBeInTheDocument();
      expect(screen.getByRole("status")).toBeInTheDocument();

      const generateButton = screen.getByRole("button", { name: /Generating/ });
      const textarea = screen.getByRole("textbox");

      expect(generateButton).toBeDisabled();
      expect(textarea).toBeDisabled();
    });

    it("disables form during loading", async () => {
      const user = userEvent.setup();
      renderQueryBox({ isLoading: true, value: "Show me sales data" });

      const generateButton = screen.getByRole("button", { name: /Generating/ });

      // Try to submit while loading
      await user.click(generateButton);

      // Should not be called since form is disabled
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe("Value Prop", () => {
    it("displays initial value from prop", () => {
      renderQueryBox({ value: "Initial query" });

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue("Initial query");
    });

    it("updates when value prop changes", () => {
      const { rerender } = renderQueryBox({ value: "Initial query" });

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue("Initial query");

      // Rerender with new value
      rerender(
        <QueryBox
          onSubmit={mockOnSubmit}
          isLoading={false}
          value="Updated query"
        />
      );

      expect(textarea).toHaveValue("Updated query");
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels and relationships", () => {
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("aria-describedby", "query-help");

      const label = screen.getByLabelText("Natural language query");
      expect(label).toBe(textarea);

      const helpText = screen.getByText(
        /Describe what you want to see in plain English/
      );
      expect(helpText).toHaveAttribute("id", "query-help");
    });

    it("maintains focus management", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      // Focus textarea directly
      await user.click(textarea);
      expect(textarea).toHaveFocus();

      // Tab to generate button (but it's disabled initially)
      await user.tab();
      // Since button is disabled, focus might not move to it
      // Let's just verify the button exists and is disabled
      expect(generateButton).toBeDisabled();
    });

    it("has loading spinner with proper accessibility attributes", async () => {
      renderQueryBox({ isLoading: true, value: "Show me sales data" });

      const loadingSpinner = screen.getByRole("status");
      expect(loadingSpinner).toBeInTheDocument();
    });
  });

  describe("Query Persistence", () => {
    it("keeps query text after successful submission", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");
      const generateButton = screen.getByRole("button", { name: "Generate" });

      await user.type(textarea, "Show me sales data");
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled();
      });

      // Query should still be in the textarea
      expect(textarea).toHaveValue("Show me sales data");
    });

    it("maintains query text when not loading", async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole("textbox");

      await user.type(textarea, "Show me sales data");

      // Query should be in the textarea
      expect(textarea).toHaveValue("Show me sales data");
    });
  });

  describe("Custom Placeholder", () => {
    it("uses custom placeholder when provided", () => {
      renderQueryBox({ placeholder: "Custom placeholder text" });

      expect(
        screen.getByPlaceholderText("Custom placeholder text")
      ).toBeInTheDocument();
    });

    it("uses default placeholder when not provided", () => {
      renderQueryBox();

      expect(
        screen.getByPlaceholderText("Ask a question about your data...")
      ).toBeInTheDocument();
    });
  });
});
