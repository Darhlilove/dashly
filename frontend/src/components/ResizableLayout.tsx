import React, { useState, useRef, useCallback, useEffect } from "react";
import { LAYOUT_CONFIG, CSS_VARIABLES, Z_INDEX } from "../config/layout";
import { useBreakpoint } from "../hooks/useMediaQuery";
import { LayoutState, ResizeConstraints } from "../types/layout";

interface ResizableLayoutProps {
  chatContent: React.ReactNode;
  dashboardContent: React.ReactNode;
  initialChatWidth?: number;
  onResize?: (chatWidth: number, dashboardWidth: number) => void;
  minChatWidth?: number;
  maxChatWidth?: number;
  className?: string;
}

const ResizableLayout: React.FC<ResizableLayoutProps> = ({
  chatContent,
  dashboardContent,
  initialChatWidth,
  onResize,
  minChatWidth = LAYOUT_CONFIG.constraints.minChatWidth,
  maxChatWidth = LAYOUT_CONFIG.constraints.maxChatWidth,
  className = "",
}) => {
  const currentBreakpoint = useBreakpoint();
  const containerRef = useRef<HTMLDivElement>(null);
  const dragHandleRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Get default width based on current breakpoint
  const getDefaultChatWidth = useCallback(() => {
    switch (currentBreakpoint) {
      case "mobile":
        return LAYOUT_CONFIG.defaultSizes.mobile.chat;
      case "tablet":
        return LAYOUT_CONFIG.defaultSizes.tablet.chat;
      case "desktop":
      case "large-desktop":
      default:
        return LAYOUT_CONFIG.defaultSizes.desktop.chat;
    }
  }, [currentBreakpoint]);

  const [layoutState, setLayoutState] = useState<
    Pick<LayoutState, "chatPaneWidth" | "dashboardPaneWidth" | "isResizing"> & {
      nearSnap: boolean;
    }
  >(() => {
    const chatWidth = initialChatWidth ?? getDefaultChatWidth();
    return {
      chatPaneWidth: chatWidth,
      dashboardPaneWidth: 100 - chatWidth,
      isResizing: false,
      nearSnap: false,
    };
  });

  // Update layout when breakpoint changes
  useEffect(() => {
    if (!layoutState.isResizing) {
      const defaultChatWidth = getDefaultChatWidth();
      setLayoutState((prev) => ({
        ...prev,
        chatPaneWidth: defaultChatWidth,
        dashboardPaneWidth: 100 - defaultChatWidth,
      }));
    }
  }, [currentBreakpoint, getDefaultChatWidth, layoutState.isResizing]);

  // Set CSS custom properties for dynamic sizing
  useEffect(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      container.style.setProperty(
        CSS_VARIABLES.chatWidth,
        `${layoutState.chatPaneWidth}%`
      );
      container.style.setProperty(
        CSS_VARIABLES.dashboardWidth,
        `${layoutState.dashboardPaneWidth}%`
      );
    }
  }, [layoutState.chatPaneWidth, layoutState.dashboardPaneWidth]);

  // Notify parent of resize changes
  useEffect(() => {
    onResize?.(layoutState.chatPaneWidth, layoutState.dashboardPaneWidth);
  }, [layoutState.chatPaneWidth, layoutState.dashboardPaneWidth, onResize]);

  // Calculate new width percentage based on mouse position
  const calculateNewWidth = useCallback(
    (clientX: number): number => {
      if (!containerRef.current) return layoutState.chatPaneWidth;

      const containerRect = containerRef.current.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const relativeX = clientX - containerRect.left;
      let newChatWidth = (relativeX / containerWidth) * 100;

      // Apply constraints
      newChatWidth = Math.min(
        Math.max(newChatWidth, minChatWidth),
        maxChatWidth
      );

      // Snap to default functionality - if within 3% of default, snap to it
      const defaultWidth = getDefaultChatWidth();
      const snapThreshold = 3;
      const isNearSnap = Math.abs(newChatWidth - defaultWidth) <= snapThreshold;

      if (isNearSnap) {
        newChatWidth = defaultWidth;
      }

      return newChatWidth;
    },
    [layoutState.chatPaneWidth, minChatWidth, maxChatWidth, getDefaultChatWidth]
  );

  // Validate that content remains functional at current sizes
  const validateContentSizes = useCallback((chatWidth: number): boolean => {
    if (!containerRef.current) return true;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;

    // Calculate actual pixel widths
    const chatPixelWidth = (chatWidth / 100) * containerWidth;
    const dashboardPixelWidth = ((100 - chatWidth) / 100) * containerWidth;

    // Minimum pixel widths for functional content
    const minChatPixels = 200; // Minimum for chat input and messages
    const minDashboardPixels = 300; // Minimum for charts and tables

    return (
      chatPixelWidth >= minChatPixels &&
      dashboardPixelWidth >= minDashboardPixels
    );
  }, []);

  // Enhanced width calculation with content validation
  const calculateValidatedWidth = useCallback(
    (clientX: number): number => {
      const newWidth = calculateNewWidth(clientX);

      // If the new width would make content non-functional, constrain it
      if (!validateContentSizes(newWidth)) {
        // Find the closest valid width
        if (!containerRef.current) return layoutState.chatPaneWidth;

        const containerRect = containerRef.current.getBoundingClientRect();
        const containerWidth = containerRect.width;

        // Calculate minimum valid chat width based on pixel requirements
        const minValidChatWidth = Math.max(
          (200 / containerWidth) * 100, // 200px minimum
          minChatWidth
        );

        // Calculate maximum valid chat width based on dashboard requirements
        const maxValidChatWidth = Math.min(
          100 - (300 / containerWidth) * 100, // Leave 300px for dashboard
          maxChatWidth
        );

        return Math.min(
          Math.max(newWidth, minValidChatWidth),
          maxValidChatWidth
        );
      }

      return newWidth;
    },
    [
      calculateNewWidth,
      validateContentSizes,
      layoutState.chatPaneWidth,
      minChatWidth,
      maxChatWidth,
    ]
  );

  // Handle mouse down on drag handle
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDraggingRef.current = true;
      startXRef.current = e.clientX;
      startWidthRef.current = layoutState.chatPaneWidth;

      setLayoutState((prev) => ({ ...prev, isResizing: true }));

      // Add cursor style to body during drag
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [layoutState.chatPaneWidth]
  );

  // Handle mouse move during drag
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDraggingRef.current) return;

      e.preventDefault();
      const newChatWidth = calculateValidatedWidth(e.clientX);

      // Check if we're near snap threshold for visual feedback
      const defaultWidth = getDefaultChatWidth();
      const snapThreshold = 3;
      const isNearSnap = Math.abs(newChatWidth - defaultWidth) <= snapThreshold;

      setLayoutState((prev) => ({
        ...prev,
        chatPaneWidth: newChatWidth,
        dashboardPaneWidth: 100 - newChatWidth,
        nearSnap: isNearSnap,
      }));
    },
    [calculateValidatedWidth, getDefaultChatWidth]
  );

  // Handle mouse up to end drag
  const handleMouseUp = useCallback(() => {
    if (!isDraggingRef.current) return;

    isDraggingRef.current = false;
    setLayoutState((prev) => ({ ...prev, isResizing: false, nearSnap: false }));

    // Remove cursor styles from body
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  // Add global mouse event listeners for drag functionality
  useEffect(() => {
    if (layoutState.isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);

      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [layoutState.isResizing, handleMouseMove, handleMouseUp]);

  // Handle keyboard navigation for resize handle
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const step = 5; // 5% steps for keyboard navigation
      let newChatWidth = layoutState.chatPaneWidth;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          newChatWidth = Math.max(
            layoutState.chatPaneWidth - step,
            minChatWidth
          );
          break;
        case "ArrowRight":
          e.preventDefault();
          newChatWidth = Math.min(
            layoutState.chatPaneWidth + step,
            maxChatWidth
          );
          break;
        case "Home":
          e.preventDefault();
          newChatWidth = getDefaultChatWidth();
          break;
        case "End":
          e.preventDefault();
          newChatWidth = maxChatWidth;
          break;
        default:
          return;
      }

      // Validate the new width to ensure content remains functional
      if (validateContentSizes(newChatWidth)) {
        setLayoutState((prev) => ({
          ...prev,
          chatPaneWidth: newChatWidth,
          dashboardPaneWidth: 100 - newChatWidth,
        }));
      }
    },
    [
      layoutState.chatPaneWidth,
      minChatWidth,
      maxChatWidth,
      getDefaultChatWidth,
      validateContentSizes,
    ]
  );

  // Mobile layout - stack vertically or use different approach
  if (currentBreakpoint === "mobile") {
    return (
      <div
        ref={containerRef}
        className={`h-full flex flex-col ${className}`}
        data-testid="resizable-layout-mobile"
      >
        {/* Mobile layout will be handled differently - for now, stack vertically */}
        <div className="flex-1 border-b border-gray-200">{chatContent}</div>
        <div className="flex-1">{dashboardContent}</div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`h-full grid grid-cols-[var(--chat-pane-width)_auto_var(--dashboard-pane-width)] ${className}`}
      style={{
        [CSS_VARIABLES.chatWidth]: `${layoutState.chatPaneWidth}%`,
        [CSS_VARIABLES.dashboardWidth]: `${layoutState.dashboardPaneWidth}%`,
      }}
      data-testid="resizable-layout"
    >
      {/* Chat Pane */}
      <div
        className="overflow-hidden border-r border-gray-200"
        data-testid="chat-pane"
      >
        {chatContent}
      </div>

      {/* Drag Handle */}
      <div
        ref={dragHandleRef}
        className={`
          w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize transition-colors duration-150
          flex items-center justify-center relative group
          ${layoutState.isResizing ? "bg-blue-500" : ""}
          ${layoutState.nearSnap ? "bg-green-500" : ""}
        `}
        style={{ zIndex: Z_INDEX.resizeHandle }}
        data-testid="resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat and dashboard panes. Use arrow keys to adjust size, Home to reset, End to maximize."
        tabIndex={0}
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
      >
        {/* Visual indicator for drag handle */}
        <div className="absolute inset-y-0 left-0 w-full flex items-center justify-center">
          <div
            className={`
            w-0.5 h-8 transition-colors duration-150
            ${
              layoutState.nearSnap
                ? "bg-white"
                : "bg-gray-400 group-hover:bg-white"
            }
          `}
          />
        </div>

        {/* Expanded hover area for easier grabbing */}
        <div className="absolute inset-y-0 -left-2 -right-2 w-5" />
      </div>

      {/* Dashboard Pane */}
      <div className="overflow-hidden" data-testid="dashboard-pane">
        {dashboardContent}
      </div>
    </div>
  );
};

export default ResizableLayout;
