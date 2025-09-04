import React, { useState, useRef, useEffect } from "react";
import MessageRenderer, { ChatMessage } from "./MessageRenderer";
import { useChat } from "../hooks/useChat";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { QueryProcessingLoading } from "./LoadingState";
import { QueryExecutionProgress } from "./ProgressIndicator";
import { useLoadingState } from "../hooks/useLoadingState";
import {
  ApiError,
  ConversationalResponse,
  ExecuteResponse,
} from "../types/api";
import { ChartConfig } from "../types/chart";
import { viewStateManager } from "../services/viewStateManager";

interface ConversationInterfaceProps {
  onSendMessage?: (message: string) => void;
  messages?: ChatMessage[];
  isProcessing?: boolean;
  suggestedQuestions?: string[];
  placeholder?: string;
  onFollowUpClick?: (question: string) => void;
  onError?: (error: ApiError) => void;
  onSuccess?: (response: any) => void;
  useBuiltInChat?: boolean; // New prop to enable built-in chat functionality
  onDashboardUpdate?: (
    chartConfig: ChartConfig,
    queryResults?: ExecuteResponse,
    query?: string
  ) => void; // New prop for dashboard updates
  enableViewStateManagement?: boolean; // New prop to enable automatic view state management
  processingStage?:
    | "translating"
    | "executing"
    | "processing"
    | "generating_chart"
    | "complete";
  processingProgress?: number;
  currentQuery?: string;
}

