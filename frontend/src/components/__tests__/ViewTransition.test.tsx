import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ViewTransition from "../ViewTransition";
import { ViewType } from "../../types/layout";

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe("ViewTransition", () => {
  const dashboardContent = (
    <div data-testid="dashboard-content">Dashboard View</div>
  );
  const dataContent = <div data-testid="data-content">Data View</div>;

  const defaultProps = {
    currentView: "data" as ViewType,
    dashboardContent,
    dataContent,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the current view content", () => {
    render(<ViewTransition {...defaultProps} />);

    expect(screen.getByTestId("data-content")).toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-content")).not.toBeInTheDocument();
  });

  it("shows loading state when isLoading is true", () => {
    render(<ViewTransition {...defaultProps} isLoading={true} />);

    expect(screen.getByText("Loading view...")).toBeInTheDocument();
    expect(screen.queryByTestId("data-content")).not.toBeInTheDocument();
  });

  it("renders dashboard content when currentView is dashboard", () => {
    render(<ViewTransition {...defaultProps} currentView="dashboard" />);

    expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    expect(screen.queryByTestId("data-content")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <ViewTransition {...defaultProps} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("has proper ARIA attributes", () => {
    render(<ViewTransition {...defaultProps} />);

    const tabpanel = screen.getByRole("tabpanel");
    expect(tabpanel).toHaveAttribute("id", "data-panel");
    expect(tabpanel).toHaveAttribute("aria-labelledby", "data-tab");
    expect(tabpanel).toHaveAttribute("tabIndex", "0");
  });

  it("respects reduced motion preference", () => {
    // Mock reduced motion preference
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(<ViewTransition {...defaultProps} currentView="dashboard" />);

    // With reduced motion, should render content immediately
    expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
  });

  it("sets minimum height to prevent layout shift", () => {
    const { container } = render(<ViewTransition {...defaultProps} />);

    expect(container.firstChild).toHaveStyle("min-height: 200px");
  });

  it("accepts custom animation duration prop", () => {
    // Test that the component accepts the prop without errors
    const { container } = render(
      <ViewTransition {...defaultProps} animationDuration={300} />
    );

    expect(container.firstChild).toBeInTheDocument();
  });
});
