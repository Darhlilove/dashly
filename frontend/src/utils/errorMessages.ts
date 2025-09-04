// User-friendly error message utilities

import { ApiError } from "../types/api";
import { ErrorMessage } from "../types/ui";
import { RecoveryAction } from "../types/api";

interface ErrorContext {
  hasData?: boolean;
  dataColumns?: string[];
  recentQuestions?: string[];
  userMessage?: string;
}

/**
 * Convert API errors to user-friendly error messages with recovery actions
 */
export function createUserFriendlyError(
  error: ApiError,
  context: ErrorContext = {}
): ErrorMessage {
  const {
    hasData = false,
    dataColumns = [],
    recentQuestions = [],
    userMessage = "",
  } = context;

  // Determine error phase and create appropriate message
  const errorPhase = determineErrorPhase(error);
  const userFriendlyMessage = generateUserFriendlyMessage(error, context);
  const suggestions = generateSuggestions(error, context);
  const recoveryActions = generateRecoveryActions(error, context);

  return {
    id: `error_${Date.now()}`,
    type: "assistant",
    content: userFriendlyMessage,
    timestamp: new Date(),
    isError: true,
    errorPhase,
    originalError: error.message,
    userFriendlyMessage,
    suggestions,
    retryable: error.retryable || false,
    recoveryActions,
    errorCode: error.code,
  };
}

/**
 * Determine the phase where the error occurred
 */
function determineErrorPhase(
  error: ApiError
):
  | "translation"
  | "execution"
  | "network"
  | "timeout"
  | "data_not_found"
  | "validation" {
  const code = error.code?.toLowerCase() || "";
  const message = error.message?.toLowerCase() || "";

  if (code.includes("network") || code.includes("connection")) {
    return "network";
  }

  if (code.includes("timeout") || message.includes("timeout")) {
    return "timeout";
  }

  if (
    code.includes("translation") ||
    code.includes("invalid_sql") ||
    message.includes("understand")
  ) {
    return "translation";
  }

  if (
    code.includes("not_found") ||
    code.includes("no_data") ||
    message.includes("no data")
  ) {
    return "data_not_found";
  }

  if (code.includes("validation") || code.includes("empty")) {
    return "validation";
  }

  return "execution";
}

/**
 * Generate user-friendly error messages based on error type and context
 */
function generateUserFriendlyMessage(
  error: ApiError,
  context: ErrorContext
): string {
  const { hasData, userMessage } = context;
  const code = error.code?.toLowerCase() || "";
  const message = error.message?.toLowerCase() || "";

  // No data uploaded scenarios
  if (
    !hasData ||
    code.includes("no_data_uploaded") ||
    code.includes("table_not_found")
  ) {
    return "I'd love to help you analyze that data, but it looks like you haven't uploaded any data yet. Once you upload a CSV file, I'll be able to answer questions about it!";
  }

  // Column not found scenarios
  if (
    code.includes("column_not_found") ||
    (message.includes("column") && message.includes("not found"))
  ) {
    return "I couldn't find that specific information in your data. The dataset might not contain the fields you're asking about, or they might be named differently.";
  }

  // Translation/understanding issues
  if (
    code.includes("translation") ||
    code.includes("invalid_sql") ||
    message.includes("understand")
  ) {
    return "I'm having trouble understanding exactly what you're looking for. Could you try rephrasing your question in a different way?";
  }

  // Timeout issues
  if (code.includes("timeout") || message.includes("timeout")) {
    return "Your question is taking longer to process than expected. This usually happens with complex queries or large datasets.";
  }

  // Network issues
  if (code.includes("network") || code.includes("connection")) {
    return "I'm having trouble connecting right now. Please check your internet connection and try again.";
  }

  // Rate limiting
  if (code.includes("rate_limit")) {
    return "You're asking questions a bit too quickly! Please wait a moment before trying again.";
  }

  // File upload issues
  if (code.includes("file_too_large")) {
    return "Your file is too large to upload. Please try a smaller CSV file (under 10MB).";
  }

  if (code.includes("invalid_file_type")) {
    return "Please upload a valid CSV file. Other file types are not supported yet.";
  }

  // Data quality issues
  if (message.includes("format") || message.includes("parsing")) {
    return "There seems to be an issue with your data format. Some values might not be in the expected format for analysis.";
  }

  // Memory/resource issues
  if (message.includes("memory") || message.includes("resource")) {
    return "Your query is trying to process too much data at once. Let's try a more focused approach.";
  }

  // Generic fallback
  return "I ran into an issue processing your request. Let me help you find a different way to get the information you're looking for.";
}

/**
 * Generate contextual suggestions based on error type and user context
 */
