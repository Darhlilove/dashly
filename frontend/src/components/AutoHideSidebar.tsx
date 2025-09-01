import { useState, useEffect, useRef, useCallback } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";

interface AutoHideSidebarProps {
  children: React.ReactNode; // Main content
  sidebarContent: React.ReactNode; // Sidebar content
  isVisible: boolean;
  onVisibilityChange: (visible: boolean) => void;
  triggerWidth?: number; // Default: 20px
  hideDelay?: number; // Default: 1000ms
}

export default function AutoHideSidebar({
  children,
  sidebarContent,
  isVisible,
  onVisibilityChange,
  triggerWidth = 20,
  hideDelay = 1000,
}: AutoHideSidebarProps) {
  const [isHovering, setIsHovering] = useState(false);
  const hideTimeoutRef = useRef<number | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const isMobile = useMediaQuery("(max-width: 768px)");

  // Clear timeout when component unmounts
  useEffect(() => {
    return () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
    };
  }, []);

  // Handle mouse position tracking for trigger zone
  useEffect(() => {
    if (isMobile) return; // Skip mouse tracking on mobile

    const handleMouseMove = (e: MouseEvent) => {
      const isInTriggerZone = e.clientX <= triggerWidth;

      if (isInTriggerZone && !isVisible) {
        // Clear any pending hide timeout
        if (hideTimeoutRef.current) {
          clearTimeout(hideTimeoutRef.current);
          hideTimeoutRef.current = null;
        }
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
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity duration-200"
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
              transform transition-transform duration-200 ease-in-out
              ${isVisible ? "translate-x-0" : "-translate-x-full"}
              ${isMobile ? "w-64" : "w-auto"}
            `}
            style={{
              zIndex: "var(--z-sidebar)",
              willChange: "transform",
            }}
            onMouseEnter={handleSidebarMouseEnter}
            onMouseLeave={handleSidebarMouseLeave}
            aria-hidden={!isVisible}
          >
            {sidebarContent}
          </div>
        )}
      </>

      {/* Trigger zone indicator */}
      {!isVisible && (
        <div
          className={`
            fixed top-0 left-0 h-full transition-opacity duration-200 pointer-events-none
            ${
              isMobile
                ? "opacity-10 bg-gray-400"
                : "opacity-0 hover:opacity-20 bg-gray-300"
            }
          `}
          style={{
            width: `${isMobile ? triggerWidth * 2 : triggerWidth}px`,
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
