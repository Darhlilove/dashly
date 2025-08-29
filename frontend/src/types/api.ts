// API Response Types for dashly backend integration

export interface UploadResponse {
  table: string;
  columns: Array<{ name: string; type: string }>;
}

export interface TranslateResponse {
  sql: string;
}

export interface ExecuteResponse {
  columns: string[];
  rows: any[][];
  row_count: number;
  runtime_ms: number;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
  retryable?: boolean;
  timestamp?: string;
  requestId?: string;
}

export interface RetryableError extends ApiError {
  retryable: true;
  retryAfter?: number; // seconds to wait before retry
  maxRetries?: number;
}

export interface NetworkError extends ApiError {
  code: "NETWORK_ERROR" | "TIMEOUT_ERROR" | "CONNECTION_ERROR";
  retryable: true;
}

export interface ValidationError extends ApiError {
  code:
    | "VALIDATION_ERROR"
    | "INVALID_FILE_TYPE"
    | "FILE_TOO_LARGE"
    | "EMPTY_QUERY"
    | "INVALID_SQL";
  retryable: false;
  fieldErrors?: Record<string, string[]>;
}

export interface ServerError extends ApiError {
  code: "INTERNAL_ERROR" | "SERVICE_UNAVAILABLE" | "DATABASE_ERROR";
  retryable: boolean;
}
