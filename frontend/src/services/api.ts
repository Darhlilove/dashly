// API Service Layer with Axios configuration and error handling

import axios, { AxiosInstance, AxiosError } from "axios";
import {
  UploadResponse,
  TranslateResponse,
  ExecuteResponse,
  ApiError,
} from "../types/api";
import { Dashboard } from "../types/dashboard";

class ApiService {
  private client: AxiosInstance;

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
    if (error.response) {
      // Server responded with error status
      const responseData = error.response.data as any;
      const message =
        responseData?.message ||
        responseData?.detail ||
        `Server error: ${error.response.status}`;
      return {
        message,
        code: error.response.status.toString(),
        details: error.response.data,
      };
    } else if (error.request) {
      // Request made but no response received
      return {
        message: "Network error: Unable to connect to server",
        code: "NETWORK_ERROR",
      };
    } else {
      // Something else happened
      return {
        message: error.message || "An unexpected error occurred",
        code: "UNKNOWN_ERROR",
      };
    }
  }

  // Upload CSV file
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

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
  }

  // Use demo data
  async useDemoData(): Promise<UploadResponse> {
    const response = await this.client.post<UploadResponse>("/upload", {
      use_demo: true,
    });

    return response.data;
  }

  // Translate natural language to SQL
  async translateQuery(query: string): Promise<TranslateResponse> {
    const response = await this.client.post<TranslateResponse>("/translate", {
      question: query,
    });

    return response.data;
  }

  // Execute SQL query
  async executeSQL(sql: string): Promise<ExecuteResponse> {
    const response = await this.client.post<ExecuteResponse>("/execute", {
      sql,
    });

    return response.data;
  }

  // Save dashboard configuration
  async saveDashboard(
    dashboard: Omit<Dashboard, "id" | "createdAt">
  ): Promise<Dashboard> {
    const response = await this.client.post<Dashboard>(
      "/dashboards",
      dashboard
    );

    return response.data;
  }

  // Get saved dashboards
  async getDashboards(): Promise<Dashboard[]> {
    const response = await this.client.get<Dashboard[]>("/dashboards");

    return response.data;
  }

  // Get dashboard by ID
  async getDashboard(id: string): Promise<Dashboard> {
    const response = await this.client.get<Dashboard>(`/dashboards/${id}`);

    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
