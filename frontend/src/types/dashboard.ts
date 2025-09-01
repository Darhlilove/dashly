// Dashboard and Application State Types

import { ChartConfig } from "./chart";
import { UploadResponse, ExecuteResponse } from "./api";

export interface Dashboard {
  id: string;
  name: string;
  question: string;
  sql: string;
  chartConfig: ChartConfig;
  createdAt: string;
}

export interface AppState {
  uploadStatus: "idle" | "uploading" | "completed" | "error";
  tableInfo: UploadResponse | null;
  currentQuery: string;
  currentSQL: string;
  queryResults: ExecuteResponse | null;
  currentChart: ChartConfig | null;
  savedDashboards: Dashboard[];
  showSQLModal: boolean;
  isLoading: boolean;
  error: string | null;
  // New fields for automatic execution
  executionMode: "automatic" | "advanced";
  isExecutingQuery: boolean;
  lastExecutionTime?: number;
}

export interface ToastNotification {
  id: string;
  type: "success" | "error" | "info";
  message: string;
  duration?: number;
}
