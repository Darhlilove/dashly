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
}
