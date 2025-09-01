// Enhanced error handling utilities for automatic execution

import { ApiError, ExecutionError, RecoveryAction } from "../types/api";
import { ErrorMessage } from "../types/ui";
import { generateId } from "./index";

// Error message templates for different error types
const ERROR_TEMPLATES = {
  // Translation errors
  EMPTY_QUERY: {
    userFriendly: "I need a question to help you with your data.",
    suggestions: [
      "Try asking something like 'Show me sales by month'",
      "Ask about trends, totals, or comparisons in your data",
      "Be specific about what you want to see",
    ],
  },
  TRANSLATION_FAILED: {
    userFriendly:
      "I couldn't understand your question well enough to create a query.",
    suggestions: [
      "Try rephrasing your question more simply",
      "Be more specific about what data you want to see",
      "Use simpler language and avoid complex requests",
      "Ask about one thing at a time",
    ],
  },
  INVALID_QUERY_STRUCTURE: {
    userFriendly: "Your question is too complex for me to translate right now.",
    suggestions: [
      "Break your question into smaller parts",
      "Ask about one metric or dimension at a time",
      "Use simpler language",
      "Try asking 'Show me...' or 'What is...'",
    ],
  },

  // Execution errors
  INVALID_SQL: {
    userFriendly: "The query I generated has a syntax error.",
    suggestions: [
      "Try rephrasing your question differently",
      "Ask about the data in a simpler way",
      "Check if the column names in your question match your data",
    ],
  },
  COLUMN_NOT_FOUND: {
    userFriendly:
      "I couldn't find a column that matches what you're asking about.",
    suggestions: [
      "Check the spelling of column names in your question",
      "Try using different words to describe what you want",
      "Ask 'What columns are available?' to see your data structure",
    ],
  },
  TIMEOUT_ERROR: {
    userFriendly: "Your query is taking too long to run.",
    suggestions: [
      "Try asking for a smaller subset of data",
      "Add filters to limit the results (like 'last 30 days')",
      "Ask for summary data instead of detailed records",
    ],
  },
  PERMISSION_DENIED: {
    userFriendly:
      "I don't have permission to access the data you're asking about.",
    suggestions: [
      "Try asking about different data",
      "Contact your administrator for access",
      "Check if you're asking about the right dataset",
    ],
  },

  // Network errors
  NETWORK_ERROR: {
    userFriendly: "I'm having trouble connecting to the server.",
    suggestions: [
      "Check your internet connection",
      "Try again in a few moments",
      "Refresh the page if the problem continues",
    ],
  },
  SERVICE_UNAVAILABLE: {
    userFriendly: "The service is temporarily unavailable.",
    suggestions: [
      "Try again in a few minutes",
      "The system might be under maintenance",
      "Contact support if this continues",
    ],
  },

  // Generic fallback
  UNKNOWN_ERROR: {
    userFriendly: "Something unexpected happened.",
    suggestions: [
      "Try rephrasing your question",
      "Refresh the page and try again",
      "Contact support if this keeps happening",
    ],
  },
};

// Generate user-friendly error message from API error
export function createUserFriendlyError(
  error: ApiError,
  phase: "translation" | "execution" | "network",
  query?: string
): ExecutionError {
  const errorCode = error.code || "UNKNOWN_ERROR";
  const template =
    ERROR_TEMPLATES[errorCode as keyof typeof ERROR_TEMPLATES] ||
    ERROR_TEMPLATES.UNKNOWN_ERROR;

  // Enhance suggestions based on context
  let contextualSuggestions = [...template.suggestions];

  if (phase === "translation" && query) {
    if (query.length > 100) {
      contextualSuggestions.unshift(
        "Your question is quite long - try making it shorter"
      );
    }
    if (query.includes("and") || query.includes("or")) {
      contextualSuggestions.unshift(
        "Try asking about one thing at a time instead of multiple things"
      );
    }
  }

  // Generate recovery actions
  const recoveryActions: RecoveryAction[] = [];

  if (error.retryable) {
    recoveryActions.push({
      type: "retry",
      label: "Try Again",
      description: "Retry the same query",
    });
  }

  recoveryActions.push({
    type: "rephrase",
    label: "Rephrase Question",
    description: "Ask your question in a different way",
  });

  if (phase === "translation") {
    recoveryActions.push({
      type: "simplify",
      label: "Ask Something Simpler",
      description: "Start with a basic question about your data",
    });
  }

  if (!error.retryable || errorCode === "UNKNOWN_ERROR") {
    recoveryActions.push({
      type: "contact_support",
      label: "Get Help",
      description: "Contact support for assistance",
    });
  }

  return {
    ...error,
    phase,
    originalError: error,
    userFriendlyMessage: template.userFriendly,
    suggestions: contextualSuggestions,
    retryable: error.retryable || false,
    recoveryActions,
  };
}

// Create error message for conversation display
export function createErrorMessage(
  executionError: ExecutionError,
  query?: string
): ErrorMessage {
  return {
    id: generateId(),
    type: "assistant",
    content: executionError.userFriendlyMessage,
    timestamp: new Date(),
    isError: true,
    errorPhase: executionError.phase,
    originalError: executionError.originalError.message,
    userFriendlyMessage: executionError.userFriendlyMessage,
    suggestions: executionError.suggestions,
    retryable: executionError.retryable,
    recoveryActions: executionError.recoveryActions,
    errorCode: executionError.code,
  };
}

