import React, { useState, useRef, useCallback, useEffect } from "react";
import { LAYOUT_CONFIG, CSS_VARIABLES, Z_INDEX } from "../config/layout";
import { useBreakpoint } from "../hooks/useMediaQuery";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { LayoutState } from "../types/layout";
import { withLayoutErrorBoundary } from "./LayoutErrorBoundary";
import { usePerformanceMonitor } from "../utils/performanceMonitor";
import {
  createFallbackProps,
  analyzeViewportConstraints,
} from "../utils/gracefulDegradation";

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
      isSnapping: boolean;
      atMinConstraint: boolean;
      atMaxConstraint: boolean;
    }
  >(() => {
    const chatWidth = initialChatWidth ?? getDefaultChatWidth();
    return {
      chatPaneWidth: chatWidth,
      dashboardPaneWidth: 100 - chatWidth,
      isResizing: false,
      nearSnap: false,
      isSnapping: false,
      atMinConstraint: false,
      atMaxConstraint: false,
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
        "--chat-pane-width",
        `${layoutState.chatPaneWidth}%`
      );
      container.style.setProperty(
        "--dashboard-pane-width",
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
    (
      clientX: number
    ): {
      width: number;
      nearSnap: boolean;
      atMinConstraint: boolean;
      atMaxConstraint: boolean;
    } => {
      if (!containerRef.current)
        return {
          width: layoutState.chatPaneWidth,
          nearSnap: false,
          atMinConstraint: false,
          atMaxConstraint: false,
        };

      const containerRect = containerRef.current.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const relativeX = clientX - containerRect.left;
      let newChatWidth = (relativeX / containerWidth) * 100;

      // Check constraint boundaries before applying them
      const atMinConstraint = newChatWidth <= minChatWidth;
      const atMaxConstraint = newChatWidth >= maxChatWidth;

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

      return {
        width: newChatWidth,
        nearSnap: isNearSnap,
        atMinConstraint,
        atMaxConstraint,
      };
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
    (
      clientX: number
    ): {
      width: number;
      nearSnap: boolean;
      atMinConstraint: boolean;
      atMaxConstraint: boolean;
    } => {
      const result = calculateNewWidth(clientX);

      // If the new width would make content non-functional, constrain it
      if (!validateContentSizes(result.width)) {
        // Find the closest valid width
        if (!containerRef.current)
          return {
            width: layoutState.chatPaneWidth,
            nearSnap: false,
            atMinConstraint: false,
            atMaxConstraint: false,
          };

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

        const constrainedWidth = Math.min(
          Math.max(result.width, minValidChatWidth),
          maxValidChatWidth
        );

        return {
          width: constrainedWidth,
          nearSnap: result.nearSnap,
          atMinConstraint: constrainedWidth <= minValidChatWidth,
          atMaxConstraint: constrainedWidth >= maxValidChatWidth,
        };
      }

      return result;
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
      document.body.classList.add("resize-cursor-active");
    },
    [layoutState.chatPaneWidth]
  );

  // Handle mouse move during drag
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDraggingRef.current) return;

      e.preventDefault();
      const result = calculateValidatedWidth(e.clientX);

      setLayoutState((prev) => ({
        ...prev,
        chatPaneWidth: result.width,
        dashboardPaneWidth: 100 - result.width,
        nearSnap: result.nearSnap,
        atMinConstraint: result.atMinConstraint,
        atMaxConstraint: result.atMaxConstraint,
      }));
    },
    [calculateValidatedWidth]
  );

  // Handle mouse up to end drag
  const handleMouseUp = useCallback(() => {
    if (!isDraggingRef.current) return;

    isDraggingRef.current = false;

    // If we were near snap when releasing, trigger snap animation
    if (layoutState.nearSnap) {
      setLayoutState((prev) => ({
        ...prev,
        isResizing: false,
        nearSnap: false,
        isSnapping: true,
        atMinConstraint: false,
        atMaxConstraint: false,
      }));

      // Clear snapping state after animation
      setTimeout(() => {
        setLayoutState((prev) => ({ ...prev, isSnapping: false }));
      }, 300);
    } else {
      setLayoutState((prev) => ({
        ...prev,
        isResizing: false,
        nearSnap: false,
        atMinConstraint: false,
        atMaxConstraint: false,
      }));
    }

    // Remove cursor styles from body
    document.body.classList.remove("resize-cursor-active");
  }, [layoutState.nearSnap]);

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

  // Global keyboard shortcuts for layout operations
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: "r",
        ctrlKey: true,
        action: () => {
          const defaultWidth = getDefaultChatWidth();
          if (validateContentSizes(defaultWidth)) {
            setLayoutState((prev) => ({
              ...prev,
              chatPaneWidth: defaultWidth,
              dashboardPaneWidth: 100 - defaultWidth,
            }));
          }
        },
        description: "Reset layout to default proportions",
      },
      {
        key: "r",
        metaKey: true,
        action: () => {
          const defaultWidth = getDefaultChatWidth();
          if (validateContentSizes(defaultWidth)) {
            setLayoutState((prev) => ({
              ...prev,
              chatPaneWidth: defaultWidth,
              dashboardPaneWidth: 100 - defaultWidth,
            }));
          }
        },
        description: "Reset layout to default proportions",
      },
      {
        key: "m",
        ctrlKey: true,
        action: () => {
          if (validateContentSizes(minChatWidth)) {
            setLayoutState((prev) => ({
              ...prev,
              chatPaneWidth: minChatWidth,
              dashboardPaneWidth: 100 - minChatWidth,
            }));
          }
        },
        description: "Maximize dashboard pane",
      },
      {
        key: "m",
        metaKey: true,
        action: () => {
          if (validateContentSizes(minChatWidth)) {
            setLayoutState((prev) => ({
              ...prev,
              chatPaneWidth: minChatWidth,
              dashboardPaneWidth: 100 - minChatWidth,
            }));
          }
        },
        description: "Maximize dashboard pane",
      },
    ],
    enabled: currentBreakpoint !== "mobile", // Disable on mobile
  });

  // Handle keyboard navigation for resize handle
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const step = 5; // 5% steps for keyboard navigation
      const largeStep = 10; // Larger steps for Shift+Arrow
      let newChatWidth = layoutState.chatPaneWidth;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          const leftStep = e.shiftKey ? largeStep : step;
          newChatWidth = Math.max(
            layoutState.chatPaneWidth - leftStep,
            minChatWidth
          );
          break;
        case "ArrowRight":
          e.preventDefault();
          const rightStep = e.shiftKey ? largeStep : step;
          newChatWidth = Math.min(
            layoutState.chatPaneWidth + rightStep,
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
        case "PageUp":
          e.preventDefault();
          newChatWidth = minChatWidth;
          break;
        case "PageDown":
          e.preventDefault();
          newChatWidth = maxChatWidth;
          break;
        case "r":
        case "R":
          // Reset to default with 'r' key
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            newChatWidth = getDefaultChatWidth();
          } else {
            return;
          }
          break;
        case "m":
        case "M":
          // Maximize dashboard pane with Ctrl/Cmd+M
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            newChatWidth = minChatWidth;
          } else {
            return;
          }
          break;
        case "c":
        case "C":
          // Maximize chat pane with Ctrl/Cmd+C
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            newChatWidth = maxChatWidth;
          } else {
            return;
          }
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
      style={
        {
          "--chat-pane-width": `${layoutState.chatPaneWidth}%`,
          "--dashboard-pane-width": `${layoutState.dashboardPaneWidth}%`,
        } as React.CSSProperties
      }
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
          w-1 bg-gray-200 resize-handle
          flex items-center justify-center relative group
          ${layoutState.isResizing ? "dragging" : ""}
          ${layoutState.nearSnap ? "near-snap" : ""}
          ${layoutState.isSnapping ? "snapping" : ""}
        `}
        style={{ zIndex: Z_INDEX.resizeHandle }}
        data-testid="resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat and dashboard panes. Arrow keys to adjust (Shift for larger steps), Home to reset, End/PageDown to maximize dashboard, PageUp to minimize chat, Ctrl+R to reset, Ctrl+M to maximize dashboard, Ctrl+C to maximize chat."
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
              layoutState.nearSnap || layoutState.isSnapping
                ? "bg-white"
                : "bg-gray-400 group-hover:bg-white"
            }
          `}
          />
        </div>

        {/* Constraint indicators */}
        {layoutState.atMinConstraint && (
          <div className="resize-constraint-indicator left active" />
        )}
        {layoutState.atMaxConstraint && (
          <div className="resize-constraint-indicator right active" />
        )}

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

