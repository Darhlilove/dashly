// API Service Layer with Axios configuration and error handling

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from "axios";
import {
  UploadResponse,
  TranslateResponse,
  ExecuteResponse,
  ApiError,
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

      switch (status) {
        case 400:
          message =
            responseData?.message ||
            responseData?.detail ||
            "Invalid request. Please check your input.";
          code = "VALIDATION_ERROR";
          retryable = false;
          break;
        case 401:
          message = "Authentication required. Please log in.";
          code = "AUTHENTICATION_ERROR";
          retryable = false;
          break;
        case 403:
          message =
            "Access denied. You don't have permission to perform this action.";
          code = "AUTHORIZATION_ERROR";
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
          message =
            responseData?.message ||
            responseData?.detail ||
            "Invalid data format.";
          code = "VALIDATION_ERROR";
          retryable = false;
          break;
        case 429:
          message = "Too many requests. Please wait a moment and try again.";
          code = "RATE_LIMIT_ERROR";
          retryable = true;
          break;
        case 500:
          message = "Internal server error. Please try again later.";
          code = "INTERNAL_ERROR";
          retryable = true;
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
          message =
            responseData?.message ||
            responseData?.detail ||
            `Server error: ${status}`;
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
          message:
            "Request timeout. Please check your connection and try again.",
          code: "TIMEOUT_ERROR",
          retryable: true,
          timestamp,
          requestId,
        };
      }

      return {
        message:
          "Network error: Unable to connect to server. Please check your internet connection.",
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

  // Use demo data with retry logic
  async useDemoData(): Promise<UploadResponse> {
    return this.retryRequest(async () => {
      const formData = new FormData();
      formData.append("use_demo", "true");

      const response = await this.client.post<UploadResponse>(
        "/upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      return response.data;
    });
  }

  // Translate natural language to SQL with retry logic
  translateQuery = measurePerformance("api_translateQuery", async (query: string): Promise<TranslateResponse> => {
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
  });

  // Execute SQL query with retry logic and caching
  executeSQL = measurePerformance("api_executeSQL", async (sql: string, question?: string): Promise<ExecuteResponse> => {
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
  });
  }

  // Save dashboard configuration with retry logic
  async saveDashboard(
    dashboard: Omit<Dashboard, "id" | "createdAt">
  ): Promise<Dashboard> {
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

  // Get saved dashboards with retry logic and caching
  async getDashboards(): Promise<Dashboard[]> {
    // Check cache first
    const cached = sessionCache.getCachedDashboards();
    if (cached) {
      console.log("Using cached dashboards");
      return cached;
    }

    return this.retryRequest(async () => {
      const response = await this.client.get<Dashboard[]>("/dashboards");

      // Cache the result
      sessionCache.cacheDashboards(response.data);

      return response.data;
    });
  }

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
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
