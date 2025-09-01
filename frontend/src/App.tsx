import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { ToastContainer, LoadingSpinner, ErrorBoundary } from "./components";
import { Message } from "./types";
import ResizableLayout from "./components/ResizableLayout";
import AutoHideSidebar from "./components/AutoHideSidebar";
import ConversationPane from "./components/ConversationPane";
import Sidebar from "./components/Sidebar";
import IntroPage from "./components/IntroPage";
import DashboardWorkspace from "./components/DashboardWorkspace";

// Lazy load modals
const SQLPreviewModal = lazy(() => import("./components/SQLPreviewModal"));
import { AppState, ToastNotification, Dashboard, ApiError } from "./types";
import { LayoutState, ViewType } from "./types/layout";
import { apiService } from "./services/api";
import { selectChartType } from "./utils";
import { generateId } from "./utils";
import { useErrorHandler } from "./hooks/useErrorHandler";
import { useSessionCache } from "./hooks/useSessionCache";
import { useBreakpoint } from "./hooks/useMediaQuery";
import { useLayoutPreferences } from "./hooks/useLayoutPreferences";
import { useUserPreferences } from "./hooks/useUserPreferences";
import { LAYOUT_CONFIG } from "./config/layout";
import SettingsModal from "./components/SettingsModal";
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

// Initial layout state - will be overridden by preferences
const getInitialLayoutState = (breakpoint: string): LayoutState => ({
  sidebarVisible: false,
  chatPaneWidth: LAYOUT_CONFIG.defaultSizes.desktop.chat,
  dashboardPaneWidth: LAYOUT_CONFIG.defaultSizes.desktop.dashboard,
  currentView: "data" as ViewType, // Default to data view as per requirements
  currentBreakpoint: breakpoint as any,
  isResizing: false,
});

