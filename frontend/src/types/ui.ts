// UI component types

export interface Message {
  id: string;
  type: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

export interface SQLMessage extends Message {
  type: "assistant";
  sqlQuery?: string;
  executionStatus?: "pending" | "executing" | "completed" | "failed";
  executionTime?: number;
  rowCount?: number;
}

export interface ExecutionStatusMessage extends Message {
  type: "system";
  status: "executing" | "completed" | "failed";
  details?: {
    executionTime?: number;
    rowCount?: number;
    error?: string;
  };
}

export interface ErrorMessage extends Message {
  type: "assistant";
  isError: true;
  errorPhase: "translation" | "execution" | "network";
  originalError?: string;
  userFriendlyMessage: string;
  suggestions: string[];
  retryable: boolean;
  recoveryActions?: RecoveryAction[];
  errorCode?: string;
}

// Import RecoveryAction from api types
import type { RecoveryAction } from "./api";
