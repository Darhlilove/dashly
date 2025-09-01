import React, { useState, useEffect, useRef } from "react";
import { ViewType } from "../types/layout";

export interface ViewTransitionProps {
  currentView: ViewType;
  dashboardContent: React.ReactNode;
  dataContent: React.ReactNode;
  isLoading?: boolean;
  className?: string;
  animationDuration?: number; // in milliseconds
  transitionType?: "fade" | "slide";
}

const ViewTransition: React.FC<ViewTransitionProps> = ({
  currentView,
  dashboardContent,
  dataContent,
  isLoading = false,
  className = "",
  animationDuration = 200,
  transitionType = "fade",
}) => {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayView, setDisplayView] = useState(currentView);
  const [previousView, setPreviousView] = useState<ViewType | null>(null);
  const [animationPhase, setAnimationPhase] = useState<
    "idle" | "exiting" | "entering"
  >("idle");
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number>();

  // Check for reduced motion preference
  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;
  const effectiveAnimationDuration = prefersReducedMotion
    ? 0
    : animationDuration;

  useEffect(() => {
    if (currentView !== displayView) {
      setPreviousView(displayView);
      setIsTransitioning(true);

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // If reduced motion is preferred, switch immediately
      if (prefersReducedMotion) {
        setDisplayView(currentView);
        setIsTransitioning(false);
        setAnimationPhase("idle");
        return;
      }

      // Phase 1: Exit animation
      setAnimationPhase("exiting");

      // Phase 2: Switch content and enter animation
      timeoutRef.current = setTimeout(() => {
        setDisplayView(currentView);
        setAnimationPhase("entering");

        // Phase 3: Complete transition
        timeoutRef.current = setTimeout(() => {
          setIsTransitioning(false);
          setAnimationPhase("idle");
          setPreviousView(null);
        }, effectiveAnimationDuration);
      }, effectiveAnimationDuration / 2);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [
    currentView,
    displayView,
    effectiveAnimationDuration,
    prefersReducedMotion,
  ]);

  const getTransitionClasses = () => {
    if (prefersReducedMotion || !isTransitioning) {
      return "opacity-100 transform translate-x-0 scale-100";
    }

    const baseClasses = "w-full h-full";

    if (transitionType === "slide") {
      if (animationPhase === "exiting") {
        return `${baseClasses} view-slide-out`;
      } else if (animationPhase === "entering") {
        // Determine slide direction based on view change
        const slideDirection =
          currentView === "dashboard"
            ? "view-slide-in-left"
            : "view-slide-in-right";
        return `${baseClasses} ${slideDirection}`;
      }
    } else {
      // Fade transition
      if (animationPhase === "exiting") {
        return `${baseClasses} view-fade-out`;
      } else if (animationPhase === "entering") {
        return `${baseClasses} view-fade-in`;
      }
    }

    return baseClasses;
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <div className="loading-spinner-enhanced rounded-full h-8 w-8 border-2 border-gray-200 border-t-blue-600"></div>
            <p className="text-sm text-gray-600">Loading view...</p>
          </div>
        </div>
      );
    }

    return displayView === "dashboard" ? dashboardContent : dataContent;
  };

  const renderLoadingOverlay = () => {
    if (!isTransitioning && !isLoading) return null;

    return (
      <div
        className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center z-10 pointer-events-none"
        style={{
          opacity: animationPhase === "exiting" ? 1 : 0,
          transition: `opacity ${effectiveAnimationDuration / 2}ms ease-in-out`,
        }}
      >
        <div className="loading-dots-enhanced flex space-x-1">
          <div className="dot w-2 h-2 bg-blue-600 rounded-full"></div>
          <div className="dot w-2 h-2 bg-blue-600 rounded-full"></div>
          <div className="dot w-2 h-2 bg-blue-600 rounded-full"></div>
        </div>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full ${className}`}
      style={{
        minHeight: "200px", // Prevent layout shift during transitions
      }}
    >
      <div
        className={getTransitionClasses()}
        role="tabpanel"
        id={`${displayView}-panel`}
        aria-labelledby={`${displayView}-tab`}
        tabIndex={0}
        aria-live="polite"
        aria-atomic="true"
      >
        {renderContent()}
      </div>

      {/* Enhanced loading overlay */}
      {renderLoadingOverlay()}
    </div>
  );
};

export default ViewTransition;
