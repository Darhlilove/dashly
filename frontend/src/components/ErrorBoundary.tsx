import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: "page" | "component";
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  retryCount: number;
}

class ErrorBoundary extends Component<Props, State> {
  private retryTimeoutId: NodeJS.Timeout | null = null;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Report error to external service (if configured)
    this.reportError(error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // In a real app, you might send this to an error reporting service
    // like Sentry, LogRocket, or Bugsnag
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    console.error("Error Report:", errorReport);

    // Example: Send to error reporting service
    // errorReportingService.captureException(error, { extra: errorReport })
  };

  private handleRetry = () => {
    const maxRetries = 3;
    if (this.state.retryCount < maxRetries) {
      this.setState((prevState) => ({
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        retryCount: prevState.retryCount + 1,
      }));
    }
  };

  private handleRefresh = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = "/";
  };

  private getErrorMessage = (error?: Error): string => {
    if (!error) return "An unexpected error occurred";

    // Provide user-friendly messages for common errors
    if (error.message.includes("ChunkLoadError")) {
      return "Failed to load application resources. Please refresh the page.";
    }
    if (error.message.includes("Network Error")) {
      return "Network connection error. Please check your internet connection.";
    }
    if (error instanceof TypeError || error.name === "TypeError") {
      return "A technical error occurred. Our team has been notified.";
    }

    return error.message || "An unexpected error occurred";
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isPageLevel = this.props.level === "page";
      const maxRetries = 3;
      const canRetry = this.state.retryCount < maxRetries;
      const errorMessage = this.getErrorMessage(this.state.error);

      // Component-level error boundary (smaller, inline error)
      if (!isPageLevel) {
        return (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-medium text-red-800">
                  Component Error
                </h3>
                <p className="mt-1 text-sm text-red-700">{errorMessage}</p>
                <div className="mt-3 flex space-x-3">
                  {canRetry && (
                    <button
                      onClick={this.handleRetry}
                      className="text-sm font-medium text-red-800 hover:text-red-900 underline"
                    >
                      Try Again ({maxRetries - this.state.retryCount} attempts
                      left)
                    </button>
                  )}
                  <button
                    onClick={this.handleRefresh}
                    className="text-sm font-medium text-red-800 hover:text-red-900 underline"
                  >
                    Refresh Page
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      }

      // Page-level error boundary (full page error)
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
          <div className="max-w-md mx-auto bg-white rounded-lg shadow-lg p-6">
            <div className="text-center">
              <div
                className="text-red-500 text-6xl mb-4"
                role="img"
                aria-label="Error"
              >
                ⚠️
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Oops! Something went wrong
              </h1>
              <p className="text-gray-600 mb-6">{errorMessage}</p>

              <div className="space-y-3">
                {canRetry && (
                  <button
                    onClick={this.handleRetry}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                  >
                    Try Again ({maxRetries - this.state.retryCount} attempts
                    left)
                  </button>
                )}

                <button
                  onClick={this.handleRefresh}
                  className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
                >
                  Refresh Page
                </button>

                <button
                  onClick={this.handleGoHome}
                  className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
                >
                  Go to Home
                </button>
              </div>

              {/* Error details for debugging */}
              <details className="mt-6 text-left">
                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 rounded">
                  Show technical details
                </summary>
                <div className="mt-3 p-3 bg-gray-100 rounded text-xs font-mono text-gray-700 overflow-auto max-h-40 text-left">
                  <div className="mb-2">
                    <strong>Error:</strong> {this.state.error?.message}
                  </div>
                  <div className="mb-2">
                    <strong>Retry Count:</strong> {this.state.retryCount}
                  </div>
                  {this.state.error?.stack && (
                    <div>
                      <strong>Stack Trace:</strong>
                      <pre className="whitespace-pre-wrap mt-1">
                        {this.state.error.stack}
                      </pre>
                    </div>
                  )}
                  {this.state.errorInfo?.componentStack && (
                    <div className="mt-2">
                      <strong>Component Stack:</strong>
                      <pre className="whitespace-pre-wrap mt-1">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
