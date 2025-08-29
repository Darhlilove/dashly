import React, { useState, useCallback } from "react";
import { ApiError } from "../types/api";
import LoadingSpinner from "./LoadingSpinner";

interface ErrorRecoveryProps {
  error: ApiError;
  onRetry: () => Promise<void>;
  onDismiss?: () => void;
  maxRetries?: number;
  currentRetryCount?: number;
  className?: string;
  showTechnicalDetails?: boolean;
}

const ErrorRecovery: React.FC<ErrorRecoveryProps> = ({
  error,
  onRetry,
  onDismiss,
  maxRetries = 3,
  currentRetryCount = 0,
  className = "",
  showTechnicalDetails = false,
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const canRetry = error.retryable && currentRetryCount < maxRetries;
  const remainingRetries = maxRetries - currentRetryCount;

  const handleRetry = useCallback(async () => {
    if (!canRetry || isRetrying) return;

    setIsRetrying(true);
    try {
      await onRetry();
    } catch (retryError) {
      console.error("Retry failed:", retryError);
    } finally {
      setIsRetrying(false);
    }
  }, [canRetry, isRetrying, onRetry]);

  const getErrorIcon = () => {
    if (error.code?.includes("NETWORK") || error.code?.includes("TIMEOUT")) {
      return (
        <svg
          className="w-6 h-6 text-orange-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      );
    }

    if (error.retryable) {
      return (
        <svg
          className="w-6 h-6 text-yellow-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    }

    return (
      <svg
        className="w-6 h-6 text-red-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    );
  };

  const getErrorTitle = () => {
    if (error.code?.includes("NETWORK")) return "Connection Problem";
    if (error.code?.includes("TIMEOUT")) return "Request Timeout";
    if (error.code?.includes("VALIDATION")) return "Invalid Input";
    if (error.code?.includes("FILE_TOO_LARGE")) return "File Too Large";
    if (error.code?.includes("INVALID_FILE_TYPE")) return "Invalid File Type";
    if (error.code?.includes("SERVICE_UNAVAILABLE"))
      return "Service Unavailable";
    if (error.code?.includes("RATE_LIMIT")) return "Too Many Requests";
    if (error.retryable) return "Temporary Error";
    return "Error";
  };

  const getSuggestion = () => {
    if (error.code?.includes("NETWORK")) {
      return "Check your internet connection and try again.";
    }
    if (error.code?.includes("TIMEOUT")) {
      return "The request took too long. Try again or check your connection.";
    }
    if (error.code?.includes("FILE_TOO_LARGE")) {
      return "Please select a smaller file (under 10MB).";
    }
    if (error.code?.includes("INVALID_FILE_TYPE")) {
      return "Please select a valid CSV file.";
    }
    if (error.code?.includes("RATE_LIMIT")) {
      return "Please wait a moment before trying again.";
    }
    if (error.code?.includes("SERVICE_UNAVAILABLE")) {
      return "Our service is temporarily unavailable. Please try again in a few minutes.";
    }
    if (error.retryable) {
      return "This appears to be a temporary issue. Please try again.";
    }
    return "Please check your input and try again.";
  };

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg p-4 shadow-sm ${className}`}
    >
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">{getErrorIcon()}</div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 mb-1">
            {getErrorTitle()}
          </h3>

          <p className="text-sm text-gray-600 mb-2">{error.message}</p>

          <p className="text-xs text-gray-500 mb-3">{getSuggestion()}</p>

          {/* Action buttons */}
          <div className="flex items-center space-x-3">
            {canRetry && (
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isRetrying ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-3 h-3 mr-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    Try Again ({remainingRetries} left)
                  </>
                )}
              </button>
            )}

            {onDismiss && (
              <button
                onClick={onDismiss}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Dismiss
              </button>
            )}

            {showTechnicalDetails && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                {showDetails ? "Hide" : "Show"} Details
              </button>
            )}
          </div>

          {/* Technical details */}
          {showDetails && showTechnicalDetails && (
            <div className="mt-3 p-3 bg-gray-50 rounded text-xs font-mono text-gray-600 border">
              <div className="space-y-1">
                <div>
                  <strong>Error Code:</strong> {error.code}
                </div>
                <div>
                  <strong>Timestamp:</strong> {error.timestamp}
                </div>
                {error.requestId && (
                  <div>
                    <strong>Request ID:</strong> {error.requestId}
                  </div>
                )}
                <div>
                  <strong>Retryable:</strong> {error.retryable ? "Yes" : "No"}
                </div>
                <div>
                  <strong>Retry Count:</strong> {currentRetryCount}/{maxRetries}
                </div>
                {error.details && (
                  <div>
                    <strong>Details:</strong>
                    <pre className="mt-1 whitespace-pre-wrap text-xs">
                      {JSON.stringify(error.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorRecovery;
