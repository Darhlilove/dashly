import React from "react";
import { ErrorMessage, RecoveryAction } from "../types/ui";

interface ErrorRecoveryProps {
  error: ErrorMessage;
  onRetry?: () => void;
  onRephrase?: () => void;
  onSimplify?: () => void;
  className?: string;
}

export default function ErrorRecovery({
  error,
  onRetry,
  onRephrase,
  onSimplify,
  className = "",
}: ErrorRecoveryProps) {
  const handleRecoveryAction = (action: RecoveryAction) => {
    // Execute the action's built-in handler if available
    if (action.action) {
      action.action();
      return;
    }

    // Fallback to prop handlers
    switch (action.type) {
      case "retry":
        onRetry?.();
        break;
      case "rephrase":
        onRephrase?.();
        break;
      case "simplify":
        onSimplify?.();
        break;
      case "contact_support":
        // Could open a support modal or redirect
        window.open("mailto:support@dashly.com?subject=Error Report", "_blank");
        break;
    }
  };

  const getErrorIcon = (phase: string) => {
    switch (phase) {
      case "translation":
        return "🤔";
      case "execution":
        return "⚠️";
      case "network":
        return "🌐";
      case "timeout":
        return "⏱️";
      case "data_not_found":
        return "📊";
      case "validation":
        return "✏️";
      default:
        return "❌";
    }
  };

  const getErrorTitle = (phase: string) => {
    switch (phase) {
      case "translation":
        return "Couldn't understand your question";
      case "execution":
        return "Query execution failed";
      case "network":
        return "Connection problem";
      case "timeout":
        return "Request timed out";
      case "data_not_found":
        return "No data found";
      case "validation":
        return "Invalid input";
      default:
        return "Something went wrong";
    }
  };

  const getContextualHelp = (phase: string): string | null => {
    switch (phase) {
      case "translation":
        return "Try using simpler language or be more specific about what data you want to see. For example: 'Show me total sales by month' instead of 'Tell me about sales'.";
      case "execution":
        return "This usually happens when the data doesn't contain what you're looking for, or the query is too complex. Try asking about specific columns or a smaller subset of data.";
      case "network":
        return "Check your internet connection and try again. If the problem persists, the server might be temporarily unavailable.";
      case "timeout":
        return "Your question might be too complex or involve too much data. Try asking about a smaller time period or specific categories.";
      case "data_not_found":
        return "Make sure you've uploaded data first, or try asking about different aspects of your dataset.";
      case "validation":
        return "Check that your question is clear and relates to the data you've uploaded. Avoid very short or vague questions.";
      default:
        return null;
    }
  };

  return (
    <div
      className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}
    >
      {/* Error header */}
      <div className="flex items-center gap-2 text-red-700 font-medium mb-3">
        <span className="text-lg">{getErrorIcon(error.errorPhase)}</span>
        <span>{getErrorTitle(error.errorPhase)}</span>
        {error.errorCode && (
          <span className="text-xs bg-red-100 px-2 py-1 rounded font-mono">
            {error.errorCode}
          </span>
        )}
      </div>

      {/* User-friendly error message */}
      <div className="text-red-700 text-sm mb-4 leading-relaxed">
        {error.userFriendlyMessage}
      </div>

      {/* Technical details (collapsible) */}
      {error.originalError && (
        <details className="mb-4">
          <summary className="text-red-600 text-xs cursor-pointer hover:text-red-700 select-none">
            Technical details
          </summary>
          <div className="mt-2 text-red-600 text-xs font-mono bg-red-100 p-2 rounded border">
            {error.originalError}
          </div>
        </details>
      )}

      {/* Suggestions */}
      {error.suggestions.length > 0 && (
        <div className="mb-4">
          <div className="text-red-700 font-medium text-sm mb-2 flex items-center gap-1">
            <span>💡</span>
            <span>Try this:</span>
          </div>
          <ul className="text-red-600 text-sm space-y-2">
            {error.suggestions.slice(0, 3).map((suggestion, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>
                <span className="leading-relaxed">{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Contextual help based on error type */}
      {getContextualHelp(error.errorPhase) && (
        <div className="mb-4 bg-blue-50 border border-blue-200 rounded p-3">
          <div className="text-blue-700 font-medium text-sm mb-1 flex items-center gap-1">
            <span>ℹ️</span>
            <span>Helpful tip:</span>
          </div>
          <div className="text-blue-600 text-sm">
            {getContextualHelp(error.errorPhase)}
          </div>
        </div>
      )}

      {/* Recovery actions */}
      {error.recoveryActions && error.recoveryActions.length > 0 && (
        <div className="border-t border-red-200 pt-3">
          <div className="text-red-700 font-medium text-sm mb-2">
            What would you like to do?
          </div>
          <div className="flex flex-wrap gap-2">
            {error.recoveryActions.map((action, index) => (
              <button
                key={index}
                onClick={() => handleRecoveryAction(action)}
                className="px-3 py-1.5 text-xs bg-red-100 text-red-700 hover:bg-red-200 rounded border border-red-300 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
                title={action.description}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Retry hint */}
      {error.retryable && (
        <div className="mt-3 pt-3 border-t border-red-200 text-red-600 text-xs flex items-center gap-1">
          <span>🔄</span>
          <span>This error might be temporary - you can try asking again</span>
        </div>
      )}
    </div>
  );
}
