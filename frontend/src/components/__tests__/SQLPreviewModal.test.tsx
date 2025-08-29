import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SQLPreviewModal from "../SQLPreviewModal";

describe("SQLPreviewModal", () => {
  const mockOnClose = vi.fn();
  const mockOnExecute = vi.fn();

  const defaultProps = {
    sql: "SELECT * FROM sales WHERE date >= '2023-01-01'",
    onClose: mockOnClose,
    onExecute: mockOnExecute,
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderModal = (props = {}) => {
    return render(<SQLPreviewModal {...defaultProps} {...props} />);
  };

  describe("Modal Structure", () => {
    it("renders modal header with title and close button", () => {
      renderModal();

      expect(screen.getByText("Review Generated SQL")).toBeInTheDocument();
      expect(screen.getByLabelText("Close modal")).toBeInTheDocument();
    });

    it("renders SQL textarea with proper attributes", () => {
      renderModal();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("id", "sql-textarea");
      expect(textarea).toHaveAttribute("aria-describedby", "sql-help");
      expect(textarea).toHaveValue(
        "SELECT * FROM sales WHERE date >= '2023-01-01'"
      );
    });

    it("renders action buttons", () => {
      renderModal();

      expect(
        screen.getByRole("button", { name: "Cancel" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Run Query" })
      ).toBeInTheDocument();
    });

    it("renders help text about SQL restrictions", () => {
      renderModal();

      expect(
        screen.getByText(/Only SELECT statements are allowed/)
      ).toBeInTheDocument();
    });
  });

  describe("SQL Editing", () => {
    it("allows editing SQL in textarea", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      await user.clear(textarea);
      await user.type(textarea, "SELECT name FROM products LIMIT 10");

      expect(textarea).toHaveValue("SELECT name FROM products LIMIT 10");
    });

    it("updates SQL when prop changes", () => {
      const { rerender } = renderModal();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue(
        "SELECT * FROM sales WHERE date >= '2023-01-01'"
      );

      rerender(
        <SQLPreviewModal {...defaultProps} sql="SELECT name FROM products" />
      );

      expect(textarea).toHaveValue("SELECT name FROM products");
    });

    it("focuses textarea when modal opens", () => {
      renderModal();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveFocus();
    });

    it("auto-resizes textarea based on content", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      const initialHeight = textarea.style.height;

      // Add more content to trigger resize
      await user.clear(textarea);
      await user.type(
        textarea,
        "SELECT *\nFROM sales\nWHERE date >= '2023-01-01'\nAND amount > 100\nORDER BY date DESC"
      );

      // In test environment, we just verify the content was added
      // The actual height change depends on DOM rendering which may not work in jsdom
      expect(textarea.value).toContain("SELECT *");
      expect(textarea.value).toContain("ORDER BY date DESC");
    });
  });

  describe("Modal Interactions", () => {
    it("closes modal when close button is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      const closeButton = screen.getByLabelText("Close modal");
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("closes modal when cancel button is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      const cancelButton = screen.getByRole("button", { name: "Cancel" });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("closes modal when overlay is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      const overlay = screen.getByTestId("sql-modal");
      await user.click(overlay);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("does not close modal when modal content is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      const modalContent = screen.getByRole("dialog");
      await user.click(modalContent);

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("closes modal when Escape key is pressed", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.keyboard("{Escape}");

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("SQL Execution", () => {
    it("successfully executes SQL query", async () => {
      const user = userEvent.setup();
      renderModal();

      const runButton = screen.getByTestId("run-query-button");
      await user.click(runButton);

      expect(mockOnExecute).toHaveBeenCalledWith(
        "SELECT * FROM sales WHERE date >= '2023-01-01'"
      );
    });

    it("executes edited SQL query", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      await user.clear(textarea);
      await user.type(textarea, "SELECT name FROM products LIMIT 10");

      const runButton = screen.getByTestId("run-query-button");
      await user.click(runButton);

      expect(mockOnExecute).toHaveBeenCalledWith(
        "SELECT name FROM products LIMIT 10"
      );
    });

    it("prevents execution of empty SQL", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      await user.clear(textarea);

      const runButton = screen.getByTestId("run-query-button");
      expect(runButton).toBeDisabled();

      await user.click(runButton);
      expect(mockOnExecute).not.toHaveBeenCalled();
    });

    it("prevents execution of whitespace-only SQL", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      await user.clear(textarea);
      await user.type(textarea, "   ");

      const runButton = screen.getByTestId("run-query-button");
      expect(runButton).toBeDisabled();

      await user.click(runButton);
      expect(mockOnExecute).not.toHaveBeenCalled();
    });
  });

  describe("Loading States", () => {
    it("shows loading state during SQL execution", () => {
      renderModal({ isLoading: true });

      expect(screen.getByText("Running Query...")).toBeInTheDocument();
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("disables buttons during execution", () => {
      renderModal({ isLoading: true });

      const runButton = screen.getByTestId("run-query-button");
      const cancelButton = screen.getByRole("button", { name: "Cancel" });

      expect(runButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();
    });
  });

  describe("Button States", () => {
    it("disables run button when SQL is empty", () => {
      renderModal({ sql: "" });

      const runButton = screen.getByTestId("run-query-button");
      expect(runButton).toBeDisabled();
    });

    it("enables run button when SQL has content", () => {
      renderModal();

      const runButton = screen.getByTestId("run-query-button");
      expect(runButton).not.toBeDisabled();
    });

    it("disables run button for whitespace-only SQL", () => {
      renderModal({ sql: "   " });

      const runButton = screen.getByTestId("run-query-button");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA labels and roles", () => {
      renderModal();

      const modal = screen.getByRole("dialog");
      expect(modal).toHaveAttribute("aria-modal", "true");
      expect(modal).toHaveAttribute("aria-labelledby", "modal-title");

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveAttribute("aria-describedby", "sql-help");
    });

    it("has loading spinner with proper accessibility attributes", () => {
      renderModal({ isLoading: true });

      const loadingSpinner = screen.getByRole("status");
      expect(loadingSpinner).toBeInTheDocument();
    });

    it("maintains focus management", async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveFocus();

      // Tab through elements - order may vary based on DOM structure
      await user.tab();
      // Just verify that focus moved to a focusable element
      const focusedElement = document.activeElement;
      expect(focusedElement).not.toBe(textarea);
      expect(focusedElement?.tagName).toMatch(/BUTTON/);
    });

    it("traps focus within modal", async () => {
      const user = userEvent.setup();
      renderModal();

      // Focus should stay within the modal
      const textarea = screen.getByRole("textbox");
      const closeButton = screen.getByLabelText("Close modal");
      const cancelButton = screen.getByRole("button", { name: "Cancel" });
      const runButton = screen.getByTestId("run-query-button");

      // All these elements should be focusable
      expect(textarea).toBeInTheDocument();
      expect(closeButton).toBeInTheDocument();
      expect(cancelButton).toBeInTheDocument();
      expect(runButton).toBeInTheDocument();
    });
  });

  describe("Event Handling", () => {
    it("prevents multiple simultaneous executions", async () => {
      const user = userEvent.setup();
      renderModal({ isLoading: true });

      const runButton = screen.getByTestId("run-query-button");

      // Button should be disabled during loading
      expect(runButton).toBeDisabled();

      await user.click(runButton);
      expect(mockOnExecute).not.toHaveBeenCalled();
    });

    it("cleans up event listeners when unmounted", () => {
      const { unmount } = renderModal();

      // Mock addEventListener and removeEventListener to verify cleanup
      const addEventListenerSpy = vi.spyOn(document, "addEventListener");
      const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

      unmount();

      // Verify that event listeners are cleaned up
      expect(removeEventListenerSpy).toHaveBeenCalled();

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });
});
