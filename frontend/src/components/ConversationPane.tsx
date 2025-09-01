import { useState } from "react";
import {
  Message,
  SQLMessage,
  ExecutionStatusMessage,
  ErrorMessage,
} from "../types";
import AdvancedModeToggle from "./AdvancedModeToggle";
import ErrorRecovery from "./ErrorRecovery";

interface ConversationPaneProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  placeholder?: string;
  executionMode?: "automatic" | "advanced";
  onExecutionModeChange?: (mode: "automatic" | "advanced") => void;
}

export default function ConversationPane({
  messages,
  onSendMessage,
  isLoading,
  placeholder = "Ask a question about your data...",
  executionMode = "automatic",
  onExecutionModeChange,
}: ConversationPaneProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  // Type guards for message types
  const isSQLMessage = (message: Message): message is SQLMessage => {
    return message.type === "assistant" && "sqlQuery" in message;
  };

  const isExecutionStatusMessage = (
    message: Message
  ): message is ExecutionStatusMessage => {
    return message.type === "system" && "status" in message;
  };

  const isErrorMessage = (message: Message): message is ErrorMessage => {
    return message.type === "assistant" && "isError" in message;
  };

  // Render SQL code block
  const renderSQLBlock = (sql: string) => (
    <div className="mt-3 bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm overflow-x-auto border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="text-gray-400 text-xs font-semibold uppercase tracking-wide">
          Generated SQL
        </div>
        <button
          onClick={() => navigator.clipboard.writeText(sql)}
          className="text-gray-400 hover:text-green-400 transition-colors p-1 rounded"
          title="Copy SQL to clipboard"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        </button>
      </div>
      <pre className="whitespace-pre-wrap text-green-300 leading-relaxed">
        {sql}
      </pre>
    </div>
  );

  // Render execution status indicator
  const renderExecutionStatus = (status: string, details?: any) => {
    const statusConfig = {
      pending: {
        color: "text-yellow-600 bg-yellow-50 border-yellow-200",
        icon: "⏳",
        text: "Query pending...",
        pulse: true,
      },
      executing: {
        color: "text-blue-600 bg-blue-50 border-blue-200",
        icon: "⚡",
        text: "Executing query...",
        pulse: true,
      },
      completed: {
        color: "text-green-600 bg-green-50 border-green-200",
        icon: "✅",
        text: "Query completed",
        pulse: false,
      },
      failed: {
        color: "text-red-600 bg-red-50 border-red-200",
        icon: "❌",
        text: "Query failed",
        pulse: false,
      },
    };

    const config =
      statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;

    return (
      <div
        className={`mt-2 px-3 py-2 rounded-lg border text-sm ${config.color} ${
          config.pulse ? "animate-pulse" : ""
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">{config.icon}</span>
          <span className="font-medium">{config.text}</span>
          {details?.executionTime && (
            <span className="text-gray-600 font-mono">
              {details.executionTime}ms
            </span>
          )}
          {details?.rowCount !== undefined && (
            <span className="text-gray-600">
              • {details.rowCount.toLocaleString()} rows
            </span>
          )}
        </div>
      </div>
    );
  };

  // Render error message using the ErrorRecovery component
  const renderErrorMessage = (message: ErrorMessage) => (
    <div className="mt-3">
      <ErrorRecovery error={message} />
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header with execution mode toggle */}
      {onExecutionModeChange && (
        <div className="border-b border-gray-200 px-4 py-3 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg
                className="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <span className="text-sm font-medium text-gray-700">
                Execution Mode
              </span>
            </div>
            <AdvancedModeToggle
              isAdvancedMode={executionMode === "advanced"}
              onToggle={(enabled) =>
                onExecutionModeChange(enabled ? "advanced" : "automatic")
              }
              disabled={isLoading}
              size="sm"
              showLabels={true}
            />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {executionMode === "automatic"
              ? "Queries are executed automatically after SQL generation"
              : "SQL queries are shown for review before execution"}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg
                className="w-12 h-12 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="text-sm">Start a conversation about your data</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.type === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 ${
                  message.type === "user"
                    ? "bg-black text-white"
                    : message.type === "system"
                    ? "bg-blue-50 text-blue-800 border border-blue-200"
                    : isErrorMessage(message)
                    ? "bg-red-50 text-red-800 border border-red-200"
                    : "bg-gray-100 text-black border border-gray-200"
                }`}
              >
                {/* Regular message content */}
                <div className="text-sm whitespace-pre-wrap">
                  {message.content}
                </div>

                {/* SQL Message enhancements */}
                {isSQLMessage(message) && message.sqlQuery && (
                  <>
                    {renderSQLBlock(message.sqlQuery)}
                    {message.executionStatus &&
                      renderExecutionStatus(message.executionStatus, {
                        executionTime: message.executionTime,
                        rowCount: message.rowCount,
                      })}
                  </>
                )}

                {/* Execution Status Message */}
                {isExecutionStatusMessage(message) &&
                  renderExecutionStatus(message.status, message.details)}

                {/* Error Message */}
                {isErrorMessage(message) && renderErrorMessage(message)}

                {/* Timestamp */}
                <div
                  className={`text-xs mt-1 ${
                    message.type === "user"
                      ? "text-gray-300"
                      : message.type === "system"
                      ? "text-blue-500"
                      : isErrorMessage(message)
                      ? "text-red-500"
                      : "text-gray-500"
                  }`}
                >
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-blue-50 text-blue-800 border border-blue-200 px-4 py-3 max-w-[80%] rounded-lg">
              <div className="flex items-center gap-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-blue-500 animate-bounce rounded-full"></div>
                  <div
                    className="w-2 h-2 bg-blue-500 animate-bounce rounded-full"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-blue-500 animate-bounce rounded-full"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">
                    {executionMode === "automatic"
                      ? "Processing your query..."
                      : "Thinking..."}
                  </span>
                  {executionMode === "automatic" && (
                    <span className="text-xs text-blue-600 mt-1">
                      Generating SQL and executing automatically
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            disabled={isLoading}
            className="flex-1 px-3 py-2 border border-gray-300 focus:outline-none focus:border-gray-400 active:border-gray-400 disabled:bg-gray-50 disabled:cursor-not-allowed"
            data-testid="query-input"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 focus:outline-none active:bg-red-800 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150"
            data-testid="generate-button"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 5l7 7-7 7M5 12h14"
              />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
