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

  it("handles mouse drag operations", () => {
    const mockOnResize = vi.fn();

    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        onResize={mockOnResize}
        initialChatWidth={30}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Clear initial call
    mockOnResize.mockClear();

    // Simulate mouse down to start drag
    fireEvent.mouseDown(resizeHandle, { clientX: 300 });

    // Simulate mouse move during drag
    fireEvent.mouseMove(document, { clientX: 400 });

    // Simulate mouse up to end drag
    fireEvent.mouseUp(document);

    // Should have called onResize during the drag operation
    expect(mockOnResize).toHaveBeenCalled();
  });

  it("provides visual feedback during drag", () => {
    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        initialChatWidth={30}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Start drag
    fireEvent.mouseDown(resizeHandle, { clientX: 300 });

    // During drag, handle should have active styling
    expect(resizeHandle).toHaveClass("dragging");

    // End drag
    fireEvent.mouseUp(document);

    // After drag, should return to normal styling
    expect(resizeHandle).not.toHaveClass("dragging");
  });

  it("snaps to default position when dragged near original", () => {
    const mockOnResize = vi.fn();

    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        onResize={mockOnResize}
        initialChatWidth={30}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Clear initial call
    mockOnResize.mockClear();

    // Simulate dragging near the default position (should snap)
    fireEvent.mouseDown(resizeHandle, { clientX: 300 });
    fireEvent.mouseMove(document, { clientX: 305 }); // Very close to original
    fireEvent.mouseUp(document);

    // Should snap back to default (16.67% ≈ 1/6)
    expect(mockOnResize).toHaveBeenCalledWith(
      expect.closeTo(16.67, 1),
      expect.closeTo(83.33, 1)
    );
  });

  it("prevents dragging beyond container bounds", () => {
    const mockOnResize = vi.fn();

    // Mock getBoundingClientRect to simulate container size
    const mockGetBoundingClientRect = vi.fn(() => ({
      left: 0,
      right: 1000,
      width: 1000,
      top: 0,
      bottom: 600,
      height: 600,
    }));

    Element.prototype.getBoundingClientRect = mockGetBoundingClientRect;

    render(
      <ResizableLayout
        chatContent={mockChatContent}
        dashboardContent={mockDashboardContent}
        onResize={mockOnResize}
        initialChatWidth={30}
        minChatWidth={10}
        maxChatWidth={50}
      />
    );

    const resizeHandle = screen.getByTestId("resize-handle");

    // Clear initial call
    mockOnResize.mockClear();

    // Try to drag beyond maximum
    fireEvent.mouseDown(resizeHandle, { clientX: 300 });
    fireEvent.mouseMove(document, { clientX: 600 }); // Way beyond max
    fireEvent.mouseUp(document);

    // Should be constrained to maximum
    const lastCall =
      mockOnResize.mock.calls[mockOnResize.mock.calls.length - 1];
    expect(lastCall[0]).toBeLessThanOrEqual(50);
  });
});
