import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import AutoHideSidebar from "../AutoHideSidebar";
import Sidebar from "../Sidebar";

// Mock the useMediaQuery hook
vi.mock("../../hooks/useMediaQuery", () => ({
  useMediaQuery: vi.fn(() => false), // Default to desktop
}));

describe("AutoHideSidebar Integration", () => {
  const mockOnVisibilityChange = vi.fn();
  const mockOnLoadDashboard = vi.fn();
  const mockOnNewDashboard = vi.fn();
  const mockOnToggle = vi.fn();

  const sidebarContent = (
    <Sidebar
      isCollapsed={false}
      onToggle={mockOnToggle}
      savedDashboards={[]}
      onLoadDashboard={mockOnLoadDashboard}
      onNewDashboard={mockOnNewDashboard}
    />
  );

  const mainContent = <div data-testid="main-content">Dashboard Content</div>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("integrates properly with Sidebar component", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    // Should render the sidebar with its content
    expect(screen.getByText("dashly")).toBeInTheDocument();
    expect(screen.getByText("New Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Recent Dashboards")).toBeInTheDocument();

    // Should render main content
    expect(screen.getByTestId("main-content")).toBeInTheDocument();
  });

  it("applies correct CSS classes for overlay positioning", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    // Find the sidebar container by looking for the fixed positioned element
    const sidebarElement = screen.getByText("dashly");
    let currentElement = sidebarElement.parentElement;

    // Walk up the DOM tree to find the fixed positioned container
    while (currentElement && !currentElement.classList.contains("fixed")) {
      currentElement = currentElement.parentElement;
    }

    // Should have fixed positioning and transform classes
    expect(currentElement).toHaveClass("fixed");
    expect(currentElement).toHaveClass("top-0");
    expect(currentElement).toHaveClass("left-0");
    expect(currentElement).toHaveClass("translate-x-0"); // visible
  });

  it("handles sidebar interactions correctly", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    // Click the New Dashboard button
    const newDashboardButton = screen.getByText("New Dashboard");
    fireEvent.click(newDashboardButton);

    // Should call the mock function
    expect(mockOnNewDashboard).toHaveBeenCalled();
  });
});
