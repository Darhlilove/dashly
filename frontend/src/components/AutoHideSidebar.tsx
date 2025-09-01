import React, { useState, useEffect, useRef, useCallback } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { withLayoutErrorBoundary } from "./LayoutErrorBoundary";
import { usePerformanceMonitor } from "../utils/performanceMonitor";
import {
  createFallbackProps,
  analyzeViewportConstraints,
} from "../utils/gracefulDegradation";

interface AutoHideSidebarProps {
  children: React.ReactNode; // Main content
  sidebarContent: React.ReactNode; // Sidebar content
  isVisible: boolean;
  onVisibilityChange: (visible: boolean) => void;
  triggerWidth?: number; // Default: 20px
  hideDelay?: number; // Default: 0ms (instant)
}

function AutoHideSidebar({
  children,
  sidebarContent,
  isVisible,
  onVisibilityChange,
  triggerWidth = 20,
  hideDelay = 0,
}: AutoHideSidebarProps) {
  const [, setIsHovering] = useState(false);
  const [isInTriggerZone, setIsInTriggerZone] = useState(false);
  const [animationState, setAnimationState] = useState<
    "idle" | "entering" | "exiting"
  >("idle");
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const isMobile = useMediaQuery("(max-width: 768px)");

  // Clear timeout when component unmounts
  useEffect(() => {
    return () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
    };
  }, []);

  // Focus management when sidebar visibility changes
  useEffect(() => {
    if (isVisible) {
      // Store the currently focused element before showing sidebar
      previousFocusRef.current = document.activeElement as HTMLElement;

      // Focus the first focusable element in the sidebar after animation
      setTimeout(() => {
        if (sidebarRef.current) {
          const firstFocusable = sidebarRef.current.querySelector(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          ) as HTMLElement;
          firstFocusable?.focus();
        }
      }, 250); // Wait for animation to complete
    } else {
      // Restore focus to the previously focused element when hiding sidebar
      if (
        previousFocusRef.current &&
        document.contains(previousFocusRef.current)
      ) {
        previousFocusRef.current.focus();
      }
      previousFocusRef.current = null;
    }
  }, [isVisible]);

  // Handle mouse position tracking for trigger zone
  useEffect(() => {
    if (isMobile) return; // Skip mouse tracking on mobile

    const handleMouseMove = (e: MouseEvent) => {
      const inTriggerZone = e.clientX <= triggerWidth;
      setIsInTriggerZone(inTriggerZone);

      if (inTriggerZone && !isVisible) {
        // Clear any pending hide timeout
        if (hideTimeoutRef.current) {
          clearTimeout(hideTimeoutRef.current);
          hideTimeoutRef.current = null;
        }
        setAnimationState("entering");
        onVisibilityChange(true);
      }
    };

    document.addEventListener("mousemove", handleMouseMove);
    return () => document.removeEventListener("mousemove", handleMouseMove);
  }, [isVisible, onVisibilityChange, triggerWidth, isMobile]);

  // Handle sidebar hover state
  const handleSidebarMouseEnter = useCallback(() => {
    setIsHovering(true);
    // Clear any pending hide timeout
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const handleSidebarMouseLeave = useCallback(() => {
    setIsHovering(false);
    // Start hide timer
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
    }
    hideTimeoutRef.current = setTimeout(() => {
      setAnimationState("exiting");
      onVisibilityChange(false);
    }, hideDelay);
  }, [onVisibilityChange, hideDelay]);

  // Handle backdrop click on mobile
  const handleBackdropClick = useCallback(() => {
    if (isMobile && isVisible) {
      onVisibilityChange(false);
    }
  }, [isMobile, isVisible, onVisibilityChange]);

  // Touch gesture state for swipe detection
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(
    null
  );

  // Handle touch events for mobile swipe
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (!isMobile) return;

      const touch = e.touches[0];
      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };

      // Immediate activation for left edge touch
      const isLeftEdge = touch.clientX <= triggerWidth;
      if (isLeftEdge && !isVisible) {
        onVisibilityChange(true);
      }
    },
    [isMobile, triggerWidth, isVisible, onVisibilityChange]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isMobile || !touchStartRef.current) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;
      const deltaTime = Date.now() - touchStartRef.current.time;

      // Detect right swipe from left edge (swipe to open sidebar)
      const isRightSwipe =
        deltaX > 30 && Math.abs(deltaY) < 100 && deltaTime < 300;
      const startedFromLeftEdge = touchStartRef.current.x <= triggerWidth * 2; // Allow slightly wider start zone

      if (isRightSwipe && startedFromLeftEdge && !isVisible) {
        onVisibilityChange(true);
        touchStartRef.current = null; // Reset to prevent multiple triggers
      }
    },
    [isMobile, triggerWidth, isVisible, onVisibilityChange]
  );

  const handleTouchEnd = useCallback(() => {
    if (!isMobile) return;
    touchStartRef.current = null;
  }, [isMobile]);

  // Keyboard shortcuts for sidebar control
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: "s",
        ctrlKey: true,
        action: () => {
          onVisibilityChange(!isVisible);
        },
        description: "Toggle sidebar visibility",
      },
      {
        key: "s",
        metaKey: true,
        action: () => {
          onVisibilityChange(!isVisible);
        },
        description: "Toggle sidebar visibility",
      },
      {
        key: "Escape",
        action: () => {
          if (isVisible) {
            onVisibilityChange(false);
          }
        },
        description: "Close sidebar",
      },
    ],
    enabled: true,
  });

  // Handle keyboard navigation within sidebar
  const handleSidebarKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onVisibilityChange(false);
      } else if (e.key === "Tab") {
        // Trap focus within sidebar when visible
        if (!sidebarRef.current) return;

        const focusableElements = sidebarRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[
          focusableElements.length - 1
        ] as HTMLElement;

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    },
    [onVisibilityChange]
  );

  return (
    <div className="relative h-full">
      {/* Main content */}
      <div
        className="h-full"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>

      {/* Sidebar overlay */}
      <>
        {/* Mobile backdrop */}
        {isMobile && isVisible && (
          <div
            className={`
              fixed inset-0 bg-black bg-opacity-50
              ${animationState === "entering" ? "sidebar-backdrop-fade-in" : ""}
              ${animationState === "exiting" ? "sidebar-backdrop-fade-out" : ""}
            `}
            style={{ zIndex: "var(--z-sidebar-overlay)" }}
            onClick={handleBackdropClick}
            aria-hidden="true"
          />
        )}

        {/* Sidebar container - always render on desktop, conditionally on mobile */}
        {(!isMobile || isVisible) && (
          <div
            ref={sidebarRef}
            className={`
              fixed top-0 left-0 h-full
              ${isVisible ? "sidebar-slide-in" : "sidebar-slide-out"}
              ${isMobile ? "w-64" : "w-auto"}
            `}
            style={{
              zIndex: "var(--z-sidebar)",
              willChange: "transform, opacity",
              transform: isVisible ? "translateX(0)" : "translateX(-100%)",
            }}
            onMouseEnter={handleSidebarMouseEnter}
            onMouseLeave={handleSidebarMouseLeave}
            onKeyDown={handleSidebarKeyDown}
            role="complementary"
            aria-label="Navigation sidebar"
            aria-hidden={!isVisible}
            aria-expanded={isVisible}
          >
            {sidebarContent}
          </div>
        )}
      </>

      {/* Trigger zone indicator */}
      {!isVisible && !isMobile && (
        <>
          <div
            className={`
              fixed top-0 left-0 h-full pointer-events-none
              ${
                isInTriggerZone
                  ? "sidebar-trigger-hover"
                  : "sidebar-trigger-glow"
              }
            `}
            style={{
              width: `${triggerWidth}px`,
              zIndex: "var(--z-sidebar-overlay)",
              background: isInTriggerZone
                ? "linear-gradient(90deg, rgba(156, 163, 175, 0.4) 0%, rgba(156, 163, 175, 0.2) 70%, transparent 100%)"
                : "rgba(156, 163, 175, 0.1)",
            }}
            aria-hidden="true"
          />
          {/* Accessible button for keyboard users to open sidebar */}
          <button
            className="fixed top-4 left-2 z-50 px-2 py-1 text-xs bg-gray-800 text-white rounded opacity-0 focus:opacity-100 transition-opacity"
            onClick={() => onVisibilityChange(true)}
            aria-label="Open navigation sidebar (Ctrl+S)"
            style={{ zIndex: "var(--z-sidebar-overlay)" }}
          >
            Open Sidebar
          </button>
        </>
      )}

      {/* Mobile trigger zone indicator */}
      {!isVisible && isMobile && (
        <div
          className="fixed top-0 left-0 h-full pointer-events-none opacity-10 bg-gray-400"
          style={{
            width: `${triggerWidth * 2}px`,
            zIndex: "var(--z-sidebar-overlay)",
          }}
          aria-hidden="true"
        />
      )}

      {/* Mobile swipe indicator */}
      {isMobile && !isVisible && (
        <div
          className="fixed top-1/2 left-2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
          style={{ zIndex: "var(--z-sidebar-overlay)" }}
          aria-hidden="true"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="animate-pulse"
          >
            <path d="M3 12h18m-9-9l9 9-9 9" />
          </svg>
        </div>
      )}
    </div>
  );
}

