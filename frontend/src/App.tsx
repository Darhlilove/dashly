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
import {
  AppState,
  ToastNotification,
  Dashboard,
  ApiError,
  ExecuteResponse,
  SQLMessage,
  ExecutionStatusMessage,
} from "./types";
import { LayoutState, ViewType } from "./types/layout";
import { apiService } from "./services/api";
import { selectChartType } from "./utils";
import { generateId } from "./utils";
import {
  createUserFriendlyError,
  createErrorMessage,
  enhanceErrorMessage,
  generateContextualSuggestions,
  shouldAutoRetry,
  calculateRetryDelay,
} from "./utils/errorHandling";
import { useErrorHandler } from "./hooks/useErrorHandler";
import { useSessionCache } from "./hooks/useSessionCache";
import { useBreakpoint } from "./hooks/useMediaQuery";
import { useLayoutPreferences } from "./hooks/useLayoutPreferences";
import { useUserPreferences } from "./hooks/useUserPreferences";
import { LAYOUT_CONFIG } from "./config/layout";
import SettingsModal from "./components/SettingsModal";
import { performanceMonitor } from "./utils/performance";
import { usePerformanceMonitor } from "./utils/performanceMonitor";
import { useAutomaticExecutionPerformance } from "./hooks/useAutomaticExecutionPerformance";
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
  // New fields for automatic execution
  executionMode: "automatic", // Default to automatic mode
  isExecutingQuery: false,
  lastExecutionTime: undefined,
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

  // Performance monitoring for App component
  const {
    measureRender,
    measureFunction,
    measureAsync,
    getMetrics,
    getAveragePerformance,
  } = usePerformanceMonitor("App");

  // Automatic execution performance monitoring
  const {
    recordExecution,
    getMetrics: getExecutionMetrics,
    logPerformanceSummary,
    getPerformanceRecommendations,
  } = useAutomaticExecutionPerformance();

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

  // Apply user preferences to document and sync execution mode
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

    // Sync execution mode from user preferences
    const savedExecutionMode = preferences.ui.executionMode;
    if (savedExecutionMode && savedExecutionMode !== state.executionMode) {
      setState((prev) => ({
        ...prev,
        executionMode: savedExecutionMode,
      }));
    }
  }, [userPreferences, currentBreakpoint, state.executionMode]);

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

    // Check execution mode to determine flow
    if (state.executionMode === "automatic") {
      await executeQueryAutomatically(query);
    } else {
      // Advanced mode - show SQL preview modal
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

        // Create enhanced error for translation phase
        const executionError = createUserFriendlyError(
          apiError,
          "translation",
          query
        );

        // Create recovery actions for advanced mode
        const recoveryActions = executionError.recoveryActions?.map(
          (action) => ({
            ...action,
            action: () => {
              switch (action.type) {
                case "retry":
                  if (executionError.retryable) {
                    handleQuery(query);
                  }
                  break;
                case "rephrase":
                  const input = document.querySelector(
                    'input[type="text"]'
                  ) as HTMLInputElement;
                  if (input) {
                    input.focus();
                    input.select();
                  }
                  break;
                case "simplify":
                  const examples = [
                    "Show me all data",
                    "What columns are available?",
                    "Show me the first 10 rows",
                  ];
                  const exampleQuery =
                    examples[Math.floor(Math.random() * examples.length)];
                  handleQuery(exampleQuery);
                  break;
              }
            },
          })
        );

        // Create enhanced error message
        const errorMessage = createErrorMessage(
          {
            ...executionError,
            recoveryActions,
          },
          query
        );

        setMessages((prev) => [...prev, errorMessage]);

        setState((prev) => ({
          ...prev,
          error: apiError.message,
          isLoading: false,
        }));

        addNotification("error", executionError.userFriendlyMessage);
      }
    }
  };

  // Execute query automatically (combines translation and execution)
  const executeQueryAutomatically = async (query: string) => {
    return measureAsync(
      "automaticExecution",
      async () => {
        const startTime = performance.now();
        const pipelineStartTime = Date.now();

        // Performance tracking for automatic execution pipeline
        const performanceMetrics = {
          translationTime: 0,
          cacheCheckTime: 0,
          executionTime: 0,
          chartSelectionTime: 0,
          uiUpdateTime: 0,
          totalPipelineTime: 0,
          fromCache: false,
          rowCount: 0,
          queryLength: query.length,
        };

        setState((prev) => ({
          ...prev,
          isExecutingQuery: true,
        }));

        try {
          // Add initial execution status message
          const executionStatusMessage: ExecutionStatusMessage = {
            id: generateId(),
            type: "system",
            content: "Executing query and generating your dashboard...",
            timestamp: new Date(),
            status: "executing",
          };
          setMessages((prev) => [...prev, executionStatusMessage]);

          // Use the API service's automatic execution method for comprehensive performance tracking
          const automaticExecutionStart = performance.now();
          const automaticResult = await apiService.executeQueryAutomatically(
            query
          );
          const automaticExecutionTime =
            performance.now() - automaticExecutionStart;

          // Extract results from the automatic execution
          const translationResponse = automaticResult.translationResult;
          const executionResponse = automaticResult.executionResult;
          const fromCache = automaticResult.fromCache;

          // Update performance metrics with actual timing
          performanceMetrics.translationTime = automaticExecutionTime * 0.3; // Estimate based on typical breakdown
          performanceMetrics.executionTime = automaticExecutionTime * 0.6; // Estimate based on typical breakdown
          performanceMetrics.cacheCheckTime = automaticExecutionTime * 0.1; // Estimate based on typical breakdown
          performanceMetrics.fromCache = fromCache;

          // Add assistant message showing the generated SQL with executing status
          const sqlMessage: SQLMessage = {
            id: generateId(),
            type: "assistant",
            content: `I've generated this SQL query and executed it:`,
            timestamp: new Date(),
            sqlQuery: translationResponse.sql,
            executionStatus: "executing",
          };
          setMessages((prev) => [...prev, sqlMessage]);

          setState((prev) => ({
            ...prev,
            currentSQL: translationResponse.sql,
          }));

          // Update row count from execution result
          performanceMetrics.rowCount = executionResponse.row_count || 0;

          // Process results and update dashboard with performance tracking
          const chartSelectionStart = performance.now();
          const chartConfig = selectChartType({
            columns: executionResponse.columns,
            rows: executionResponse.rows,
          });
          performanceMetrics.chartSelectionTime =
            performance.now() - chartSelectionStart;

          const uiUpdateStart = performance.now();
          const totalPipelineTime = Date.now() - pipelineStartTime;
          performanceMetrics.totalPipelineTime = totalPipelineTime;

          // Show cache notification if applicable
          if (fromCache) {
            addNotification("info", "Using cached results");
            performanceMonitor.startTimer("cache_hit_processing");
          } else {
            performanceMonitor.startTimer("cache_miss_processing");
          }

          // Add execution completion status message with enhanced performance info
          const completionStatusMessage: ExecutionStatusMessage = {
            id: generateId(),
            type: "system",
            content: `Query executed successfully! Found ${
              executionResponse.row_count
            } rows in ${executionResponse.runtime_ms}ms${
              fromCache ? " (cached result)" : ""
            }${
              performanceMetrics.totalPipelineTime > 2000
                ? ` • Total pipeline: ${(
                    performanceMetrics.totalPipelineTime / 1000
                  ).toFixed(1)}s`
                : ""
            }`,
            timestamp: new Date(),
            status: "completed",
            details: {
              executionTime: executionResponse.runtime_ms,
              rowCount: executionResponse.row_count,
              pipelineTime: performanceMetrics.totalPipelineTime,
              fromCache,
            },
          };
          setMessages((prev) => [...prev, completionStatusMessage]);

          // Add success message with execution details
          const successMessage: SQLMessage = {
            id: generateId(),
            type: "assistant",
            content: `Perfect! I've executed your query and the results are displayed in the dashboard on the right. ${
              fromCache
                ? "This result was retrieved from cache for faster performance."
                : `The query processed ${executionResponse.row_count} rows and completed in ${executionResponse.runtime_ms}ms.`
            }${
              performanceMetrics.totalPipelineTime > 3000
                ? ` The complete pipeline took ${(
                    performanceMetrics.totalPipelineTime / 1000
                  ).toFixed(1)} seconds.`
                : ""
            }`,
            timestamp: new Date(),
            sqlQuery: translationResponse.sql,
            executionStatus: "completed" as const,
            executionTime: executionResponse.runtime_ms,
            rowCount: executionResponse.row_count,
          };
          setMessages((prev) => [...prev, successMessage]);

          setState((prev) => ({
            ...prev,
            queryResults: executionResponse,
            currentChart: chartConfig,
            isLoading: false,
            isExecutingQuery: false,
            lastExecutionTime: totalPipelineTime,
          }));

          performanceMetrics.uiUpdateTime = performance.now() - uiUpdateStart;

          // Log comprehensive performance metrics
          console.group("🚀 Automatic Execution Performance Metrics");
          console.log(
            `📊 Query: "${query.substring(0, 50)}${
              query.length > 50 ? "..." : ""
            }"`
          );
          console.log(
            `⏱️  Translation: ${performanceMetrics.translationTime.toFixed(
              2
            )}ms`
          );
          console.log(
            `🗄️  Cache check: ${performanceMetrics.cacheCheckTime.toFixed(2)}ms`
          );
          console.log(`💾 Cache ${fromCache ? "HIT" : "MISS"}`);
          console.log(
            `⚡ SQL execution: ${performanceMetrics.executionTime.toFixed(2)}ms`
          );
          console.log(
            `📈 Chart selection: ${performanceMetrics.chartSelectionTime.toFixed(
              2
            )}ms`
          );
          console.log(
            `🎨 UI update: ${performanceMetrics.uiUpdateTime.toFixed(2)}ms`
          );
          console.log(
            `🏁 Total pipeline: ${performanceMetrics.totalPipelineTime}ms`
          );
          console.log(`📋 Rows processed: ${performanceMetrics.rowCount}`);
          console.log(
            `📝 Query length: ${performanceMetrics.queryLength} chars`
          );

          // Performance analysis and recommendations
          if (performanceMetrics.totalPipelineTime > 5000) {
            console.warn("⚠️  Slow automatic execution detected (>5s)");
          }
          if (performanceMetrics.translationTime > 2000) {
            console.warn("⚠️  Slow translation detected (>2s)");
          }
          if (performanceMetrics.executionTime > 3000) {
            console.warn("⚠️  Slow SQL execution detected (>3s)");
          }
          if (performanceMetrics.rowCount > 10000 && !fromCache) {
            console.info("💡 Large dataset - consider caching or pagination");
          }

          console.groupEnd();

          // Record performance metrics for monitoring
          performanceMonitor.startTimer("automatic_execution_complete");
          const endTimer = performanceMonitor.endTimer(
            "automatic_execution_complete"
          );

          // End cache processing timer
          if (fromCache) {
            performanceMonitor.endTimer("cache_hit_processing");
          } else {
            performanceMonitor.endTimer("cache_miss_processing");
          }

          addNotification(
            "success",
            `Query executed successfully (${
              executionResponse.row_count
            } rows, ${executionResponse.runtime_ms}ms${
              fromCache ? ", cached" : ""
            })`
          );

          // Record execution performance for monitoring
          recordExecution({
            query,
            executionTime: performanceMetrics.totalPipelineTime,
            success: true,
            fromCache,
            rowCount: performanceMetrics.rowCount,
          });

          // Return performance metrics for potential use by calling code
          return {
            success: true,
            metrics: performanceMetrics,
            result: executionResponse,
          };
        } catch (error) {
          const apiError = error as ApiError;
          const errorTime = Date.now() - pipelineStartTime;

          // Log error performance metrics
          console.group("❌ Automatic Execution Error Metrics");
          console.log(
            `📊 Query: "${query.substring(0, 50)}${
              query.length > 50 ? "..." : ""
            }"`
          );
          console.log(`⏱️  Time to error: ${errorTime}ms`);
          console.log(
            `🔍 Translation time: ${performanceMetrics.translationTime.toFixed(
              2
            )}ms`
          );
          console.log(
            `🗄️  Cache check time: ${performanceMetrics.cacheCheckTime.toFixed(
              2
            )}ms`
          );
          console.log(
            `⚡ Execution time: ${performanceMetrics.executionTime.toFixed(
              2
            )}ms`
          );
          console.log(`❌ Error: ${apiError.message}`);
          console.log(`🔄 Retryable: ${apiError.retryable ? "Yes" : "No"}`);
          console.groupEnd();

          // Record error metrics
          performanceMonitor.startTimer("automatic_execution_error");
          performanceMonitor.endTimer("automatic_execution_error");

          // Determine error phase for better user messaging
          const isTranslationError = !state.currentSQL;
          const errorPhase = isTranslationError ? "translation" : "execution";

          // Create enhanced error with user-friendly messaging and suggestions
          const executionError = createUserFriendlyError(
            apiError,
            errorPhase,
            query
          );

          // Create recovery actions with actual functionality
          const recoveryActions = executionError.recoveryActions?.map(
            (action) => ({
              ...action,
              action: () => {
                switch (action.type) {
                  case "retry":
                    if (executionError.retryable) {
                      handleQuery(query);
                    }
                    break;
                  case "rephrase":
                    // Focus on input to encourage rephrasing
                    const input = document.querySelector(
                      'input[type="text"]'
                    ) as HTMLInputElement;
                    if (input) {
                      input.focus();
                      input.select();
                    }
                    break;
                  case "simplify":
                    // Provide example simple questions
                    const examples = [
                      "Show me all data",
                      "What columns are available?",
                      "Show me the first 10 rows",
                    ];
                    const exampleQuery =
                      examples[Math.floor(Math.random() * examples.length)];
                    handleQuery(exampleQuery);
                    break;
                  case "contact_support":
                    // Could open a support modal or redirect
                    console.log("Contact support action triggered");
                    break;
                }
              },
            })
          );

          // Add execution failure status message with performance context
          const failureStatusMessage: ExecutionStatusMessage = {
            id: generateId(),
            type: "system",
            content: `Query execution failed: ${
              executionError.userFriendlyMessage
            }${
              errorTime > 5000
                ? ` (failed after ${(errorTime / 1000).toFixed(1)}s)`
                : ""
            }`,
            timestamp: new Date(),
            status: "failed",
            details: {
              error: executionError.userFriendlyMessage,
              errorTime,
              phase: errorPhase,
            },
          };
          setMessages((prev) => [...prev, failureStatusMessage]);

          // Create enhanced error message for conversation
          const errorMessage = createErrorMessage(
            {
              ...executionError,
              recoveryActions,
            },
            query
          );

          setMessages((prev) => [...prev, errorMessage]);

          setState((prev) => ({
            ...prev,
            error: apiError.message,
            isLoading: false,
            isExecutingQuery: false,
          }));

          // Enhanced notification with user-friendly message
          addNotification("error", executionError.userFriendlyMessage);

          // Auto-retry logic for retryable errors
          if (shouldAutoRetry(apiError, 0)) {
            const retryDelay = calculateRetryDelay(0);

            // Show retry notification
            addNotification(
              "info",
              `Retrying automatically in ${Math.round(
                retryDelay / 1000
              )} seconds...`
            );

            setTimeout(() => {
              console.log("Auto-retrying query due to retryable error");
              handleQuery(query);
            }, retryDelay);
          }

          // Record error execution performance for monitoring
          recordExecution({
            query,
            executionTime: errorTime,
            success: false,
            fromCache: false,
            rowCount: 0,
            errorPhase,
          });

          // Return error metrics for potential use by calling code
          return {
            success: false,
            metrics: {
              ...performanceMetrics,
              totalPipelineTime: errorTime,
              error: apiError.message,
              errorPhase,
            },
            error: apiError,
          };
        }
      },
      {
        queryLength: query.length,
        executionMode: "automatic",
      }
    );
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

      // Create enhanced error for execution phase
      const executionError = createUserFriendlyError(
        apiError,
        "execution",
        state.currentQuery
      );

      // Create recovery actions for SQL execution
      const recoveryActions = executionError.recoveryActions?.map((action) => ({
        ...action,
        action: () => {
          switch (action.type) {
            case "retry":
              if (executionError.retryable) {
                handleSQLExecution(sql);
              }
              break;
            case "rephrase":
              // Close modal and focus on input for rephrasing
              setState((prev) => ({ ...prev, showSQLModal: false }));
              const input = document.querySelector(
                'input[type="text"]'
              ) as HTMLInputElement;
              if (input) {
                input.focus();
                input.select();
              }
              break;
          }
        },
      }));

      // Create enhanced error message
      const errorMessage = createErrorMessage(
        {
          ...executionError,
          recoveryActions,
        },
        state.currentQuery
      );

      setMessages((prev) => [...prev, errorMessage]);

      setState((prev) => ({
        ...prev,
        error: apiError.message,
        isLoading: false,
      }));

      addNotification("error", executionError.userFriendlyMessage);
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

  // Handle execution mode change
  const handleExecutionModeChange = (mode: "automatic" | "advanced") => {
    setState((prev) => ({
      ...prev,
      executionMode: mode,
    }));

    // Persist the preference
    userPreferences.updateUI({
      executionMode: mode,
    });

    addNotification("info", `Switched to ${mode} execution mode`);
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
                    executionMode={state.executionMode}
                    onExecutionModeChange={handleExecutionModeChange}
                  />
                ) : (
                  <DashboardWorkspace
                    tableInfo={state.tableInfo!}
                    queryResults={state.queryResults}
                    currentChart={state.currentChart}
                    currentQuery={state.currentQuery}
                    onSaveDashboard={handleSaveDashboard}
                    onNewQuery={handleNewDashboard}
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
                  executionMode={state.executionMode}
                  onExecutionModeChange={handleExecutionModeChange}
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
                    onNewQuery={handleNewDashboard}
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

      {/* SQL Preview Modal - Only show in advanced mode */}
      {state.showSQLModal && state.executionMode === "advanced" && (
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

// Global performance monitoring utilities for development and debugging
if (typeof window !== "undefined") {
  // Add performance monitoring to window for debugging
  (window as any).dashlyPerformance = {
    logExecutionSummary: () => {
      console.log("Use the performance summary in the app component");
    },
    logCachePerformance: () => {
      sessionCache.logCachePerformance();
    },
    clearPerformanceHistory: () => {
      performanceMonitor.clearMetrics();
      sessionCache.clearAllCache();
      console.log("🧹 All performance data cleared");
    },
    getPerformanceMetrics: () => {
      return {
        general: performanceMonitor.getMetrics(),
        cache: sessionCache.getCachePerformanceMetrics(),
        cacheStats: sessionCache.getCacheStats(),
      };
    },
  };

  // Log available performance commands
  console.log("🔧 Performance monitoring available:");
  console.log("  window.dashlyPerformance.logCachePerformance()");
  console.log("  window.dashlyPerformance.clearPerformanceHistory()");
  console.log("  window.dashlyPerformance.getPerformanceMetrics()");
}

export default App;