function generateSuggestions(error: ApiError, context: ErrorContext): string[] {
  const { hasData, dataColumns, userMessage } = context;
  const code = error.code?.toLowerCase() || "";
  const message = error.message?.toLowerCase() || "";
  const suggestions: string[] = [];

  // No data scenarios
  if (!hasData) {
    return [
      "Click the upload button to add your CSV file",
      "Try the demo data to see how the system works",
      "What kind of data are you planning to analyze?",
    ];
  }

  // Column not found scenarios
  if (code.includes("column_not_found")) {
    suggestions.push("Try asking about different data fields");
    if (dataColumns.length > 0) {
      suggestions.push(
        `Available columns include: ${dataColumns.slice(0, 3).join(", ")}`
      );
    }
    suggestions.push("Would you like to see what data is available?");
    return suggestions.slice(0, 3);
  }

  // Translation issues
  if (code.includes("translation") || code.includes("invalid_sql")) {
    suggestions.push("Try using simpler, more direct language");
    suggestions.push("Ask about one thing at a time");

    // Add context-specific examples
    const userLower = userMessage?.toLowerCase() || "";
    if (userLower.includes("sales") || userLower.includes("revenue")) {
      suggestions.push("Example: 'Show me total sales by month'");
    } else if (userLower.includes("customer")) {
      suggestions.push("Example: 'How many customers do I have?'");
    } else {
      suggestions.push("Example: 'Show me the top 10 results'");
    }

    return suggestions.slice(0, 3);
  }

  // Timeout issues
  if (code.includes("timeout")) {
    return [
      "Try asking about a smaller subset of data",
      "Filter to a specific time period or category",
      "Ask for totals or summaries instead of detailed data",
    ];
  }

  // Network issues
  if (code.includes("network")) {
    return [
      "Check your internet connection",
      "Try refreshing the page",
      "Wait a moment and try again",
    ];
  }

  // Generic suggestions based on user message content
  const userLower = userMessage?.toLowerCase() || "";
  if (userLower.includes("sales") || userLower.includes("revenue")) {
    suggestions.push(
      "Try asking 'What are my total sales?' or 'Show me sales trends'"
    );
  } else if (userLower.includes("customer")) {
    suggestions.push(
      "Try asking 'How many customers do I have?' or 'Show me customer data'"
    );
  } else if (userLower.includes("product")) {
    suggestions.push(
      "Try asking 'What are my top products?' or 'Show me product performance'"
    );
  }

  // Add generic helpful suggestions
  suggestions.push("Try rephrasing your question in simpler terms");
  suggestions.push("Ask about specific aspects of your data");
  suggestions.push("Would you like to see what data is available to explore?");

  return suggestions.slice(0, 3);
}

/**
 * Generate recovery actions based on error type
 */
function generateRecoveryActions(
  error: ApiError,
  context: ErrorContext
): RecoveryAction[] {
  const { hasData } = context;
  const code = error.code?.toLowerCase() || "";
  const actions: RecoveryAction[] = [];

  // Always add retry if the error is retryable
  if (error.retryable) {
    actions.push({
      type: "retry",
      label: "Try Again",
      description: "Retry the same request",
    });
  }

  // Add rephrase option for translation/understanding issues
  if (
    code.includes("translation") ||
    code.includes("invalid_sql") ||
    code.includes("validation")
  ) {
    actions.push({
      type: "rephrase",
      label: "Rephrase Question",
      description: "Try asking in a different way",
    });
  }

  // Add simplify option for complex queries
  if (
    code.includes("timeout") ||
    code.includes("memory") ||
    code.includes("complex")
  ) {
    actions.push({
      type: "simplify",
      label: "Simplify Question",
      description: "Ask a simpler version of your question",
    });
  }

  // Add contact support for persistent issues
  if (
    !error.retryable ||
    code.includes("internal") ||
    code.includes("server")
  ) {
    actions.push({
      type: "contact_support",
      label: "Contact Support",
      description: "Get help from our support team",
    });
  }

  return actions.slice(0, 3); // Limit to 3 actions
}

/**
 * Get error-specific help text for common scenarios
 */
export function getErrorHelpText(errorCode: string): string | null {
  const helpTexts: Record<string, string> = {
    NO_DATA_UPLOADED:
      "Upload a CSV file first to start analyzing your data. The system needs data to answer questions about it.",
    COLUMN_NOT_FOUND:
      "The data doesn't contain the specific field you're asking about. Try asking about different columns or check what data is available.",
    TRANSLATION_FAILED:
      "The system couldn't understand your question. Try using simpler language or be more specific about what you want to see.",
    TIMEOUT_ERROR:
      "Your question is too complex or involves too much data. Try asking about a smaller subset or simpler metrics.",
    NETWORK_ERROR:
      "There's a connection issue. Check your internet connection and try again.",
    RATE_LIMIT_ERROR:
      "You're asking questions too quickly. Wait a few seconds before trying again.",
    FILE_TOO_LARGE:
      "Your CSV file is too big. Try uploading a smaller file or removing unnecessary columns.",
    INVALID_FILE_TYPE:
      "Only CSV files are supported. Make sure your file has a .csv extension and is properly formatted.",
  };

  return helpTexts[errorCode] || null;
}

/**
 * Check if an error suggests the user should upload data
 */
export function shouldSuggestDataUpload(error: ApiError): boolean {
  const code = error.code?.toLowerCase() || "";
  const message = error.message?.toLowerCase() || "";

  return (
    code.includes("no_data") ||
    code.includes("table_not_found") ||
    message.includes("no data") ||
    message.includes("upload")
  );
}

/**
 * Check if an error suggests the user should try demo data
 */
export function shouldSuggestDemoData(error: ApiError): boolean {
  return shouldSuggestDataUpload(error);
}