// Enhanced ResizableLayout with error boundary and performance monitoring
const EnhancedResizableLayout: React.FC<ResizableLayoutProps> = (props) => {
  // Skip enhancements in test environment
  if (process.env.NODE_ENV === "test") {
    return <ResizableLayout {...props} />;
  }

  const performanceMonitor = usePerformanceMonitor("ResizableLayout");
  const { viewport, constraints } = analyzeViewportConstraints();

  // Apply graceful degradation based on constraints
  const fallbackProps = createFallbackProps("ResizableLayout");
  const enhancedProps = { ...fallbackProps, ...props };

  // Check for extreme constraints that require fallback
  if (constraints.includes("extremely-narrow")) {
    return (
      <div className="flex flex-col h-full">
        <div className="bg-yellow-50 border-b border-yellow-200 p-2">
          <p className="text-xs text-yellow-800">
            Screen too narrow for resizable layout. Using stacked layout.
          </p>
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="h-1/3 border-b border-gray-200 overflow-auto">
            {props.chatContent}
          </div>
          <div className="h-2/3 overflow-auto">{props.dashboardContent}</div>
        </div>
      </div>
    );
  }

  // Measure render performance
  const endMeasure = performanceMonitor.measureRender();

  useEffect(() => {
    endMeasure();
  });

  return <ResizableLayout {...enhancedProps} />;
};

// Wrap with error boundary (skip in tests)
const ResizableLayoutWithErrorBoundary =
  process.env.NODE_ENV === "test"
    ? ResizableLayout
    : withLayoutErrorBoundary(EnhancedResizableLayout, "ResizableLayout");

export default ResizableLayoutWithErrorBoundary;