function App() {
  const [state, setState] = useState<AppState>(initialState);
  const [notifications, setNotifications] = useState<ToastNotification[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentDashboardId, setCurrentDashboardId] = useState<
    string | undefined
  >();

  // Layout state management
  const currentBreakpoint = useBreakpoint();
  const [layoutState, setLayoutState] = useState<LayoutState>(() =>
    getInitialLayoutState(currentBreakpoint)
  );

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

  // Layout preferences management
  const {
    loadPreferences,
    savePreferences,
    resetPreferences,
    resetAllPreferences,
  } = useLayoutPreferences();

  // User preferences management
  const userPreferences = useUserPreferences();

  // Mobile view state (separate from desktop view state)
  const [mobileView, setMobileView] = useState<"chat" | "data" | "dashboard">(
    "chat"
  );

  // Settings modal state
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Initialize layout preferences after hooks are ready
  useEffect(() => {
    const preferences = loadPreferences(currentBreakpoint as any);
    setLayoutState((prev) => ({ ...prev, ...preferences }));
  }, [loadPreferences, currentBreakpoint]);

  // Layout state handlers
  const handleSidebarVisibilityChange = useCallback((visible: boolean) => {
    setLayoutState((prev) => ({ ...prev, sidebarVisible: visible }));
  }, []);

  const handlePaneResize = useCallback(
    (chatWidth: number, dashboardWidth: number) => {
      setLayoutState((prev) => ({
        ...prev,
        chatPaneWidth: chatWidth,
        dashboardPaneWidth: dashboardWidth,
      }));
    },
    []
  );

  const handleViewChange = useCallback((view: ViewType) => {
    setLayoutState((prev) => ({ ...prev, currentView: view }));
  }, []);

  const handleMobileViewChange = useCallback(
    (view: "chat" | "data" | "dashboard") => {
      setMobileView(view);
    },
    []
  );

  // Layout preference handlers
  const handleResetLayoutPreferences = useCallback(() => {
    const defaultPreferences = resetPreferences(layoutState.currentBreakpoint);
    setLayoutState((prev) => ({ ...prev, ...defaultPreferences }));
    addNotification("success", "Layout reset to defaults");
  }, [layoutState.currentBreakpoint, resetPreferences, addNotification]);

  const handleResetAllLayoutPreferences = useCallback(() => {
    resetAllPreferences();
    // Reload preferences for current breakpoint
    const preferences = loadPreferences(layoutState.currentBreakpoint);
    setLayoutState((prev) => ({ ...prev, ...preferences }));
    addNotification("success", "All layout preferences reset to defaults");
  }, [
    resetAllPreferences,
    loadPreferences,
    layoutState.currentBreakpoint,
    addNotification,
  ]);

  // Update layout state when breakpoint changes
  useEffect(() => {
    setLayoutState((prev) => {
      // Load preferences for the new breakpoint
      const preferences = loadPreferences(currentBreakpoint as any);

      return {
        ...prev,
        currentBreakpoint: currentBreakpoint as any,
        // Only update sizes if not currently resizing
        ...(prev.isResizing
          ? {}
          : {
              chatPaneWidth: preferences.chatPaneWidth ?? prev.chatPaneWidth,
              dashboardPaneWidth:
                preferences.dashboardPaneWidth ?? prev.dashboardPaneWidth,
              currentView: preferences.currentView ?? prev.currentView,
              sidebarVisible: preferences.sidebarVisible ?? prev.sidebarVisible,
            }),
      };
    });
  }, [currentBreakpoint, loadPreferences]);

  // Save layout preferences when layout state changes
  useEffect(() => {
    // Don't save during initial render or while resizing
    if (layoutState.isResizing) return;

    // Save preferences with a small delay to avoid excessive saves
    const timeoutId = setTimeout(() => {
      savePreferences(layoutState);
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [
    layoutState.chatPaneWidth,
    layoutState.dashboardPaneWidth,
    layoutState.currentView,
    layoutState.sidebarVisible,
    layoutState.currentBreakpoint,
    layoutState.isResizing,
    savePreferences,
  ]);

  // Apply user preferences to document
  useEffect(() => {
    const { preferences, animationsEnabled, effectiveTheme } = userPreferences;
    const root = document.documentElement;
    const body = document.body;

    // Apply animation classes
    if (animationsEnabled) {
      root.classList.add("animations-enabled");
      root.classList.remove("animations-disabled");
    } else {
      root.classList.add("animations-disabled");
      root.classList.remove("animations-enabled");
    }

    // Apply accessibility classes
    if (preferences.accessibility.highContrast) {
      body.classList.add("high-contrast");
    } else {
      body.classList.remove("high-contrast");
    }

    if (preferences.accessibility.screenReaderOptimizations) {
      body.classList.add("screen-reader-optimized");
    } else {
      body.classList.remove("screen-reader-optimized");
    }

    if (preferences.accessibility.keyboardNavigation) {
      body.classList.add("keyboard-navigation-enhanced");
    } else {
      body.classList.remove("keyboard-navigation-enhanced");
    }

    // Apply UI preferences
    if (preferences.ui.compactMode) {
      body.classList.add("compact-mode");
    } else {
      body.classList.remove("compact-mode");
    }

    // Apply theme (for future dark mode support)
    body.setAttribute("data-theme", effectiveTheme);

    // Apply mobile animation preferences
    if (currentBreakpoint === "mobile" && !animationsEnabled) {
      body.classList.add("mobile-no-animations");
    } else {
      body.classList.remove("mobile-no-animations");
    }
  }, [userPreferences, currentBreakpoint]);

  // Handle orientation changes on mobile/tablet
  useEffect(() => {
    const handleOrientationChange = () => {
      // Force a re-render after orientation change to recalculate layout
      setTimeout(() => {
        window.dispatchEvent(new Event("resize"));
      }, 100);
    };

    window.addEventListener("orientationchange", handleOrientationChange);
    return () =>
      window.removeEventListener("orientationchange", handleOrientationChange);
  }, []);

  // Load saved dashboards on app initialization - TEMPORARILY DISABLED
  useEffect(() => {
    console.log("Dashboard loading temporarily disabled for debugging");
    // const loadDashboards = async () => {
    //   try {
    //     const dashboards = await apiService.getDashboards();
    //     setState((prev) => ({ ...prev, savedDashboards: dashboards }));
    //   } catch (error) {
    //     console.error("Failed to load dashboards:", error);
    //     // Don't show error toast for initial load failure, but log it
    //     handleGlobalError(error as ApiError);
    //   }
    // };

    // loadDashboards();
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
    console.log("Demo data button clicked");
    setState((prev) => ({
      ...prev,
      uploadStatus: "uploading",
      isLoading: true,
      error: null,
    }));

    try {
      console.log("App: Calling apiService.useDemoData()");

      const response = await apiService.useDemoData();

      console.log("App: Received response:", response);
      console.log("App: Response type:", typeof response);
      console.log("App: Response keys:", Object.keys(response || {}));

      // After loading demo data structure, also fetch sample data to display
      try {
        console.log("App: Fetching sample demo data for display");
        const sampleDataResponse = await apiService.executeSQL(
          `SELECT * FROM ${response.table} LIMIT 100`,
          "Sample demo data"
        );

        setState((prev) => ({
          ...prev,
          uploadStatus: "completed",
          tableInfo: response,
          queryResults: sampleDataResponse, // Add sample data for display
          currentQuery: "Sample demo data",
          currentSQL: `SELECT * FROM ${response.table} LIMIT 100`,
          isLoading: false,
        }));

        console.log("App: State updated with demo data and sample rows");
        addNotification(
          "success",
          "Demo data loaded successfully with sample preview"
        );
      } catch (sampleError) {
        // If sample data fetch fails, still show the table structure
        console.warn(
          "App: Failed to fetch sample data, showing structure only:",
          sampleError
        );
        setState((prev) => ({
          ...prev,
          uploadStatus: "completed",
          tableInfo: response,
          isLoading: false,
        }));
        addNotification("success", "Demo data loaded successfully");
      }
    } catch (error) {
      console.error("App: Demo data error:", error);
      console.error("App: Error type:", typeof error);
      console.error("App: Error details:", JSON.stringify(error, null, 2));

      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as ApiError)?.message || "Unknown error occurred";

      setState((prev) => ({
        ...prev,
        uploadStatus: "error",
        error: errorMessage,
        isLoading: false,
      }));

      addNotification("error", `Failed to load demo data: ${errorMessage}`);
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
  const hasCharts = Boolean(state.currentChart && state.queryResults);

  return (
    <div className="h-screen bg-white">
      {/* Skip link for keyboard navigation */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <ErrorBoundary level="component" onError={handleGlobalError}>
        <AutoHideSidebar
          isVisible={layoutState.sidebarVisible}
          onVisibilityChange={handleSidebarVisibilityChange}
          triggerWidth={LAYOUT_CONFIG.constraints.sidebarTriggerWidth}
          hideDelay={LAYOUT_CONFIG.constraints.sidebarHideDelay}
          sidebarContent={
            <Sidebar
              isCollapsed={false}
              onToggle={() => {}} // Not used in auto-hide mode
              savedDashboards={state.savedDashboards}
              onLoadDashboard={handleLoadDashboard}
              onNewDashboard={handleNewDashboard}
              onSettings={() => setShowSettingsModal(true)}
              currentDashboardId={currentDashboardId}
            />
          }
        >
          {!hasData ? (
            <main id="main-content" role="main" className="h-full">
              <IntroPage
                onFileUpload={handleFileUpload}
                onDemoData={handleDemoData}
                isLoading={state.isLoading}
                error={state.error}
                savedDashboards={state.savedDashboards}
                onLoadDashboard={handleLoadDashboard}
              />
            </main>
          ) : currentBreakpoint === "mobile" ? (
            // Mobile Layout - Use tabs/slide-over interface
            <div className="h-full flex flex-col">
              {/* Mobile Navigation Tabs */}
              <div className="bg-white border-b border-gray-200 flex">
                <button
                  onClick={() => handleMobileViewChange("chat")}
                  className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    mobileView === "chat"
                      ? "text-blue-600 border-blue-600 bg-blue-50"
                      : "text-gray-600 border-transparent hover:text-gray-800 hover:border-gray-300"
                  }`}
                >
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    Chat
                  </span>
                </button>
                <button
                  onClick={() => handleMobileViewChange("data")}
                  className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    mobileView === "data"
                      ? "text-blue-600 border-blue-600 bg-blue-50"
                      : "text-gray-600 border-transparent hover:text-gray-800 hover:border-gray-300"
                  }`}
                >
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                    Data
                  </span>
                </button>
                {hasCharts && (
                  <button
                    onClick={() => handleMobileViewChange("dashboard")}
                    className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                      mobileView === "dashboard"
                        ? "text-blue-600 border-blue-600 bg-blue-50"
                        : "text-gray-600 border-transparent hover:text-gray-800 hover:border-gray-300"
                    }`}
                  >
                    <span className="flex items-center justify-center gap-2">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                        />
                      </svg>
                      Charts
                    </span>
                  </button>
                )}
              </div>

              {/* Mobile Content */}
              <main
                id="main-content"
                role="main"
                className="flex-1 overflow-hidden"
              >
                {mobileView === "chat" ? (
                  <ConversationPane
                    messages={messages}
                    onSendMessage={handleQuery}
                    isLoading={state.isLoading}
                  />
                ) : (
                  <DashboardWorkspace
                    tableInfo={state.tableInfo!}
                    queryResults={state.queryResults}
                    currentChart={state.currentChart}
                    currentQuery={state.currentQuery}
                    onSaveDashboard={handleSaveDashboard}
                    isLoading={state.isLoading}
                    currentView={
                      mobileView === "dashboard" ? "dashboard" : "data"
                    }
                    onViewChange={handleViewChange}
                  />
                )}
              </main>
            </div>
          ) : (
            // Desktop/Tablet Layout - Use ResizableLayout
            <ResizableLayout
              initialChatWidth={layoutState.chatPaneWidth}
              onResize={handlePaneResize}
              minChatWidth={LAYOUT_CONFIG.constraints.minChatWidth}
              maxChatWidth={LAYOUT_CONFIG.constraints.maxChatWidth}
              chatContent={
                <ConversationPane
                  messages={messages}
                  onSendMessage={handleQuery}
                  isLoading={state.isLoading}
                />
              }
              dashboardContent={
                <main id="main-content" role="main" className="h-full">
                  <DashboardWorkspace
                    tableInfo={state.tableInfo!}
                    queryResults={state.queryResults}
                    currentChart={state.currentChart}
                    currentQuery={state.currentQuery}
                    onSaveDashboard={handleSaveDashboard}
                    isLoading={state.isLoading}
                    currentView={layoutState.currentView}
                    onViewChange={handleViewChange}
                  />
                </main>
              }
            />
          )}
        </AutoHideSidebar>
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

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        currentLayoutState={layoutState}
        onLayoutReset={handleResetLayoutPreferences}
        onAllLayoutReset={handleResetAllLayoutPreferences}
      />

      {/* Toast Notifications */}
      <ToastContainer
        notifications={notifications}
        onDismiss={removeNotification}
      />
    </div>
  );
}

export default App;