export default function ConversationInterface({
  onSendMessage,
  messages: externalMessages,
  isProcessing: externalIsProcessing,
  suggestedQuestions = [],
  placeholder = "Ask me anything about your data...",
  onFollowUpClick,
  onError,
  onSuccess,
  useBuiltInChat = false,
  onDashboardUpdate,
  enableViewStateManagement = true,
  processingStage = "processing",
  processingProgress,
  currentQuery,
}: ConversationInterfaceProps) {
  const [input, setInput] = useState("");
  const [focusedSuggestionIndex, setFocusedSuggestionIndex] = useState(-1);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const suggestionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Use built-in chat hook if enabled, otherwise use external props
  const chat = useChat({
    onError,
    onSuccess: (response: ConversationalResponse) => {
      // Handle chat response with proper view routing
      handleChatResponse(response);
      onSuccess?.(response);
    },
  });

  const messages = useBuiltInChat ? chat.messages : externalMessages || [];
  const isProcessing = useBuiltInChat
    ? chat.isProcessing
    : externalIsProcessing || false;
  const isLoadingHistory = useBuiltInChat ? chat.isLoadingHistory : false;

  // Get loading state for enhanced progress display
  const { queryExecution } = useLoadingState();

  /**
   * Handle chat response with proper view routing
   * Requirements: 2.5, 2.7 - Route responses to correct view and implement automatic view switching
   */
  const handleChatResponse = (response: ConversationalResponse) => {
    if (!enableViewStateManagement) {
      return;
    }

    // Check if response contains chart configuration (visualization)
    if (response.chart_config) {
      console.log(
        "📊 Chat response contains visualization - routing to dashboard view"
      );

      // Create placeholder query results if not provided
      // In a full implementation, the backend would provide both chart config and query results
      const queryResults: ExecuteResponse = {
        columns: [],
        rows: [],
        row_count: 0,
        runtime_ms: 0,
        truncated: false,
      };

      // Update dashboard view state (never affects data view)
      // This automatically switches to dashboard view when visualizations are created
      viewStateManager.updateDashboardData(
        queryResults,
        response.chart_config,
        "", // Query text would come from the original message
        true // Auto-switch to dashboard view
      );

      // Notify parent component about dashboard update
      onDashboardUpdate?.(response.chart_config, queryResults, "");

      console.log(
        "✅ Visualization routed to dashboard view, data view preserved"
      );
    } else {
      console.log(
        "💬 Chat response contains no visualization - staying in current view"
      );
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isProcessing]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Keyboard shortcuts for chat interface
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: "Escape",
        action: () => {
          setFocusedSuggestionIndex(-1);
          inputRef.current?.focus();
        },
        description: "Clear suggestion focus and return to input",
      },
      {
        key: "ArrowDown",
        action: () => {
          if (suggestedQuestions.length > 0) {
            setFocusedSuggestionIndex((prev) =>
              prev < suggestedQuestions.length - 1 ? prev + 1 : 0
            );
          }
        },
        description: "Navigate down through suggested questions",
      },
      {
        key: "ArrowUp",
        action: () => {
          if (suggestedQuestions.length > 0) {
            setFocusedSuggestionIndex((prev) =>
              prev > 0 ? prev - 1 : suggestedQuestions.length - 1
            );
          }
        },
        description: "Navigate up through suggested questions",
      },
      {
        key: "Enter",
        action: () => {
          if (
            focusedSuggestionIndex >= 0 &&
            focusedSuggestionIndex < suggestedQuestions.length
          ) {
            handleSuggestedQuestion(suggestedQuestions[focusedSuggestionIndex]);
            setFocusedSuggestionIndex(-1);
          }
        },
        description: "Select focused suggested question",
      },
    ],
    enabled: !isProcessing,
  });

  // Focus management for suggestions
  useEffect(() => {
    if (
      focusedSuggestionIndex >= 0 &&
      suggestionRefs.current[focusedSuggestionIndex]
    ) {
      suggestionRefs.current[focusedSuggestionIndex]?.focus();
    }
  }, [focusedSuggestionIndex]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      const message = input.trim();

      if (useBuiltInChat) {
        // Built-in chat handles response routing automatically
        chat.sendMessage(message);
      } else if (onSendMessage) {
        // External message handler - preserve existing behavior
        onSendMessage(message);
      }

      setInput("");

      // Log message routing for debugging
      console.log(
        `💬 Message sent: "${message.substring(0, 50)}${
          message.length > 50 ? "..." : ""
        }" (${useBuiltInChat ? "built-in" : "external"} chat)`
      );
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    if (!isProcessing) {
      if (useBuiltInChat) {
        // Built-in chat handles response routing automatically
        chat.sendMessage(question);
      } else if (onSendMessage) {
        // External message handler - preserve existing behavior
        onSendMessage(question);
      }

      setFocusedSuggestionIndex(-1);
      inputRef.current?.focus();

      // Log suggested question routing for debugging
      console.log(
        `💬 Suggested question sent: "${question}" (${
          useBuiltInChat ? "built-in" : "external"
        } chat)`
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Skip link for keyboard navigation */}
      <a
        href="#chat-input"
        className="skip-link"
        onFocus={() => inputRef.current?.focus()}
      >
        Skip to chat input
      </a>

      {/* Messages Area */}
      <main
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
        role="log"
        aria-live="polite"
        aria-label="Chat conversation"
        tabIndex={-1}
      >
        {/* Loading history indicator */}
        {isLoadingHistory && (
          <div
            className="flex justify-center py-4"
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center gap-2 text-gray-600">
              <svg
                className="w-4 h-4 animate-spin"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span className="text-sm">Loading conversation history...</span>
            </div>
          </div>
        )}

        {messages.length === 0 && !isProcessing && !isLoadingHistory ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h1 className="text-lg font-medium text-gray-900 mb-2">
                Let's explore your data together
              </h1>
              <p className="text-gray-600 text-sm">
                Ask me questions in plain English and I'll help you discover
                insights from your data.
              </p>

              {/* Show suggested questions if available */}
              {suggestedQuestions.length > 0 && (
                <section
                  className="mt-6"
                  aria-labelledby="suggested-questions-heading"
                >
                  <h2
                    id="suggested-questions-heading"
                    className="text-sm font-medium text-gray-700 mb-3"
                  >
                    Try asking:
                  </h2>
                  <div className="space-y-2" role="list">
                    {suggestedQuestions.slice(0, 3).map((question, index) => (
                      <button
                        key={index}
                        ref={(el) => (suggestionRefs.current[index] = el)}
                        onClick={() => handleSuggestedQuestion(question)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleSuggestedQuestion(question);
                          }
                        }}
                        className={`block w-full text-left px-3 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 focus:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg transition-colors ${
                          focusedSuggestionIndex === index
                            ? "bg-blue-100 ring-2 ring-blue-500"
                            : ""
                        }`}
                        role="listitem"
                        aria-label={`Suggested question: ${question}`}
                      >
                        "{question}"
                      </button>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageRenderer
                key={message.id}
                message={message}
                onFollowUpClick={onFollowUpClick || onSendMessage}
              />
            ))}

            {/* Enhanced processing indicator */}
            {(isProcessing || queryExecution.isLoading) && (
              <div
                className="flex justify-start"
                role="status"
                aria-live="polite"
              >
                <div className="bg-gray-100 border border-gray-200 px-4 py-3 rounded-lg max-w-[90%]">
                  {queryExecution.isLoading ? (
                    <QueryExecutionProgress
                      currentStage={
                        (queryExecution.stage as any) || "translating"
                      }
                      queryText={currentQuery}
                      progress={queryExecution.progress}
                      error={queryExecution.error}
                    />
                  ) : (
                    <QueryProcessingLoading
                      isLoading={true}
                      stage={processingStage}
                      progress={processingProgress}
                      queryText={currentQuery}
                    />
                  )}
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="border-t border-gray-200 p-4 bg-gray-50">
        <form onSubmit={handleSubmit} className="flex gap-3" role="search">
          <div className="flex-1">
            <label htmlFor="chat-input" className="sr-only">
              Ask a question about your data
            </label>
            <input
              id="chat-input"
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isProcessing || isLoadingHistory}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
              data-testid="chat-input"
              aria-describedby={isProcessing ? "processing-status" : undefined}
              autoComplete="off"
              spellCheck="true"
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isProcessing || isLoadingHistory}
            className="px-4 sm:px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 min-w-[80px] sm:min-w-[100px]"
            data-testid="send-button"
            aria-label={
              isProcessing ? "Processing your question" : "Send message"
            }
          >
            {isProcessing ? (
              <svg
                className="w-4 h-4 animate-spin"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            ) : (
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 5l7 7-7 7M5 12h14"
                />
              </svg>
            )}
            <span className="hidden sm:inline text-sm">
              {isProcessing ? "Thinking..." : "Send"}
            </span>
          </button>
        </form>
        {isProcessing && (
          <div id="processing-status" className="sr-only" aria-live="polite">
            Processing your question, please wait...
          </div>
        )}
      </footer>
    </div>
  );
}

// Typing Indicator Component
function TypingIndicator() {
  const [currentStatus, setCurrentStatus] = useState(0);

  const statusMessages = [
    "Analyzing your question...",
    "Looking at the data...",
    "Preparing your answer...",
    "Creating visualization...",
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStatus((prev) => (prev + 1) % statusMessages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [statusMessages.length]);

  return (
    <div className="flex justify-start" role="status" aria-live="polite">
      <div className="bg-gray-100 border border-gray-200 px-4 py-3 rounded-lg max-w-[80%] sm:max-w-[85%]">
        <div className="flex items-center gap-3">
          {/* Animated dots */}
          <div className="flex space-x-1" aria-hidden="true">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
            <div
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.1s" }}
            ></div>
            <div
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            ></div>
          </div>

          {/* Status message */}
          <div className="text-sm text-gray-700">
            {statusMessages[currentStatus]}
          </div>
        </div>
      </div>
    </div>
  );
}
