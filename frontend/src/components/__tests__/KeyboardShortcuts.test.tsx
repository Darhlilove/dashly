import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ResizableLayout from "../ResizableLayout";
import ViewToggle from "../ViewToggle";
import AutoHideSidebar from "../AutoHideSidebar";

// Mock the hooks
vi.mock("../hooks/useMediaQuery", () => ({
  useBreakpoint: () => "desktop",
  useMediaQuery: () => false,
}));

describe("Keyboard Shortcuts", () => {
  describe("ResizableLayout", () => {
    it("handles keyboard shortcuts for layout operations", () => {
      const onResize = vi.fn();
      render(
        <ResizableLayout
          chatContent={<div>Chat</div>}
          dashboardContent={<div>Dashboard</div>}
          onResize={onResize}
        />
      );

      const resizeHandle = screen.getByTestId("resize-handle");
      resizeHandle.focus();

      // Test arrow key navigation
      fireEvent.keyDown(resizeHandle, { key: "ArrowRight" });
      expect(onResize).toHaveBeenCalled();

      // Test reset shortcut
      fireEvent.keyDown(resizeHandle, { key: "Home" });
      expect(onResize).toHaveBeenCalled();

      // Test maximize shortcuts
      fireEvent.keyDown(resizeHandle, { key: "End" });
      expect(onResize).toHaveBeenCalled();
    });

    it("handles global keyboard shortcuts", () => {
      const onResize = vi.fn();
      render(
        <ResizableLayout
          chatContent={<div>Chat</div>}
          dashboardContent={<div>Dashboard</div>}
          onResize={onResize}
        />
      );

      // Test global reset shortcut
      fireEvent.keyDown(document, { key: "r", ctrlKey: true });
      expect(onResize).toHaveBeenCalled();

      // Test global maximize shortcut
      fireEvent.keyDown(document, { key: "m", ctrlKey: true });
      expect(onResize).toHaveBeenCalled();
    });

    it("includes proper ARIA labels with keyboard instructions", () => {
      render(
        <ResizableLayout
          chatContent={<div>Chat</div>}
          dashboardContent={<div>Dashboard</div>}
        />
      );

      const resizeHandle = screen.getByTestId("resize-handle");
      expect(resizeHandle).toHaveAttribute("aria-label");
      expect(resizeHandle.getAttribute("aria-label")).toContain("Arrow keys");
      expect(resizeHandle.getAttribute("aria-label")).toContain("Ctrl+R");
    });
  });

  describe("ViewToggle", () => {
    const defaultProps = {
      currentView: "data" as const,
      onViewChange: vi.fn(),
      hasCharts: true,
    };

    it("handles keyboard navigation between tabs", () => {
      const onViewChange = vi.fn();
      render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

      const dashboardButton = screen.getByRole("tab", { name: /dashboard/i });
      dashboardButton.focus();

      // Test arrow key navigation
      fireEvent.keyDown(dashboardButton, { key: "ArrowRight" });
      expect(onViewChange).toHaveBeenCalledWith("data");
    });

    it("handles global keyboard shortcuts for view switching", () => {
      const onViewChange = vi.fn();
      render(<ViewToggle {...defaultProps} onViewChange={onViewChange} />);

      // Test global shortcuts
      fireEvent.keyDown(document, { key: "1", ctrlKey: true });
      expect(onViewChange).toHaveBeenCalledWith("dashboard");

      fireEvent.keyDown(document, { key: "2", ctrlKey: true });
      expect(onViewChange).toHaveBeenCalledWith("data");
    });

    it("includes keyboard shortcut information in ARIA labels", () => {
      render(<ViewToggle {...defaultProps} />);

      const dashboardButton = screen.getByRole("tab", { name: /dashboard/i });
      const dataButton = screen.getByRole("tab", { name: /data/i });

      expect(dashboardButton.getAttribute("aria-label")).toContain("Ctrl+1");
      expect(dataButton.getAttribute("aria-label")).toContain("Ctrl+2");
    });
  });

  describe("AutoHideSidebar", () => {
    const defaultProps = {
      children: <div>Main content</div>,
      sidebarContent: <div>Sidebar content</div>,
      isVisible: false,
      onVisibilityChange: vi.fn(),
    };

    it("handles keyboard shortcuts for sidebar control", () => {
      const onVisibilityChange = vi.fn();
      render(
        <AutoHideSidebar
          {...defaultProps}
          onVisibilityChange={onVisibilityChange}
        />
      );

      // Test sidebar toggle shortcut
      fireEvent.keyDown(document, { key: "s", ctrlKey: true });
      expect(onVisibilityChange).toHaveBeenCalledWith(true);
    });

    it("handles escape key to close visible sidebar", () => {
      const onVisibilityChange = vi.fn();
      render(
        <AutoHideSidebar
          {...defaultProps}
          isVisible={true}
          onVisibilityChange={onVisibilityChange}
        />
      );

      // Test escape to close when sidebar is visible
      fireEvent.keyDown(document, { key: "Escape" });
      expect(onVisibilityChange).toHaveBeenCalledWith(false);
    });

    it("provides accessible button for keyboard users", () => {
      render(<AutoHideSidebar {...defaultProps} />);

      const openButton = screen.getByRole("button", { name: /open.*sidebar/i });
      expect(openButton).toBeInTheDocument();
      expect(openButton.getAttribute("aria-label")).toContain("Ctrl+S");
    });

    it("includes proper ARIA attributes on sidebar", () => {
      render(<AutoHideSidebar {...defaultProps} isVisible={true} />);

      const sidebar = screen.getByRole("complementary");
      expect(sidebar).toHaveAttribute("aria-label", "Navigation sidebar");
      expect(sidebar).toHaveAttribute("aria-expanded", "true");
    });
  });
});
