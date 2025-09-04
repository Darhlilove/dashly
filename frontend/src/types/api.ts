// API Response Types for dashly backend integration

export interface UploadResponse {
  table: string;
  columns: Array<{ name: string; type: string }>;
  suggested_questions?: string[];
  sample_rows?: any[][]; // Sample data for immediate display
  total_rows?: number; // Total number of rows in the table
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

// Enhanced error interface for automatic execution
export interface ExecutionError extends ApiError {
  phase: "translation" | "execution" | "network";
  originalError: ApiError;
  userFriendlyMessage: string;
  suggestions: string[];
  retryable: boolean;
  recoveryActions?: RecoveryAction[];
}

// Recovery action interface for error handling
export interface RecoveryAction {
  type: "retry" | "rephrase" | "simplify" | "contact_support";
  label: string;
  description: string;
  action?: () => void;
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

// Execution state management for automatic execution
export type ExecutionState =
  | { phase: "idle" }
  | { phase: "translating"; query: string }
  | { phase: "translated"; sql: string; query: string }
  | { phase: "executing"; sql: string; query: string }
  | { phase: "completed"; results: ExecuteResponse; sql: string; query: string }
  | { phase: "failed"; error: string; sql?: string; query: string };

// Result type for automatic execution flow
export interface AutomaticExecutionResult {
  translationResult: TranslateResponse;
  executionResult: ExecuteResponse;
  executionTime: number;
  fromCache: boolean;
}

// Chat API Types
export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ConversationalResponse {
  message: string;
  chart_config?: any; // Will be typed as ChartConfig from chart.ts when imported
  insights: string[];
  follow_up_questions: string[];
  processing_time_ms: number;
  conversation_id: string;
}

// ChartConfig moved to chart.ts to avoid conflicts

// Chat Error Types
export interface ChatError extends ApiError {
  suggestions: string[];
  alternative_questions?: string[];
  error_type:
    | "no_data"
    | "column_not_found"
    | "syntax_error"
    | "timeout"
    | "connection_error"
    | "general";
}

// Conversation History Types
export interface ConversationMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata?: {
    insights?: string[];
    follow_up_questions?: string[];
    chart_config?: any; // Will be typed as ChartConfig from chart.ts when imported
    processing_time_ms?: number;
  };
}

export interface ConversationHistory {
  conversation_id: string;
  messages: ConversationMessage[];
}

export interface ConversationContext {
  conversation_id: string;
  context: {
    recent_messages: ConversationMessage[];
    user_questions: string[];
    assistant_responses: string[];
    topics: string[];
    conversation_length: number;
  };
}

export interface ConversationSummary {
  id: string;
  message_count: number;
  created_at: string | null;
  last_updated: string | null;
  first_question: string | null;
}
