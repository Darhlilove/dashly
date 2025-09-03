// API Service Layer with Axios configuration and error handling

import axios, { AxiosInstance, AxiosError } from "axios";
import {
  UploadResponse,
  TranslateResponse,
  ExecuteResponse,
  ApiError,
  AutomaticExecutionResult,
  ExecutionError,
  ChatRequest,
  ConversationalResponse,
  ConversationHistory,
  ConversationContext,
  ConversationSummary,
} from "../types/api";
import { Dashboard } from "../types/dashboard";
import { sessionCache } from "../utils/cache";
import { measurePerformance } from "../utils/performance";

interface RetryConfig {
  retries: number;
  retryDelay: number;
  retryCondition?: (error: AxiosError) => boolean;
  onRetry?: (attempt: number, error: AxiosError) => void;
}

class ApiService {
  private client: AxiosInstance;
  private defaultRetryConfig: RetryConfig = {
    retries: 3,
    retryDelay: 1000,
    retryCondition: (error: AxiosError) => {
      // Retry on network errors or 5xx server errors
      return (
        !error.response ||
        (error.response.status >= 500 && error.response.status < 600)
      );
    },
  };

  constructor() {
    this.client = axios.create({
      baseURL: "/api",
      timeout: 30000, // 30 second timeout
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(
          `API Request: ${config.method?.toUpperCase()} ${config.url}`
        );
        return config;
      },
      (error) => {
        console.error("API Request Error:", error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error: AxiosError) => {
        const apiError = this.handleError(error);
        console.error("API Response Error:", apiError);
        return Promise.reject(apiError);
      }
    );
  }

  private handleError(error: AxiosError): ApiError {
    const timestamp = new Date().toISOString();
    const requestId =
      error.response?.headers?.["x-request-id"] ||
      error.config?.headers?.["x-request-id"] ||
      `req_${Date.now()}`;

    if (error.response) {
      // Server responded with error status
      const responseData = error.response.data as any;
      const status = error.response.status;

      let message: string;
      let retryable = false;
      let code: string;

      // Enhanced error detection for SQL and translation errors
      const errorText = responseData?.message || responseData?.detail || "";
      const isColumnError =
        errorText.toLowerCase().includes("column") &&
        (errorText.toLowerCase().includes("not found") ||
          errorText.toLowerCase().includes("does not exist"));
      const isSyntaxError =
        errorText.toLowerCase().includes("syntax error") ||
        errorText.toLowerCase().includes("invalid sql");
      const isTimeoutError =
        errorText.toLowerCase().includes("timeout") ||
        errorText.toLowerCase().includes("time limit");

      switch (status) {
        case 400:
          if (isColumnError) {
            message = errorText;
            code = "COLUMN_NOT_FOUND";
            retryable = false;
          } else if (isSyntaxError) {
            message = errorText;
            code = "INVALID_SQL";
            retryable = false;
          } else {
            message = errorText || "Invalid request. Please check your input.";
            code = "VALIDATION_ERROR";
            retryable = false;
          }
          break;
        case 401:
          message = "Authentication required. Please log in.";
          code = "AUTHENTICATION_ERROR";
          retryable = false;
          break;
        case 403:
          message =
            "Access denied. You don't have permission to perform this action.";
          code = "PERMISSION_DENIED";
          retryable = false;
          break;
        case 404:
          message = "The requested resource was not found.";
          code = "NOT_FOUND_ERROR";
          retryable = false;
          break;
        case 413:
          message = "File too large. Please upload a smaller file.";
          code = "FILE_TOO_LARGE";
          retryable = false;
          break;
        case 415:
          message = "Unsupported file type. Please upload a CSV file.";
          code = "INVALID_FILE_TYPE";
          retryable = false;
          break;
        case 422:
          if (isSyntaxError) {
            message = this.getUserFriendlyMessage(errorText, "sql_error");
            code = "INVALID_SQL";
            retryable = false;
          } else if (errorText.toLowerCase().includes("translation")) {
            message = this.getUserFriendlyMessage(
              errorText,
              "translation_error"
            );
            code = "TRANSLATION_FAILED";
            retryable = false;
          } else {
            message = errorText || "Invalid data format.";
            code = "VALIDATION_ERROR";
            retryable = false;
          }
          break;
        case 429:
          message = "Too many requests. Please wait a moment and try again.";
          code = "RATE_LIMIT_ERROR";
          retryable = true;
          break;
        case 500:
          if (isTimeoutError) {
            message = "Query timeout. The query is taking too long to execute.";
            code = "TIMEOUT_ERROR";
            retryable = false;
          } else {
            message = "Internal server error. Please try again later.";
            code = "INTERNAL_ERROR";
            retryable = true;
          }
          break;
        case 502:
          message = "Service temporarily unavailable. Please try again.";
          code = "SERVICE_UNAVAILABLE";
          retryable = true;
          break;
        case 503:
          message = "Service unavailable. Please try again later.";
          code = "SERVICE_UNAVAILABLE";
          retryable = true;
          break;
        case 504:
          message = "Request timeout. Please try again.";
          code = "TIMEOUT_ERROR";
          retryable = true;
          break;
        default:
          message = errorText || `Server error: ${status}`;
          code = `HTTP_${status}`;
          retryable = status >= 500;
      }

      return {
        message,
        code,
        details: error.response.data,
        retryable,
        timestamp,
        requestId,
      };
    } else if (error.request) {
      // Request made but no response received
      if (error.code === "ECONNABORTED") {
        return {
          message: this.getUserFriendlyMessage("", "timeout_error"),
          code: "TIMEOUT_ERROR",
          retryable: true,
          timestamp,
          requestId,
        };
      }

      return {
        message: this.getUserFriendlyMessage("", "network_error"),
        code: "NETWORK_ERROR",
        retryable: true,
        timestamp,
        requestId,
      };
    } else {
      // Something else happened
      return {
        message: error.message || "An unexpected error occurred",
        code: "UNKNOWN_ERROR",
        retryable: false,
        timestamp,
        requestId,
      };
    }
  }

  // Helper method to convert technical errors to user-friendly messages
  private getUserFriendlyMessage(errorText: string, errorType: string): string {
    const lowerError = errorText.toLowerCase();

    switch (errorType) {
      case "sql_error":
        if (
          lowerError.includes("column") &&
          (lowerError.includes("not found") ||
            lowerError.includes("does not exist"))
        ) {
          return "The data doesn't contain a column mentioned in your question. Try asking about different fields or check what data is available.";
        }
        if (lowerError.includes("syntax error")) {
          return "There was an issue with the generated query. Try rephrasing your question in simpler terms.";
        }
        if (lowerError.includes("table") && lowerError.includes("not found")) {
          return "The data table couldn't be found. Make sure you've uploaded data first.";
        }
        return "There was an issue with your query. Try asking in a different way or be more specific about what you want to see.";

      case "translation_error":
        if (lowerError.includes("understand") || lowerError.includes("parse")) {
          return "I couldn't understand your question. Try using simpler language or be more specific about what data you want to see.";
        }
        if (lowerError.includes("ambiguous")) {
          return "Your question could mean several things. Try being more specific about what you want to analyze.";
        }
        return "I had trouble translating your question. Try rephrasing it or asking about specific data fields.";

      case "network_error":
        return "Connection issue. Please check your internet connection and try again.";

      case "timeout_error":
        return "The request is taking too long. Try asking a simpler question or check your connection.";

      default:
        return errorText || "Something went wrong. Please try again.";
    }
  }

  private async delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private async retryRequest<T>(
    requestFn: () => Promise<T>,
    config: Partial<RetryConfig> = {}
  ): Promise<T> {
    const retryConfig = { ...this.defaultRetryConfig, ...config };
    let lastError: any;

    for (let attempt = 0; attempt <= retryConfig.retries; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;

        // Don't retry on the last attempt
        if (attempt === retryConfig.retries) {
          break;
        }

        // Check if we should retry this error
        if (
          retryConfig.retryCondition &&
          !retryConfig.retryCondition(error as AxiosError)
        ) {
          break;
        }

        // Call retry callback if provided
        if (retryConfig.onRetry) {
          retryConfig.onRetry(attempt + 1, error as AxiosError);
        }

        // Wait before retrying with exponential backoff
        const delayMs = retryConfig.retryDelay * Math.pow(2, attempt);
        console.log(
          `API request failed, retrying in ${delayMs}ms (attempt ${
            attempt + 1
          }/${retryConfig.retries + 1})`
        );
        await this.delay(delayMs);
      }
    }

    throw lastError;
  }