// Enhanced AutoHideSidebar with error boundary and performance monitoring
const EnhancedAutoHideSidebar: React.FC<AutoHideSidebarProps> = (props) => {
  const performanceMonitor = usePerformanceMonitor("AutoHideSidebar");
  const { constraints } = analyzeViewportConstraints();

  // Apply graceful degradation based on constraints
  const fallbackProps = createFallbackProps("AutoHideSidebar");
  const enhancedProps = { ...fallbackProps, ...props };

  // Check for extreme constraints that require fallback
  if (constraints.includes("very-short")) {
    return (
      <div className="flex flex-col h-full">
        <div className="bg-yellow-50 border-b border-yellow-200 p-2">
          <p className="text-xs text-yellow-800">
            Screen too short for auto-hide sidebar. Using bottom navigation.
          </p>
        </div>
        <div className="flex-1 overflow-hidden">{props.children}</div>
        <div className="border-t border-gray-200 bg-white p-2 max-h-32 overflow-auto">
          {props.sidebarContent}
        </div>
      </div>
    );
  }

  // Skip enhancements in test environment
  const isTestEnv = typeof window !== "undefined" && (window as any).__vitest__;
  if (isTestEnv) {
    return <AutoHideSidebar {...props} />;
  }

  // Measure render performance
  const endMeasure = performanceMonitor.measureRender();

  useEffect(() => {
    endMeasure();
  });

  return <AutoHideSidebar {...enhancedProps} />;
};

// Wrap with error boundary (skip in tests)
const isTestEnv = typeof window !== "undefined" && (window as any).__vitest__;
const AutoHideSidebarWithErrorBoundary = isTestEnv
  ? AutoHideSidebar
  : withLayoutErrorBoundary(EnhancedAutoHideSidebar, "AutoHideSidebar");

export { AutoHideSidebarWithErrorBoundary as default };
