import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AdvancedModeToggle from "../AdvancedModeToggle";

describe("AdvancedModeToggle", () => {
  it("renders with automatic mode by default", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    expect(screen.getByText("Automatic")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  });

  it("renders with advanced mode when enabled", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={true} onToggle={mockOnToggle} />
    );

    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  });

  it("calls onToggle when clicked", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    fireEvent.click(screen.getByRole("switch"));
    expect(mockOnToggle).toHaveBeenCalledWith(true);
  });

  it("calls onToggle when Enter key is pressed", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    fireEvent.keyDown(screen.getByRole("switch"), { key: "Enter" });
    expect(mockOnToggle).toHaveBeenCalledWith(true);
  });

  it("calls onToggle when Space key is pressed", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    fireEvent.keyDown(screen.getByRole("switch"), { key: " " });
    expect(mockOnToggle).toHaveBeenCalledWith(true);
  });

  it("does not call onToggle when disabled", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle
        isAdvancedMode={false}
        onToggle={mockOnToggle}
        disabled={true}
      />
    );

    fireEvent.click(screen.getByRole("switch"));
    expect(mockOnToggle).not.toHaveBeenCalled();
  });

  it("has proper accessibility attributes", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    const toggle = screen.getByRole("switch");
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toHaveAttribute(
      "aria-label",
      "Switch to advanced execution mode"
    );
    expect(toggle).toHaveAttribute(
      "aria-describedby",
      "execution-mode-description"
    );
  });

  it("renders without labels when showLabels is false", () => {
    const mockOnToggle = vi.fn();
    render(
      <AdvancedModeToggle
        isAdvancedMode={false}
        onToggle={mockOnToggle}
        showLabels={false}
      />
    );

    expect(screen.queryByText("Automatic")).not.toBeInTheDocument();
    expect(screen.queryByText("Advanced")).not.toBeInTheDocument();
    expect(screen.getByRole("switch")).toBeInTheDocument();
  });

  it("applies different sizes correctly", () => {
    const mockOnToggle = vi.fn();
    const { rerender } = render(
      <AdvancedModeToggle
        isAdvancedMode={false}
        onToggle={mockOnToggle}
        size="sm"
      />
    );

    let toggle = screen.getByRole("switch");
    expect(toggle).toHaveClass("w-8", "h-4");

    rerender(
      <AdvancedModeToggle
        isAdvancedMode={false}
        onToggle={mockOnToggle}
        size="lg"
      />
    );

    toggle = screen.getByRole("switch");
    expect(toggle).toHaveClass("w-12", "h-6");
  });

  it("shows correct aria-label based on current mode", () => {
    const mockOnToggle = vi.fn();
    const { rerender } = render(
      <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
    );

    expect(screen.getByRole("switch")).toHaveAttribute(
      "aria-label",
      "Switch to advanced execution mode"
    );

    rerender(
      <AdvancedModeToggle isAdvancedMode={true} onToggle={mockOnToggle} />
    );

    expect(screen.getByRole("switch")).toHaveAttribute(
      "aria-label",
      "Switch to automatic execution mode"
    );
  });

  describe("Advanced Mode Toggle Functionality", () => {
    it("shows tooltip on hover", async () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const toggle = screen.getByRole("switch");

      // Hover over the toggle
      fireEvent.mouseEnter(toggle);

      await waitFor(() => {
        expect(
          screen.getByText("Switch to manual SQL review")
        ).toBeInTheDocument();
      });

      // Hover away
      fireEvent.mouseLeave(toggle);

      await waitFor(() => {
        expect(
          screen.queryByText("Switch to manual SQL review")
        ).not.toBeInTheDocument();
      });
    });

    it("shows different tooltip text based on mode", async () => {
      const mockOnToggle = vi.fn();
      const { rerender } = render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      let toggle = screen.getByRole("switch");
      fireEvent.mouseEnter(toggle);

      await waitFor(() => {
        expect(
          screen.getByText("Switch to manual SQL review")
        ).toBeInTheDocument();
      });

      fireEvent.mouseLeave(toggle);

      rerender(
        <AdvancedModeToggle isAdvancedMode={true} onToggle={mockOnToggle} />
      );

      toggle = screen.getByRole("switch");
      fireEvent.mouseEnter(toggle);

      await waitFor(() => {
        expect(
          screen.getByText("Switch to automatic execution")
        ).toBeInTheDocument();
      });
    });

    it("does not show tooltip when disabled", async () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle
          isAdvancedMode={false}
          onToggle={mockOnToggle}
          disabled={true}
        />
      );

      const toggle = screen.getByRole("switch");
      fireEvent.mouseEnter(toggle);

      // Wait a bit to ensure tooltip doesn't appear
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(
        screen.queryByText("Switch to manual SQL review")
      ).not.toBeInTheDocument();
    });

    it("applies correct visual states for different modes", () => {
      const mockOnToggle = vi.fn();
      const { rerender } = render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      let toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("bg-gray-200");

      rerender(
        <AdvancedModeToggle isAdvancedMode={true} onToggle={mockOnToggle} />
      );

      toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("bg-blue-600");
    });

    it("applies disabled styling when disabled", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle
          isAdvancedMode={false}
          onToggle={mockOnToggle}
          disabled={true}
        />
      );

      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveClass("opacity-50", "cursor-not-allowed");
      expect(toggle).toBeDisabled();
    });

    it("handles focus states correctly", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const toggle = screen.getByRole("switch");

      // Focus the toggle
      toggle.focus();
      expect(toggle).toHaveFocus();

      // Should have focus ring classes
      expect(toggle).toHaveClass("focus:ring-2", "focus:ring-blue-500");
    });

    it("handles keyboard interactions correctly", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const toggle = screen.getByRole("switch");

      // Test that the component handles space and enter keys
      fireEvent.keyDown(toggle, { key: " " });
      expect(mockOnToggle).toHaveBeenCalledWith(true);

      vi.clearAllMocks();

      fireEvent.keyDown(toggle, { key: "Enter" });
      expect(mockOnToggle).toHaveBeenCalledWith(true);
    });

    it("ignores other key presses", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const toggle = screen.getByRole("switch");

      fireEvent.keyDown(toggle, { key: "Tab" });
      fireEvent.keyDown(toggle, { key: "Escape" });
      fireEvent.keyDown(toggle, { key: "a" });

      expect(mockOnToggle).not.toHaveBeenCalled();
    });

    it("applies custom className when provided", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle
          isAdvancedMode={false}
          onToggle={mockOnToggle}
          className="custom-class"
        />
      );

      // The className is applied to the outermost container
      const container = screen
        .getByRole("switch")
        .closest("div")?.parentElement;
      expect(container).toHaveClass("custom-class");
    });

    it("renders screen reader description", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const description = document.getElementById("execution-mode-description");
      expect(description).toBeInTheDocument();
      expect(description).toHaveClass("sr-only");
      expect(description).toHaveTextContent(
        "Automatic mode: SQL queries will be executed immediately after generation"
      );
    });

    it("updates screen reader description based on mode", () => {
      const mockOnToggle = vi.fn();
      const { rerender } = render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      let description = document.getElementById("execution-mode-description");
      expect(description).toHaveTextContent(
        "Automatic mode: SQL queries will be executed immediately after generation"
      );

      rerender(
        <AdvancedModeToggle isAdvancedMode={true} onToggle={mockOnToggle} />
      );

      description = document.getElementById("execution-mode-description");
      expect(description).toHaveTextContent(
        "Advanced mode: SQL queries will be shown for review before execution"
      );
    });

    it("handles rapid toggle clicks correctly", () => {
      const mockOnToggle = vi.fn();
      render(
        <AdvancedModeToggle isAdvancedMode={false} onToggle={mockOnToggle} />
      );

      const toggle = screen.getByRole("switch");

      // Rapid clicks
      fireEvent.click(toggle);
      fireEvent.click(toggle);
      fireEvent.click(toggle);

      expect(mockOnToggle).toHaveBeenCalledTimes(3);
      expect(mockOnToggle).toHaveBeenNthCalledWith(1, true);
      expect(mockOnToggle).toHaveBeenNthCalledWith(2, true);
      expect(mockOnToggle).toHaveBeenNthCalledWith(3, true);
    });
  });
});