  // Upload CSV file with retry logic
  async uploadFile(file: File): Promise<UploadResponse> {
    // Validate file before upload
    if (
      !file.type.includes("csv") &&
      !file.name.toLowerCase().endsWith(".csv")
    ) {
      throw {
        message: "Invalid file type. Please upload a CSV file.",
        code: "INVALID_FILE_TYPE",
      } as ApiError;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      throw {
        message: "File too large. Please upload a file smaller than 10MB.",
        code: "FILE_TOO_LARGE",
      } as ApiError;
    }

    return this.retryRequest(
      async () => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await this.client.post<UploadResponse>(
          "/upload",
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
            timeout: 60000, // Longer timeout for file uploads
          }
        );

        return response.data;
      },
      { retries: 2 }
    ); // Fewer retries for uploads
  }

  // Use demo data with comprehensive debugging
  async useDemoData(): Promise<UploadResponse> {
    console.log("API: useDemoData called");

    const requestUrl = "/api/demo";
    const fullUrl = `${window.location.origin}${requestUrl}`;

    console.log("API: Request details:");
    console.log("  - URL:", requestUrl);
    console.log("  - Full URL:", fullUrl);
    console.log("  - Method: POST");
    console.log("  - Headers: Content-Type: application/json");

    try {
      console.log("API: Starting fetch request...");

      const response = await fetch(requestUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // Add explicit timeout
        signal: AbortSignal.timeout(15000),
      });

      console.log("API: Fetch completed!");
      console.log("API: Response status:", response.status);
      console.log("API: Response statusText:", response.statusText);
      console.log("API: Response headers:", response.headers);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("API: Response not ok:", response.status, errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      console.log("API: Parsing JSON response...");
      const data = await response.json();
      console.log("API: JSON parsed successfully:", data);

      return data;
    } catch (error) {
      console.error("API: useDemoData error:", error);

      if (error instanceof Error) {
        if (error.name === "TimeoutError") {
          throw {
            message: "Request timed out after 15 seconds",
            code: "TIMEOUT_ERROR",
          } as ApiError;
        }

        throw {
          message: error.message,
          code: "REQUEST_ERROR",
        } as ApiError;
      }

      throw error;
    }
  }

  // Translate natural language to SQL with retry logic
  translateQuery = measurePerformance(
    "api_translateQuery",
    async (query: string): Promise<TranslateResponse> => {
      if (!query.trim()) {
        throw {
          message: "Please enter a question about your data.",
          code: "EMPTY_QUERY",
        } as ApiError;
      }

      return this.retryRequest(async () => {
        const response = await this.client.post<any>(
          "/query",
          {
            query: query.trim(),
          },
          {
            timeout: 45000, // Longer timeout for LLM processing
          }
        );

        // The /api/query endpoint returns a different format, so we need to adapt it
        return {
          sql: response.data.sql,
        };
      });
    }
  );

  // Execute SQL query with retry logic and caching
  executeSQL = measurePerformance(
    "api_executeSQL",
    async (sql: string, question?: string): Promise<ExecuteResponse> => {
      if (!sql.trim()) {
        throw {
          message: "SQL query cannot be empty.",
          code: "EMPTY_SQL",
        } as ApiError;
      }

      // Check cache first if we have a question context
      if (question) {
        const cached = sessionCache.getCachedQueryResult(sql, question);
        if (cached) {
          console.log("Using cached query result");
          return cached;
        }
      }

      return this.retryRequest(async () => {
        const response = await this.client.post<ExecuteResponse>(
          "/execute",
          {
            sql: sql.trim(),
          },
          {
            timeout: 60000, // Longer timeout for complex queries
          }
        );

        // Cache the result if we have question context
        if (question) {
          sessionCache.cacheQueryResult(sql, question, response.data);
        }

        return response.data;
      });
    }
  );

  // Execute query automatically: translate and execute in one flow
  executeQueryAutomatically = measurePerformance(
    "api_executeQueryAutomatically",
    async (query: string): Promise<AutomaticExecutionResult> => {
      if (!query.trim()) {
        throw this.createExecutionError(
          "translation",
          {
            message: "Please enter a question about your data.",
            code: "EMPTY_QUERY",
          } as ApiError,
          "Please enter a question about your data.",
          [
            "Try asking something like 'Show me sales by month'",
            "Ask about trends, comparisons, or summaries in your data",
            "Be specific about what you want to see",
          ]
        );
      }

      const startTime = performance.now();
      const performanceMetrics = {
        cacheCheckTime: 0,
        translationTime: 0,
        executionTime: 0,
        cacheStoreTime: 0,
        totalApiTime: 0,
      };

      let translationResult: TranslateResponse;
      let executionResult: ExecuteResponse;
      let fromCache = false;

      try {
        // Step 1: Check cache first for the complete query with performance tracking
        const cacheCheckStart = performance.now();
        const cached = sessionCache.getCachedQueryResult("", query);
        performanceMetrics.cacheCheckTime = performance.now() - cacheCheckStart;

        if (cached) {
          console.log("🚀 API: Using cached automatic execution result");
          performanceMetrics.totalApiTime = performance.now() - startTime;

          // Log API performance for cached result
          console.log(
            `📊 API Cache Performance: ${performanceMetrics.cacheCheckTime.toFixed(
              2
            )}ms check, ${performanceMetrics.totalApiTime.toFixed(2)}ms total`
          );

          // For cached results, we need to reconstruct the translation result
          // This is a limitation of the current cache structure
          return {
            translationResult: { sql: "-- Cached result --" },
            executionResult: cached,
            executionTime: performanceMetrics.totalApiTime,
            fromCache: true,
          };
        }

        // Step 2: Translate natural language to SQL with performance tracking
        try {
          const translationStart = performance.now();
          translationResult = await this.translateQuery(query);
          performanceMetrics.translationTime =
            performance.now() - translationStart;
        } catch (error) {
          throw this.createExecutionError(
            "translation",
            error as ApiError,
            "I couldn't understand your question. Could you try rephrasing it?",
            [
              "Try using simpler language",
              "Be more specific about what data you want to see",
              "Check if your question relates to the uploaded data",
              "Example: 'Show me total sales by month'",
            ]
          );
        }

        // Step 3: Execute the generated SQL with performance tracking
        try {
          const executionStart = performance.now();
          executionResult = await this.executeSQL(translationResult.sql, query);
          performanceMetrics.executionTime = performance.now() - executionStart;
        } catch (error) {
          throw this.createExecutionError(
            "execution",
            error as ApiError,
            "There was a problem running your query. The data might not contain what you're looking for.",
            [
              "Try asking about different columns or data",
              "Check if the data contains the information you're looking for",
              "Try a simpler question first",
              "Make sure your question matches the available data",
            ]
          );
        }

        // Step 4: Cache the successful result with performance tracking
        const cacheStoreStart = performance.now();
        sessionCache.cacheQueryResult(
          translationResult.sql,
          query,
          executionResult
        );
        performanceMetrics.cacheStoreTime = performance.now() - cacheStoreStart;

        performanceMetrics.totalApiTime = performance.now() - startTime;

        // Log comprehensive API performance metrics
        console.group("🔧 API Automatic Execution Performance");
        console.log(
          `🗄️  Cache check: ${performanceMetrics.cacheCheckTime.toFixed(2)}ms`
        );
        console.log(
          `🔤 Translation: ${performanceMetrics.translationTime.toFixed(2)}ms`
        );
        console.log(
          `⚡ SQL execution: ${performanceMetrics.executionTime.toFixed(2)}ms`
        );
        console.log(
          `💾 Cache store: ${performanceMetrics.cacheStoreTime.toFixed(2)}ms`
        );
        console.log(
          `🏁 Total API time: ${performanceMetrics.totalApiTime.toFixed(2)}ms`
        );
        console.log(`📋 Rows returned: ${executionResult.row_count}`);
        console.log(`⏱️  Backend execution: ${executionResult.runtime_ms}ms`);

        // Performance analysis
        const backendVsFrontend =
          performanceMetrics.totalApiTime - executionResult.runtime_ms;
        console.log(
          `🔄 Network + processing overhead: ${backendVsFrontend.toFixed(2)}ms`
        );

        if (performanceMetrics.translationTime > 3000) {
          console.warn("⚠️  Slow translation detected in API (>3s)");
        }
        if (performanceMetrics.executionTime > 5000) {
          console.warn("⚠️  Slow execution detected in API (>5s)");
        }
        if (performanceMetrics.cacheStoreTime > 100) {
          console.warn("⚠️  Slow cache store detected (>100ms)");
        }

        console.groupEnd();

        return {
          translationResult,
          executionResult,
          executionTime: performanceMetrics.totalApiTime,
          fromCache,
        };
      } catch (error) {
        // Log error performance
        const errorTime = performance.now() - startTime;
        console.error(`❌ API Error after ${errorTime.toFixed(2)}ms:`, error);

        // If it's already an ExecutionError, re-throw it
        if (this.isExecutionError(error)) {
          throw error;
        }

        // Handle unexpected errors
        throw this.createExecutionError(
          "execution",
          error as ApiError,
          "Something unexpected happened. Please try again.",
          [
            "Try refreshing the page",
            "Check your internet connection",
            "Try a different question",
            "Contact support if the problem persists",
          ]
        );
      }
    }
  );

  // Helper method to create user-friendly execution errors
  private createExecutionError(
    phase: "translation" | "execution" | "network",
    originalError: ApiError,
    userFriendlyMessage: string,
    suggestions: string[]
  ): ExecutionError {
    return {
      phase,
      originalError,
      userFriendlyMessage,
      suggestions,
      message: userFriendlyMessage,
      code: originalError.code || "EXECUTION_ERROR",
      retryable: originalError.retryable || false,
      timestamp: new Date().toISOString(),
      requestId: originalError.requestId || `req_${Date.now()}`,
    };
  }

  // Helper method to check if an error is an ExecutionError
  private isExecutionError(error: any): error is ExecutionError {
    return (
      error &&
      typeof error === "object" &&
      "phase" in error &&
      "userFriendlyMessage" in error
    );
  }

  // Save dashboard configuration with retry logic
  saveDashboard = measurePerformance(
    "api_saveDashboard",
    async (
      dashboard: Omit<Dashboard, "id" | "createdAt">
    ): Promise<Dashboard> => {
      if (!dashboard.name.trim()) {
        throw {
          message: "Dashboard name cannot be empty.",
          code: "EMPTY_NAME",
        } as ApiError;
      }

      return this.retryRequest(async () => {
        const response = await this.client.post<Dashboard>(
          "/dashboards",
          dashboard
        );

        // Clear dashboard cache since we have new data
        sessionCache.clearDashboardCache();

        return response.data;
      });
    }
  );

  // Get saved dashboards with retry logic and caching - TEMPORARILY SIMPLIFIED
  getDashboards = async (): Promise<Dashboard[]> => {
    console.log("getDashboards called (caching temporarily disabled)");

    try {
      const response = await this.client.get<Dashboard[]>("/dashboards");
      console.log("getDashboards response:", response.data);
      return response.data;
    } catch (error) {
      console.error("getDashboards error:", error);
      return []; // Return empty array on error
    }
  };

  // Get dashboard by ID with retry logic
  async getDashboard(id: string): Promise<Dashboard> {
    if (!id.trim()) {
      throw {
        message: "Dashboard ID cannot be empty.",
        code: "EMPTY_ID",
      } as ApiError;
    }

    return this.retryRequest(async () => {
      const response = await this.client.get<Dashboard>(`/dashboards/${id}`);
      return response.data;
    });
  }

  // Chat API Methods
  async sendChatMessage(request: ChatRequest): Promise<ConversationalResponse> {
    if (!request.message.trim()) {
      throw {
        message: "Please enter a message.",
        code: "EMPTY_MESSAGE",
        retryable: false,
      } as ApiError;
    }

    return this.retryRequest(
      async () => {
        const response = await this.client.post<ConversationalResponse>(
          "/chat",
          {
            message: request.message.trim(),
            conversation_id: request.conversation_id,
          },
          {
            timeout: 30000, // 30 second timeout for chat processing
          }
        );

        return response.data;
      },
      {
        retries: 2, // Fewer retries for chat to avoid long waits
        retryCondition: (error: AxiosError) => {
          // Only retry on network errors or 5xx server errors
          // Don't retry on 4xx errors (user input issues)
          return (
            !error.response ||
            (error.response.status >= 500 && error.response.status < 600)
          );
        },
      }
    );
  }

  // Conversation History Management Methods
  async getConversationHistory(
    conversationId: string
  ): Promise<ConversationHistory> {
    if (!conversationId.trim()) {
      throw {
        message: "Conversation ID cannot be empty.",
        code: "EMPTY_CONVERSATION_ID",
        retryable: false,
      } as ApiError;
    }

    return this.retryRequest(async () => {
      const response = await this.client.get<ConversationHistory>(
        `/conversations/${conversationId}/history`
      );
      return response.data;
    });
  }

  async getConversationContext(
    conversationId: string
  ): Promise<ConversationContext> {
    if (!conversationId.trim()) {
      throw {
        message: "Conversation ID cannot be empty.",
        code: "EMPTY_CONVERSATION_ID",
        retryable: false,
      } as ApiError;
    }

    return this.retryRequest(async () => {
      const response = await this.client.get<ConversationContext>(
        `/conversations/${conversationId}/context`
      );
      return response.data;
    });
  }

  async getConversationSummary(
    conversationId: string
  ): Promise<ConversationSummary> {
    if (!conversationId.trim()) {
      throw {
        message: "Conversation ID cannot be empty.",
        code: "EMPTY_CONVERSATION_ID",
        retryable: false,
      } as ApiError;
    }

    return this.retryRequest(async () => {
      const response = await this.client.get<ConversationSummary>(
        `/conversations/${conversationId}/summary`
      );
      return response.data;
    });
  }

  async clearConversation(
    conversationId: string
  ): Promise<{ message: string; conversation_id: string }> {
    if (!conversationId.trim()) {
      throw {
        message: "Conversation ID cannot be empty.",
        code: "EMPTY_CONVERSATION_ID",
        retryable: false,
      } as ApiError;
    }

    return this.retryRequest(async () => {
      const response = await this.client.delete<{
        message: string;
        conversation_id: string;
      }>(`/conversations/${conversationId}`);
      return response.data;
    });
  }

  async cleanupExpiredConversations(): Promise<{
    message: string;
    count: number;
  }> {
    return this.retryRequest(async () => {
      const response = await this.client.post<{
        message: string;
        count: number;
      }>(`/conversations/cleanup`);
      return response.data;
    });
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
