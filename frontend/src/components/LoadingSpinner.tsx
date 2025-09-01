import React from "react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  variant?: "spinner" | "dots" | "pulse";
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  variant = "spinner",
  className = "",
}) => {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 sm:w-8 sm:h-8 border-2",
    lg: "w-10 h-10 sm:w-12 sm:h-12 border-2 sm:border-3",
  };

  const dotSizeClasses = {
    sm: "w-1 h-1",
    md: "w-2 h-2",
    lg: "w-3 h-3",
  };

  if (variant === "dots") {
    return (
      <div
        className={`inline-flex space-x-1 ${className}`}
        role="status"
        aria-label="Loading"
        aria-live="polite"
      >
        <div
          className={`${dotSizeClasses[size]} bg-blue-600 rounded-full loading-dots-enhanced dot`}
        ></div>
        <div
          className={`${dotSizeClasses[size]} bg-blue-600 rounded-full loading-dots-enhanced dot`}
        ></div>
        <div
          className={`${dotSizeClasses[size]} bg-blue-600 rounded-full loading-dots-enhanced dot`}
        ></div>
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (variant === "pulse") {
    return (
      <div className={`inline-block ${className}`}>
        <div
          className={`${sizeClasses[size]} bg-blue-600 rounded-full loading-spinner-enhanced`}
          role="status"
          aria-label="Loading"
          aria-live="polite"
        >
          <span className="sr-only">Loading...</span>
        </div>
      </div>
    );
  }

  // Default spinner variant
  return (
    <div className={`inline-block ${className}`}>
      <div
        className={`${sizeClasses[size]} border-gray-200 border-t-blue-600 animate-spin rounded-full`}
        role="status"
        aria-label="Loading"
        aria-live="polite"
      >
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  );
};

export default LoadingSpinner;