// Enhanced error message formatting for different error codes
export function enhanceErrorMessage(
  error: ApiError,
  context?: { query?: string; phase?: string }
): string {
  const { code, message } = error;
  const query = context?.query;
  const phase = context?.phase;

  // SQL-specific error enhancements
  if (
    code === "INVALID_SQL" ||
    message.toLowerCase().includes("syntax error")
  ) {
    return "I generated invalid SQL. This usually happens when the question is ambiguous or uses terms I don't recognize.";
  }

  if (
    message.toLowerCase().includes("column") &&
    message.toLowerCase().includes("not found")
  ) {
    const columnMatch = message.match(/'([^']+)'/);
    const columnName = columnMatch ? columnMatch[1] : "requested column";
    return `I couldn't find a column called "${columnName}" in your data. Check the spelling or try describing it differently.`;
  }

  if (message.toLowerCase().includes("timeout") || code === "TIMEOUT_ERROR") {
    return "Your query is taking too long to run. Try asking for less data or add filters to narrow down the results.";
  }

  // Translation-specific error enhancements
  if (phase === "translation") {
    if (
      message.toLowerCase().includes("understand") ||
      message.toLowerCase().includes("parse")
    ) {
      return "I couldn't understand your question well enough to create a database query.";
    }

    if (query && query.length < 5) {
      return "Your question is too short. Try being more specific about what you want to see.";
    }
  }

  // Network error enhancements
  if (code === "NETWORK_ERROR" || message.toLowerCase().includes("network")) {
    return "I'm having trouble connecting to the server. Please check your internet connection.";
  }

  if (code === "TIMEOUT_ERROR" || message.toLowerCase().includes("timeout")) {
    return "The request timed out. The server might be busy - try again in a moment.";
  }

  // Rate limiting
  if (
    code === "RATE_LIMIT_ERROR" ||
    message.toLowerCase().includes("rate limit")
  ) {
    return "You're asking questions too quickly. Please wait a moment before trying again.";
  }

  // File upload errors
  if (code === "FILE_TOO_LARGE") {
    return "Your file is too large. Please upload a smaller CSV file (under 10MB).";
  }

  if (code === "INVALID_FILE_TYPE") {
    return "Please upload a CSV file. Other file types aren't supported yet.";
  }

  // Generic enhancement - make technical errors more user-friendly
  if (
    message.toLowerCase().includes("500") ||
    message.toLowerCase().includes("internal server")
  ) {
    return "Something went wrong on our end. Please try again in a moment.";
  }

  if (
    message.toLowerCase().includes("400") ||
    message.toLowerCase().includes("bad request")
  ) {
    return "There was a problem with your request. Try rephrasing your question.";
  }

  // Return enhanced message or fall back to original
  return message.length > 100
    ? "Something went wrong. Please try rephrasing your question or try again."
    : message;
}

// Generate contextual suggestions based on error and query
export function generateContextualSuggestions(
  error: ApiError,
  query?: string,
  phase?: "translation" | "execution" | "network"
): string[] {
  const suggestions: string[] = [];
  const errorCode = error.code || "";
  const message = error.message.toLowerCase();

  // Phase-specific suggestions
  if (phase === "translation") {
    if (query) {
      if (query.length > 100) {
        suggestions.push("Try making your question shorter and more focused");
      }
      if (query.includes("?")) {
        suggestions.push(
          "Remove question marks - just describe what you want to see"
        );
      }
      if (query.split(" ").length > 20) {
        suggestions.push("Break your question into smaller, simpler parts");
      }
    }

    suggestions.push("Try starting with 'Show me...' or 'What is...'");
    suggestions.push("Ask about one thing at a time");
    suggestions.push("Use simple, everyday language");
  }

  if (phase === "execution") {
    if (message.includes("column")) {
      suggestions.push(
        "Check if the column names in your question match your data"
      );
      suggestions.push("Try using different words to describe what you want");
    }

    if (message.includes("timeout") || errorCode === "TIMEOUT_ERROR") {
      suggestions.push("Ask for a smaller amount of data");
      suggestions.push("Add time filters like 'last 30 days' or 'this year'");
      suggestions.push(
        "Try asking for summary data instead of detailed records"
      );
    }

    suggestions.push("Try rephrasing your question");
    suggestions.push("Ask about your data in a simpler way");
  }

  if (phase === "network") {
    suggestions.push("Check your internet connection");
    suggestions.push("Try again in a few moments");
    suggestions.push("Refresh the page if the problem continues");
  }

  // Error-specific suggestions
  if (errorCode === "RATE_LIMIT_ERROR") {
    suggestions.push("Wait a moment before asking another question");
    suggestions.push("Try asking fewer questions at once");
  }

  if (message.includes("permission") || message.includes("access")) {
    suggestions.push("Contact your administrator for access");
    suggestions.push("Try asking about different data");
  }

  // Generic fallback suggestions
  if (suggestions.length === 0) {
    suggestions.push("Try rephrasing your question");
    suggestions.push("Ask something simpler about your data");
    suggestions.push("Refresh the page and try again");
  }

  return suggestions.slice(0, 4); // Limit to 4 suggestions max
}

// Check if error should trigger automatic retry
export function shouldAutoRetry(error: ApiError, retryCount: number): boolean {
  const maxRetries = 2;

  if (retryCount >= maxRetries) {
    return false;
  }

  // Auto-retry for network errors
  if (error.code === "NETWORK_ERROR" || error.code === "TIMEOUT_ERROR") {
    return true;
  }

  // Auto-retry for server errors
  if (error.code === "INTERNAL_ERROR" || error.code === "SERVICE_UNAVAILABLE") {
    return true;
  }

  // Don't auto-retry for validation errors
  if (error.code === "VALIDATION_ERROR" || error.code === "INVALID_SQL") {
    return false;
  }

  return error.retryable || false;
}

// Calculate retry delay with exponential backoff
export function calculateRetryDelay(
  retryCount: number,
  baseDelay: number = 1000
): number {
  return Math.min(baseDelay * Math.pow(2, retryCount), 10000); // Max 10 seconds
}
