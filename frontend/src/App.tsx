import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { ToastContainer, LoadingSpinner, ErrorBoundary } from "./components";
import MainLayout, { Message } from "./components/MainLayout";
import IntroPage from "./components/IntroPage";
import DashboardWorkspace from "./components/DashboardWorkspace";

// Lazy load modals
const SQLPreviewModal = lazy(() => import("./components/SQLPreviewModal"));
import { AppState, ToastNotification, Dashboard, ApiError } from "./types";
import { apiService } from "./services/api";
import { selectChartType } from "./utils";
import { generateId } from "./utils";
import { useErrorHandler } from "./hooks/useErrorHandler";
import { useSessionCache } from "./hooks/useSessionCache";
import "./utils/optimization"; // Load optimization checks

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
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentDashboardId, setCurrentDashboardId] = useState<
    string | undefined
  >();

  // Global error handler
  const { handleError: handleGlobalError } = useErrorHandler({
    onError: (error) => {
      addNotification("error", error.message);
    },
  });

  // Session cache for query results
  const { getCachedResult, setCachedResult } = useSessionCache();

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
    // Add user message
    const userMessage: Message = {
      id: generateId(),
      type: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setState((prev) => ({
      ...prev,
      currentQuery: query,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await apiService.translateQuery(query);

      // Add assistant message with SQL
      const assistantMessage: Message = {
        id: generateId(),
        type: "assistant",
        content: `I've generated this SQL query for you:\n\n\`\`\`sql\n${response.sql}\n\`\`\`\n\nWould you like me to execute it?`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      setState((prev) => ({
        ...prev,
        currentSQL: response.sql,
        showSQLModal: true,
        isLoading: false,
      }));
    } catch (error) {
      const apiError = error as ApiError;

      // Add error message
      const errorMessage: Message = {
        id: generateId(),
        type: "assistant",
        content: `Sorry, I couldn't translate your query: ${apiError.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);

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
      // Check cache first
      const cachedResult = getCachedResult(sql, state.currentQuery);
      let response: typeof cachedResult;

      if (cachedResult) {
        response = cachedResult;
        addNotification("info", "Using cached results");
      } else {
        response = await apiService.executeSQL(sql, state.currentQuery);
        // Cache the result
        setCachedResult(sql, state.currentQuery, response);
      }

      const chartConfig = selectChartType({
        columns: response.columns,
        rows: response.rows,
      });

      // Add success message
      const successMessage: Message = {
        id: generateId(),
        type: "assistant",
        content: `Great! I've executed your query and found ${response.row_count} rows. The results are displayed in the dashboard on the right.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, successMessage]);

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

      // Add error message
      const errorMessage: Message = {
        id: generateId(),
        type: "assistant",
        content: `There was an error executing the query: ${apiError.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);

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
    setCurrentDashboardId(dashboard.id);

    try {
      const response = await apiService.executeSQL(
        dashboard.sql,
        dashboard.question
      );

      // Clear messages and add loaded dashboard context
      const loadMessage: Message = {
        id: generateId(),
        type: "assistant",
        content: `I've loaded the "${dashboard.name}" dashboard. The data shows ${response.row_count} rows based on the question: "${dashboard.question}"`,
        timestamp: new Date(),
      };
      setMessages([loadMessage]);

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

  // Handle new dashboard
  const handleNewDashboard = () => {
    setState((prev) => ({
      ...prev,
      currentQuery: "",
      currentSQL: "",
      queryResults: null,
      currentChart: null,
      error: null,
      uploadStatus: "idle",
      tableInfo: null,
    }));
    setMessages([]);
    setCurrentDashboardId(undefined);
  };

  // Determine current phase based on application state
  const hasData = state.uploadStatus === "completed" && state.tableInfo;
  const showConversation = Boolean(hasData);

  return (
    <div className="h-screen bg-white">
      {/* Skip link for keyboard navigation */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <ErrorBoundary level="component" onError={handleGlobalError}>
        <MainLayout
          savedDashboards={state.savedDashboards}
          onLoadDashboard={handleLoadDashboard}
          onNewDashboard={handleNewDashboard}
          currentDashboardId={currentDashboardId}
          messages={messages}
          onSendMessage={handleQuery}
          isLoading={state.isLoading}
          showConversation={showConversation}
        >
          <main id="main-content" role="main" className="h-full">
            {!hasData ? (
              <IntroPage
                onFileUpload={handleFileUpload}
                onDemoData={handleDemoData}
                isLoading={state.isLoading}
                error={state.error}
                savedDashboards={state.savedDashboards}
                onLoadDashboard={handleLoadDashboard}
              />
            ) : (
              <DashboardWorkspace
                tableInfo={state.tableInfo!}
                queryResults={state.queryResults}
                currentChart={state.currentChart}
                currentQuery={state.currentQuery}
                onSaveDashboard={handleSaveDashboard}
                isLoading={state.isLoading}
              />
            )}
          </main>
        </MainLayout>
      </ErrorBoundary>

      {/* SQL Preview Modal */}
      {state.showSQLModal && (
        <ErrorBoundary level="component" onError={handleGlobalError}>
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white p-6 flex items-center gap-4 border border-gray-300">
                  <LoadingSpinner size="md" />
                  <span className="text-black">Loading...</span>
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
