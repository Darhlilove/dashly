import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import AutoHideSidebar from "../AutoHideSidebar";
import { useMediaQuery } from "../../hooks/useMediaQuery";

// Mock the useMediaQuery hook
vi.mock("../../hooks/useMediaQuery", () => ({
  useMediaQuery: vi.fn(() => false), // Default to desktop
}));

describe("AutoHideSidebar", () => {
  const mockOnVisibilityChange = vi.fn();
  const sidebarContent = (
    <div data-testid="sidebar-content">Sidebar Content</div>
  );
  const mainContent = <div data-testid="main-content">Main Content</div>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("renders main content", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={false}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    expect(screen.getByTestId("main-content")).toBeInTheDocument();
  });

  it("shows sidebar when isVisible is true", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    expect(screen.getByTestId("sidebar-content")).toBeInTheDocument();
  });

  it("hides sidebar when isVisible is false on desktop", () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={false}
        onVisibilityChange={mockOnVisibilityChange}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    // On desktop with isVisible=false, sidebar should still be rendered but hidden
    const sidebarElement = screen.getByTestId("sidebar-content");
    const sidebarContainer = sidebarElement.parentElement;

    // The sidebar container should have the slide-out class and transform style
    expect(sidebarContainer).toHaveClass("sidebar-slide-out");
    expect(sidebarContainer).toHaveStyle("transform: translateX(-100%)");
  });

  it("calls onVisibilityChange when mouse enters trigger zone", async () => {
    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={false}
        onVisibilityChange={mockOnVisibilityChange}
        triggerWidth={20}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    // Simulate mouse move in trigger zone
    fireEvent.mouseMove(document, { clientX: 10 });

    await waitFor(() => {
      expect(mockOnVisibilityChange).toHaveBeenCalledWith(true);
    });
  });

  it("starts hide timer when mouse leaves sidebar", () => {
    vi.useFakeTimers();

    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
        hideDelay={1000}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    const sidebarContainer = screen
      .getByTestId("sidebar-content")
      .closest("div");

    // Mouse leave sidebar
    fireEvent.mouseLeave(sidebarContainer!);

    // Fast-forward time
    vi.advanceTimersByTime(1000);

    // Check that the callback was called
    expect(mockOnVisibilityChange).toHaveBeenCalledWith(false);

    vi.useRealTimers();
  });

  it("cancels hide timer when mouse re-enters sidebar", () => {
    vi.useFakeTimers();

    render(
      <AutoHideSidebar
        sidebarContent={sidebarContent}
        isVisible={true}
        onVisibilityChange={mockOnVisibilityChange}
        hideDelay={1000}
      >
        {mainContent}
      </AutoHideSidebar>
    );

    const sidebarContainer = screen
      .getByTestId("sidebar-content")
      .closest("div");

    // Mouse leave sidebar
    fireEvent.mouseLeave(sidebarContainer!);

    // Mouse re-enter before timeout
    vi.advanceTimersByTime(500);
    fireEvent.mouseEnter(sidebarContainer!);

    // Complete the original timeout period
    vi.advanceTimersByTime(500);

    // Should not have called onVisibilityChange(false)
    expect(mockOnVisibilityChange).not.toHaveBeenCalledWith(false);

    vi.useRealTimers();
  });

  describe("Mobile touch support", () => {
    beforeEach(() => {
      // Mock mobile viewport
      vi.mocked(useMediaQuery).mockReturnValue(true);
    });

    it("activates sidebar on touch at left edge", () => {
      render(
        <AutoHideSidebar
          sidebarContent={sidebarContent}
          isVisible={false}
          onVisibilityChange={mockOnVisibilityChange}
          triggerWidth={20}
        >
          {mainContent}
        </AutoHideSidebar>
      );

      const mainContentElement =
        screen.getByTestId("main-content").parentElement;

      // Touch at left edge
      fireEvent.touchStart(mainContentElement!, {
        touches: [{ clientX: 10, clientY: 100 }],
      });

      expect(mockOnVisibilityChange).toHaveBeenCalledWith(true);
    });

    it("activates sidebar on right swipe from left edge", () => {
      vi.useFakeTimers();
      const mockDateNow = vi.spyOn(Date, "now");
      mockDateNow.mockReturnValue(1000);

      render(
        <AutoHideSidebar
          sidebarContent={sidebarContent}
          isVisible={false}
          onVisibilityChange={mockOnVisibilityChange}
          triggerWidth={20}
        >
          {mainContent}
        </AutoHideSidebar>
      );

      const mainContentElement =
        screen.getByTestId("main-content").parentElement;

      // Start touch at left edge
      fireEvent.touchStart(mainContentElement!, {
        touches: [{ clientX: 15, clientY: 100 }],
      });

      // Simulate time passing
      mockDateNow.mockReturnValue(1200);

      // Move right (swipe gesture)
      fireEvent.touchMove(mainContentElement!, {
        touches: [{ clientX: 60, clientY: 110 }],
      });

      expect(mockOnVisibilityChange).toHaveBeenCalledWith(true);

      vi.useRealTimers();
      mockDateNow.mockRestore();
    });

    it("does not activate on vertical swipe", () => {
      vi.useFakeTimers();
      const mockDateNow = vi.spyOn(Date, "now");
      mockDateNow.mockReturnValue(1000);

      render(
        <AutoHideSidebar
          sidebarContent={sidebarContent}
          isVisible={false}
          onVisibilityChange={mockOnVisibilityChange}
          triggerWidth={20}
        >
          {mainContent}
        </AutoHideSidebar>
      );

      const mainContentElement =
        screen.getByTestId("main-content").parentElement;

      // Start touch just outside immediate trigger zone but within swipe zone
      fireEvent.touchStart(mainContentElement!, {
        touches: [{ clientX: 35, clientY: 100 }],
      });

      // Clear any calls from touchStart
      mockOnVisibilityChange.mockClear();

      // Simulate time passing
      mockDateNow.mockReturnValue(1200);

      // Move vertically (not a right swipe)
      fireEvent.touchMove(mainContentElement!, {
        touches: [{ clientX: 40, clientY: 200 }],
      });

      // Should not activate sidebar for vertical movement
      expect(mockOnVisibilityChange).not.toHaveBeenCalledWith(true);

      vi.useRealTimers();
      mockDateNow.mockRestore();
    });

    it("closes sidebar on backdrop click", () => {
      render(
        <AutoHideSidebar
          sidebarContent={sidebarContent}
          isVisible={true}
          onVisibilityChange={mockOnVisibilityChange}
        >
          {mainContent}
        </AutoHideSidebar>
      );

      // Find and click the backdrop
      const backdrop = document.querySelector(".bg-black.bg-opacity-50");
      expect(backdrop).toBeInTheDocument();

      fireEvent.click(backdrop!);

      expect(mockOnVisibilityChange).toHaveBeenCalledWith(false);
    });
  });
});
