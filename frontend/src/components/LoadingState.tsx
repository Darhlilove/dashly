import React, { useState, useEffect } from "react";
import LoadingSpinner from "./LoadingSpinner";

interface LoadingStateProps {
  isLoading: boolean;
  message?: string;
  progress?: number; // 0-100
  showProgress?: boolean;
  timeout?: number; // milliseconds
  onTimeout?: () => void;
  size?: "sm" | "md" | "lg";
  className?: string;
  overlay?: boolean;
  children?: React.ReactNode;
}

const LoadingState: React.FC<LoadingStateProps> = ({
  isLoading,
  message = "Loading...",
  progress,
  showProgress = false,
  timeout,
  onTimeout,
  size = "md",
  className = "",
  overlay = false,
  children,
}) => {
  const [timeoutReached, setTimeoutReached] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setTimeoutReached(false);
      setElapsedTime(0);
      return;
    }

    const startTime = Date.now();

    // Update elapsed time every second
    const elapsedInterval = setInterval(() => {
      setElapsedTime(Date.now() - startTime);
    }, 1000);

    // Set timeout if specified
    let timeoutId: NodeJS.Timeout | undefined;
    if (timeout) {
      timeoutId = setTimeout(() => {
        setTimeoutReached(true);
        onTimeout?.();
      }, timeout);
    }

    return () => {
      clearInterval(elapsedInterval);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [isLoading, timeout, onTimeout]);

  const formatElapsedTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) {
      return `${seconds}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getLoadingMessage = () => {
    if (timeoutReached) {
      return "This is taking longer than expected...";
    }

    if (elapsedTime > 10000) {
      // 10 seconds
      return `${message} (${formatElapsedTime(elapsedTime)})`;
    }

    return message;
  };

  if (!isLoading) {
    return <>{children}</>;
  }

  const loadingContent = (
    <div
      className={`flex flex-col items-center justify-center p-6 ${className}`}
    >
      <LoadingSpinner size={size} className="mb-4" />

      <div className="text-center max-w-sm">
        <p
          className={`text-gray-700 mb-2 ${
            size === "sm" ? "text-sm" : size === "lg" ? "text-lg" : "text-base"
          }`}
        >
          {getLoadingMessage()}
        </p>

        {showProgress && typeof progress === "number" && (
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        )}

        {showProgress && typeof progress === "number" && (
          <p className="text-xs text-gray-500 mb-2">
            {Math.round(progress)}% complete
          </p>
        )}

        {elapsedTime > 5000 && (
          <p className="text-xs text-gray-500">
            Elapsed: {formatElapsedTime(elapsedTime)}
          </p>
        )}

        {timeoutReached && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              The operation is taking longer than usual. You can wait or try
              refreshing the page.
            </p>
          </div>
        )}
      </div>
    </div>
  );

  if (overlay) {
    return (
      <>
        {children}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="loading-title"
        >
          <div className="bg-white rounded-lg shadow-lg max-w-sm w-full">
            <div id="loading-title" className="sr-only">
              {message}
            </div>
            {loadingContent}
          </div>
        </div>
      </>
    );
  }

  return loadingContent;
};

// Specialized loading components for different scenarios
export const FileUploadLoading: React.FC<{
  isLoading: boolean;
  fileName?: string;
  progress?: number;
}> = ({ isLoading, fileName, progress }) => (
  <LoadingState
    isLoading={isLoading}
    message={fileName ? `Uploading ${fileName}...` : "Uploading file..."}
    progress={progress}
    showProgress={true}
    timeout={60000} // 1 minute timeout for uploads
    size="md"
  />
);

export const QueryProcessingLoading: React.FC<{
  isLoading: boolean;
  stage?: "translating" | "executing" | "processing";
}> = ({ isLoading, stage = "processing" }) => {
  const messages = {
    translating: "Converting your question to SQL...",
    executing: "Running your query...",
    processing: "Processing your request...",
  };

  return (
    <LoadingState
      isLoading={isLoading}
      message={messages[stage]}
      timeout={45000} // 45 seconds for query processing
      size="md"
    />
  );
};

export const DashboardLoadingOverlay: React.FC<{
  isLoading: boolean;
  message?: string;
  children: React.ReactNode;
}> = ({ isLoading, message = "Loading dashboard...", children }) => (
  <LoadingState
    isLoading={isLoading}
    message={message}
    overlay={true}
    size="md"
  >
    {children}
  </LoadingState>
);

export default LoadingState;
