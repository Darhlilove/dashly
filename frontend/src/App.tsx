import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { ToastContainer, LoadingSpinner, ErrorBoundary } from "./components";
import {
  UploadWidgetSkeleton,
  QueryBoxSkeleton,
} from "./components/SkeletonLoader";

// Lazy load phase components and modals
const UploadPhase = lazy(() => import("./components/UploadPhase"));
const QueryPhase = lazy(() => import("./components/QueryPhase"));
const SQLPreviewModal = lazy(() => import("./components/SQLPreviewModal"));
import { AppState, ToastNotification, Dashboard, ApiError } from "./types";
import { apiService } from "./services/api";
import { selectChartType } from "./utils";
import { generateId } from "./utils";
import { useErrorHandler } from "./hooks/useErrorHandler";

// Initial application state
const initialState: AppState = {
  uploadStatus: "idle",
  tableInfo: null,
  currentQuery: "",
  currentSQL: "",
  queryResults: null,
  currentChart: null,
  savedDashboards: [],
  showSQLModal: false,
  isLoading: false,
  error: null,
};

function App() {
  const [state, setState] = useState<AppState>(initialState);
  const [notifications, setNotifications] = useState<ToastNotification[]>([]);

  // Global error handler
  const { handleError: handleGlobalError } = useErrorHandler({
    onError: (error) => {
      addNotification("error", error.message);
    },
  });

  // Toast notification management
  const addNotification = useCallback(
    (type: "success" | "error" | "info", message: string) => {
      const notification: ToastNotification = {
        id: generateId(),
        type,
        message,
        duration: type === "error" ? 7000 : 5000, // Longer duration for errors
      };
      setNotifications((prev) => [...prev, notification]);
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  // Load saved dashboards on app initialization
  useEffect(() => {
    const loadDashboards = async () => {
      try {
        const dashboards = await apiService.getDashboards();
        setState((prev) => ({ ...prev, savedDashboards: dashboards }));
      } catch (error) {
        console.error("Failed to load dashboards:", error);
        // Don't show error toast for initial load failure, but log it
        handleGlobalError(error as ApiError);
      }
    };

    loadDashboards();
  }, [handleGlobalError]);

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    setState((prev) => ({
      ...prev,
      uploadStatus: "uploading",
      isLoading: true,
      error: null,
    }));

    try {
      const response = await apiService.uploadFile(file);
      setState((prev) => ({
        ...prev,
        uploadStatus: "completed",
        tableInfo: response,
        isLoading: false,
      }));
      addNotification("success", `Successfully uploaded ${file.name}`);

      // Preload query phase components since user will likely query next
      import("./components/QueryPhase");
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({
        ...prev,
        uploadStatus: "error",
        error: apiError.message,
        isLoading: false,
      }));
      addNotification("error", `Upload failed: ${apiError.message}`);
    }
  };

  // Handle demo data selection
  const handleDemoData = async () => {
    setState((prev) => ({
      ...prev,
      uploadStatus: "uploading",
      isLoading: true,
      error: null,
    }));

    try {
      const response = await apiService.useDemoData();
      setState((prev) => ({
        ...prev,
        uploadStatus: "completed",
        tableInfo: response,
        isLoading: false,
      }));
      addNotification("success", "Demo data loaded successfully");

      // Preload query phase components since user will likely query next
      import("./components/QueryPhase");
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({
        ...prev,
        uploadStatus: "error",
        error: apiError.message,
        isLoading: false,
      }));
      addNotification("error", `Failed to load demo data: ${apiError.message}`);
    }
  };

  // Handle natural language query
  const handleQuery = async (query: string) => {
    setState((prev) => ({
      ...prev,
      currentQuery: query,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await apiService.translateQuery(query);
      setState((prev) => ({
        ...prev,
        currentSQL: response.sql,
        showSQLModal: true,
        isLoading: false,
      }));
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({
        ...prev,
        error: apiError.message,
        isLoading: false,
      }));
      addNotification("error", `Query translation failed: ${apiError.message}`);
    }
  };

  // Handle SQL execution
  const handleSQLExecution = async (sql: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiService.executeSQL(sql);
      const chartConfig = selectChartType({
        columns: response.columns,
        rows: response.rows,
      });

      setState((prev) => ({
        ...prev,
        queryResults: response,
        currentChart: chartConfig,
        showSQLModal: false,
        isLoading: false,
      }));
      addNotification(
        "success",
        `Query executed successfully (${response.row_count} rows, ${response.runtime_ms}ms)`
      );
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({
        ...prev,
        error: apiError.message,
        isLoading: false,
      }));
      addNotification("error", `Query execution failed: ${apiError.message}`);
    }
  };

  // Handle dashboard saving
  const handleSaveDashboard = async (name: string) => {
    if (!state.currentQuery || !state.currentSQL || !state.currentChart) {
      addNotification("error", "No dashboard to save");
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      const dashboard = await apiService.saveDashboard({
        name,
        question: state.currentQuery,
        sql: state.currentSQL,
        chartConfig: state.currentChart,
      });

      setState((prev) => ({
        ...prev,
        savedDashboards: [...prev.savedDashboards, dashboard],
        isLoading: false,
      }));
      addNotification("success", `Dashboard "${name}" saved successfully`);
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({ ...prev, isLoading: false }));
      addNotification("error", `Failed to save dashboard: ${apiError.message}`);
    }
  };

  // Handle loading saved dashboard
  const handleLoadDashboard = async (dashboard: Dashboard) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiService.executeSQL(dashboard.sql);

      setState((prev) => ({
        ...prev,
        currentQuery: dashboard.question,
        currentSQL: dashboard.sql,
        queryResults: response,
        currentChart: dashboard.chartConfig,
        isLoading: false,
      }));
      addNotification("success", `Loaded dashboard "${dashboard.name}"`);
    } catch (error) {
      const apiError = error as ApiError;
      setState((prev) => ({
        ...prev,
        error: apiError.message,
        isLoading: false,
      }));
      addNotification("error", `Failed to load dashboard: ${apiError.message}`);
    }
  };

  // Handle modal close
  const handleModalClose = () => {
    setState((prev) => ({ ...prev, showSQLModal: false }));
  };

  // Handle new query (reset current results)
  const handleNewQuery = () => {
    setState((prev) => ({
      ...prev,
      currentQuery: "",
      currentSQL: "",
      queryResults: null,
      currentChart: null,
      error: null,
    }));
  };

  // Determine current phase based on application state
  const currentPhase = state.uploadStatus === "completed" ? "query" : "upload";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Skip link for keyboard navigation */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
        <header className="text-center mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-2">
            Dashly
          </h1>
          <p className="text-base sm:text-lg text-gray-600">
            Dashboard Auto-Designer
          </p>
          {state.tableInfo && (
            <p className="text-sm text-gray-500 mt-2">
              Table: {state.tableInfo.table} ({state.tableInfo.columns.length}{" "}
              columns)
            </p>
          )}
        </header>

        <main id="main-content" className="max-w-7xl mx-auto" role="main">
          <ErrorBoundary level="component" onError={handleGlobalError}>
            {/* Upload Phase */}
            {currentPhase === "upload" && (
              <Suspense fallback={<UploadWidgetSkeleton />}>
                <UploadPhase
                  onFileUpload={handleFileUpload}
                  onDemoData={handleDemoData}
                  isLoading={state.isLoading}
                  error={state.error}
                  savedDashboards={state.savedDashboards}
                  onLoadDashboard={handleLoadDashboard}
                />
              </Suspense>
            )}

            {/* Query Phase */}
            {currentPhase === "query" && (
              <Suspense fallback={<QueryBoxSkeleton />}>
                <QueryPhase
                  currentQuery={state.currentQuery}
                  isLoading={state.isLoading}
                  onQuery={handleQuery}
                  onNewQuery={handleNewQuery}
                  queryResults={state.queryResults}
                  currentChart={state.currentChart}
                  onSaveDashboard={handleSaveDashboard}
                  savedDashboards={state.savedDashboards}
                  onLoadDashboard={handleLoadDashboard}
                />
              </Suspense>
            )}
          </ErrorBoundary>

          {/* Global loading overlay */}
          {state.isLoading && (
            <div
              className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="loading-title"
            >
              <div className="bg-white rounded-lg p-4 sm:p-6 flex items-center gap-4 max-w-sm w-full">
                <LoadingSpinner size="md" />
                <span
                  id="loading-title"
                  className="text-gray-700 text-sm sm:text-base"
                >
                  Processing...
                </span>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* SQL Preview Modal */}
      {state.showSQLModal && (
        <ErrorBoundary level="component" onError={handleGlobalError}>
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 flex items-center gap-4">
                  <LoadingSpinner size="md" />
                  <span className="text-gray-700">Loading...</span>
                </div>
              </div>
            }
          >
            <SQLPreviewModal
              sql={state.currentSQL}
              onExecute={handleSQLExecution}
              onClose={handleModalClose}
              isLoading={state.isLoading}
            />
          </Suspense>
        </ErrorBoundary>
      )}

      {/* Toast Notifications */}
      <ToastContainer
        notifications={notifications}
        onDismiss={removeNotification}
      />
    </div>
  );
}

export default App;
