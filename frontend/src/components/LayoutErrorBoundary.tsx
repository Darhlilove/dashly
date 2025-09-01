import { Component, ErrorInfo, ReactNode } from "react";
import ErrorBoundary from "./ErrorBoundary";

interface Props {
  children: ReactNode;
  componentName: string;
  fallbackComponent?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * Specialized error boundary for layout components with graceful degradation
 */
class LayoutErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(
      `Layout Error in ${this.props.componentName}:`,
      error,
      errorInfo
    );

    // Report layout-specific errors
    this.reportLayoutError(error, errorInfo);
  }

  private reportLayoutError = (error: Error, errorInfo: ErrorInfo) => {
    const layoutErrorReport = {
      component: this.props.componentName,
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      userAgent: navigator.userAgent,
    };

    console.error("Layout Error Report:", layoutErrorReport);

    // In production, send to error reporting service
    // errorService.captureLayoutError(layoutErrorReport);
  };

  private getFallbackComponent = (): ReactNode => {
    const { componentName, fallbackComponent } = this.props;

    if (fallbackComponent) {
      return fallbackComponent;
    }

    // Provide component-specific fallbacks
    switch (componentName) {
      case "ResizableLayout":
        return (
          <div className="flex h-full">
            <div className="w-1/4 border-r border-gray-200 p-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                <p className="text-sm text-yellow-800">
                  Layout resizing is temporarily unavailable. Using fixed
                  layout.
                </p>
              </div>
              {/* Render children in a simple layout */}
              <div className="mt-4">
                {Array.isArray(this.props.children)
                  ? this.props.children[0]
                  : this.props.children}
              </div>
            </div>
            <div className="flex-1 p-4">
              {Array.isArray(this.props.children)
                ? this.props.children[1]
                : null}
            </div>
          </div>
        );

      case "AutoHideSidebar":
        return (
          <div className="flex h-full">
            <div className="w-64 bg-gray-50 border-r border-gray-200 p-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
                <p className="text-sm text-yellow-800">
                  Auto-hide sidebar is temporarily unavailable. Sidebar is
                  always visible.
                </p>
              </div>
              {/* Render sidebar content */}
              {Array.isArray(this.props.children)
                ? this.props.children.find(
                    (child: any) => child?.props?.["data-sidebar"] === true
                  )
                : null}
            </div>
            <div className="flex-1">
              {/* Render main content */}
              {Array.isArray(this.props.children)
                ? this.props.children.find(
                    (child: any) => child?.props?.["data-sidebar"] !== true
                  )
                : this.props.children}
            </div>
          </div>
        );

      case "DataTableView":
        return (
          <div className="p-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <p className="text-sm text-yellow-800">
                Advanced table features are temporarily unavailable. Showing
                basic data view.
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-medium">Data Preview</h3>
                <p className="text-sm text-gray-500">Basic table view</p>
              </div>
              <div className="p-4">
                <p className="text-gray-600">
                  Data table is temporarily unavailable. Please refresh the page
                  to try again.
                </p>
              </div>
            </div>
          </div>
        );

      case "ViewToggle":
        return (
          <div className="p-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <p className="text-sm text-yellow-800">
                View switching is temporarily unavailable. Showing default view.
              </p>
            </div>
            {this.props.children}
          </div>
        );

      default:
        return (
          <div className="p-4">
            <div className="bg-red-50 border border-red-200 rounded p-3">
              <p className="text-sm text-red-800">
                {componentName} component encountered an error and is
                temporarily unavailable.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="mt-2 text-sm text-red-800 underline hover:text-red-900"
              >
                Refresh page to try again
              </button>
            </div>
          </div>
        );
    }
  };

  render() {
    if (this.state.hasError) {
      return this.getFallbackComponent();
    }

    return this.props.children;
  }
}

/**
 * Higher-order component to wrap layout components with error boundaries
 */
export function withLayoutErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName: string,
  fallbackComponent?: ReactNode
) {
  const WithLayoutErrorBoundary = (props: P) => (
    <LayoutErrorBoundary
      componentName={componentName}
      fallbackComponent={fallbackComponent}
    >
      <WrappedComponent {...props} />
    </LayoutErrorBoundary>
  );

  WithLayoutErrorBoundary.displayName = `withLayoutErrorBoundary(${componentName})`;

  return WithLayoutErrorBoundary;
}

export default LayoutErrorBoundary;
