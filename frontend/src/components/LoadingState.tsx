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
    let timeoutId: number | undefined;
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
              role="progressbar"
              aria-valuenow={Math.min(100, Math.max(0, progress))}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Progress: ${Math.round(progress)}%`}
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
  stage?: "validating" | "uploading" | "processing" | "complete";
}> = ({ isLoading, fileName, progress, stage = "uploading" }) => {
  const getStageMessage = () => {
    switch (stage) {
      case "validating":
        return fileName ? `Validating ${fileName}...` : "Validating file...";
      case "uploading":
        return fileName ? `Uploading ${fileName}...` : "Uploading file...";
      case "processing":
        return fileName ? `Processing ${fileName}...` : "Processing file...";
      case "complete":
        return fileName
          ? `${fileName} uploaded successfully!`
          : "File uploaded successfully!";
      default:
        return fileName ? `Uploading ${fileName}...` : "Uploading file...";
    }
  };

  return (
    <LoadingState
      isLoading={isLoading}
      message={getStageMessage()}
      progress={progress}
      showProgress={true}
      timeout={60000} // 1 minute timeout for uploads
      size="md"
    />
  );
};

export const QueryProcessingLoading: React.FC<{
  isLoading: boolean;
  stage?:
    | "translating"
    | "executing"
    | "processing"
    | "generating_chart"
    | "complete";
  progress?: number;
  queryText?: string;
}> = ({ isLoading, stage = "processing", progress, queryText }) => {
  const getStageMessage = () => {
    const baseMessages = {
      translating: "Converting your question to SQL...",
      executing: "Running your query...",
      processing: "Processing your request...",
      generating_chart: "Creating visualization...",
      complete: "Query completed successfully!",
    };

    const message = baseMessages[stage];

    // Add query context for better user understanding
    if (queryText && queryText.length > 0 && stage !== "complete") {
      const shortQuery =
        queryText.length > 40 ? `${queryText.substring(0, 40)}...` : queryText;
      return `${message}\n"${shortQuery}"`;
    }

    return message;
  };

  return (
    <LoadingState
      isLoading={isLoading}
      message={getStageMessage()}
      progress={progress}
      showProgress={typeof progress === "number"}
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

export const DataProcessingLoading: React.FC<{
  isLoading: boolean;
  stage?: "uploading" | "parsing" | "validating" | "storing" | "complete";
  progress?: number;
  fileName?: string;
  rowsProcessed?: number;
  totalRows?: number;
}> = ({
  isLoading,
  stage = "uploading",
  progress,
  fileName,
  rowsProcessed,
  totalRows,
}) => {
  const getStageMessage = () => {
    const baseMessages = {
      uploading: "Uploading your data...",
      parsing: "Reading and parsing CSV data...",
      validating: "Validating data structure...",
      storing: "Storing data in database...",
      complete: "Data processing complete!",
    };

    let message = baseMessages[stage];

    if (fileName) {
      message = message.replace("your data", fileName);
    }

    if (rowsProcessed && totalRows && stage === "storing") {
      message += `\nProcessed ${rowsProcessed.toLocaleString()} of ${totalRows.toLocaleString()} rows`;
    }

    return message;
  };

  const calculateProgress = () => {
    if (typeof progress === "number") {
      return progress;
    }

    if (rowsProcessed && totalRows) {
      return Math.round((rowsProcessed / totalRows) * 100);
    }

    // Default progress based on stage
    const stageProgress = {
      uploading: 25,
      parsing: 50,
      validating: 75,
      storing: 90,
      complete: 100,
    };

    return stageProgress[stage];
  };

  return (
    <LoadingState
      isLoading={isLoading}
      message={getStageMessage()}
      progress={calculateProgress()}
      showProgress={true}
      timeout={120000} // 2 minute timeout for data processing
      size="md"
    />
  );
};

export const ViewTransitionLoading: React.FC<{
  isLoading: boolean;
  fromView?: string;
  toView?: string;
}> = ({ isLoading, fromView, toView }) => {
  const getMessage = () => {
    if (fromView && toView) {
      return `Switching from ${fromView} to ${toView} view...`;
    }
    return "Switching views...";
  };

  return (
    <LoadingState
      isLoading={isLoading}
      message={getMessage()}
      size="sm"
      timeout={5000} // Short timeout for view transitions
    />
  );
};

export default LoadingState;
