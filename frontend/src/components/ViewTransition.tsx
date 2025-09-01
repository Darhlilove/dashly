import React, { useState, useEffect, useRef } from "react";
import { ViewType } from "../types/layout";

export interface ViewTransitionProps {
  currentView: ViewType;
  dashboardContent: React.ReactNode;
  dataContent: React.ReactNode;
  isLoading?: boolean;
  className?: string;
  animationDuration?: number; // in milliseconds
}

const ViewTransition: React.FC<ViewTransitionProps> = ({
  currentView,
  dashboardContent,
  dataContent,
  isLoading = false,
  className = "",
  animationDuration = 150,
}) => {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayView, setDisplayView] = useState(currentView);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();

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
      setIsTransitioning(true);

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // If reduced motion is preferred, switch immediately
      if (prefersReducedMotion) {
        setDisplayView(currentView);
        setIsTransitioning(false);
        return;
      }

      // Start transition after a brief delay to ensure smooth animation
      timeoutRef.current = setTimeout(() => {
        setDisplayView(currentView);

        // End transition after animation completes
        timeoutRef.current = setTimeout(() => {
          setIsTransitioning(false);
        }, effectiveAnimationDuration);
      }, 10);
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
    const baseClasses = "transition-all ease-in-out";
    const durationClass = `duration-${effectiveAnimationDuration}`;

    if (isTransitioning) {
      return `${baseClasses} ${durationClass} opacity-0 transform scale-95`;
    }

    return `${baseClasses} ${durationClass} opacity-100 transform scale-100`;
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-sm text-gray-600">Loading view...</p>
          </div>
        </div>
      );
    }

    return displayView === "dashboard" ? dashboardContent : dataContent;
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
        style={{
          transitionDuration: `${effectiveAnimationDuration}ms`,
        }}
        role="tabpanel"
        id={`${displayView}-panel`}
        aria-labelledby={`${displayView}-tab`}
        tabIndex={0}
      >
        {renderContent()}
      </div>

      {/* Loading overlay for smooth transitions */}
      {(isTransitioning || isLoading) && (
        <div
          className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10"
          style={{
            transition: `opacity ${effectiveAnimationDuration}ms ease-in-out`,
          }}
        >
          <div className="animate-pulse">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
              <div
                className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                style={{ animationDelay: "0.1s" }}
              ></div>
              <div
                className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                style={{ animationDelay: "0.2s" }}
              ></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViewTransition;
