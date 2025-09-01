import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ResizableLayout from "../ResizableLayout";

// Mock the useBreakpoint hook
vi.mock("../../hooks/useMediaQuery", () => ({
  useBreakpoint: () => "desktop",
}));

describe("ResizableLayout", () => {
  const mockChatContent = <div data-testid="chat-content">Chat Content</div>;
  const mockDashboardContent = (
    <div data-testid="dashboard-content">Dashboard Content</div>
  );

  it("renders with default layout structure", () => {
    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
      />
    );

    expect(screen.getByTestId("resizable-layout")).toBeInTheDocument();
    expect(screen.getByTestId("chat-pane")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-pane")).toBeInTheDocument();
    expect(screen.getByTestId("resize-handle")).toBeInTheDocument();
    expect(screen.getByTestId("chat-content")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
  });

  it("renders resize handle with proper accessibility attributes", () => {
    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");
    expect(resizeHandle).toHaveAttribute("role", "separator");
    expect(resizeHandle).toHaveAttribute("aria-orientation", "vertical");
    expect(resizeHandle).toHaveAttribute("tabIndex", "0");
    expect(resizeHandle).toHaveAttribute("aria-label");
  });

  it("calls onResize callback when provided", () => {
    const mockOnResize = vi.fn();

    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        onResize={mockOnResize}
      />
    );

    // Should be called once on initial render
    expect(mockOnResize).toHaveBeenCalledWith(
      expect.any(Number),
      expect.any(Number)
    );
  });

  it("handles keyboard navigation on resize handle", () => {
    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        initialChatWidth={30}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Test that the resize handle can receive focus and keyboard events
    resizeHandle.focus();
    expect(resizeHandle).toHaveFocus();

    // Test that keyboard events don't throw errors
    expect(() => {
      fireEvent.keyDown(resizeHandle, { key: "ArrowRight" });
      fireEvent.keyDown(resizeHandle, { key: "ArrowLeft" });
      fireEvent.keyDown(resizeHandle, { key: "Home" });
      fireEvent.keyDown(resizeHandle, { key: "End" });
    }).not.toThrow();
  });

  it("respects minimum and maximum width constraints", () => {
    const mockOnResize = vi.fn();

    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        onResize={mockOnResize}
        initialChatWidth={10}
        minChatWidth={10}
        maxChatWidth={50}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Clear initial call
    mockOnResize.mockClear();

    // Try to go below minimum
    fireEvent.keyDown(resizeHandle, { key: "ArrowLeft" });
    expect(mockOnResize).not.toHaveBeenCalled(); // Should not change below minimum

    // Try to go above maximum (start from near max)
    fireEvent.keyDown(resizeHandle, { key: "End" }); // Go to max
    mockOnResize.mockClear();
    fireEvent.keyDown(resizeHandle, { key: "ArrowRight" });
    expect(mockOnResize).not.toHaveBeenCalled(); // Should not change above maximum
  });

  it("applies custom CSS class", () => {
    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        className="custom-class"
      />
    );

    const layout = screen.getByTestId("resizable-layout");
    expect(layout).toHaveClass("custom-class");
  });
});
