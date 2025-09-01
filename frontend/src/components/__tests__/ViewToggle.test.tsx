import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ViewToggle from "../ViewToggle";
import { ViewType } from "../../types/layout";

describe("ViewToggle", () => {
  const defaultProps = {
    currentView: "data" as ViewType,
    onViewChange: vi.fn(),
    hasCharts: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders both dashboard and data buttons", () => {
    render(<ViewToggle {...defaultProps} />);

    expect(
      screen.getByRole("tab", { name: /switch to dashboard view/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /switch to data table view/i })
    ).toBeInTheDocument();
  });

  it("shows correct active state for current view", () => {
    render(<ViewToggle {...defaultProps} currentView="dashboard" />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    const dataButton = screen.getByRole("tab", {
      name: /switch to data table view/i,
    });

    expect(dashboardButton).toHaveAttribute("aria-selected", "true");
    expect(dataButton).toHaveAttribute("aria-selected", "false");
  });

  it("calls onViewChange when clicking buttons", () => {
    const onViewChange = vi.fn();
    render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    fireEvent.click(dashboardButton);

    expect(onViewChange).toHaveBeenCalledWith("dashboard");
  });

  it("disables dashboard button when no charts are available", () => {
    render(<ViewToggle {...defaultProps} hasCharts={false} />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    expect(dashboardButton).toBeDisabled();
    expect(dashboardButton).toHaveTextContent("(No charts)");
  });

  it("does not call onViewChange when dashboard button is clicked and no charts available", () => {
    const onViewChange = vi.fn();
    render(
      <ViewToggle
        {...defaultProps}
        hasCharts={false}
        onViewChange={onViewChange}
      />
    );

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    fireEvent.click(dashboardButton);

    expect(onViewChange).not.toHaveBeenCalled();
  });

  it("disables both buttons when disabled prop is true", () => {
    render(<ViewToggle {...defaultProps} disabled={true} />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    const dataButton = screen.getByRole("tab", {
      name: /switch to data table view/i,
    });

    expect(dashboardButton).toBeDisabled();
    expect(dataButton).toBeDisabled();
  });

  it("handles keyboard navigation with Enter key", () => {
    const onViewChange = vi.fn();
    render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    fireEvent.keyDown(dashboardButton, { key: "Enter" });

    expect(onViewChange).toHaveBeenCalledWith("dashboard");
  });

  it("handles keyboard navigation with Space key", () => {
    const onViewChange = vi.fn();
    render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    fireEvent.keyDown(dashboardButton, { key: " " });

    expect(onViewChange).toHaveBeenCalledWith("dashboard");
  });

  it("handles arrow key navigation", () => {
    const onViewChange = vi.fn();
    render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

    const dataButton = screen.getByRole("tab", {
      name: /switch to data table view/i,
    });
    fireEvent.keyDown(dataButton, { key: "ArrowLeft" });

    expect(onViewChange).toHaveBeenCalledWith("dashboard");
  });

  it("does not switch to dashboard with arrow keys when no charts available", () => {
    const onViewChange = vi.fn();
    render(
      <ViewToggle
        {...defaultProps}
        hasCharts={false}
        onViewChange={onViewChange}
      />
    );

    const dataButton = screen.getByRole("tab", {
      name: /switch to data table view/i,
    });
    fireEvent.keyDown(dataButton, { key: "ArrowLeft" });

    expect(onViewChange).not.toHaveBeenCalled();
  });

  it("applies custom className", () => {
    const { container } = render(
      <ViewToggle {...defaultProps} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("has proper ARIA attributes", () => {
    render(<ViewToggle {...defaultProps} />);

    const tablist = screen.getByRole("tablist");
    expect(tablist).toHaveAttribute(
      "aria-label",
      "View toggle between dashboard and data table"
    );

    const dashboardButton = screen.getByRole("tab", {
      name: /switch to dashboard view/i,
    });
    expect(dashboardButton).toHaveAttribute("aria-controls", "dashboard-panel");

    const dataButton = screen.getByRole("tab", {
      name: /switch to data table view/i,
    });
    expect(dataButton).toHaveAttribute("aria-controls", "data-panel");
  });
});
