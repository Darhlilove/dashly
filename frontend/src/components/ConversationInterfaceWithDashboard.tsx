import React, { useState, useRef, useEffect } from "react";
import MessageRenderer, { ChatMessage } from "./MessageRenderer";
import { useChatWithDashboard } from "../hooks/useChatWithDashboard";
import { dashboardAutomationService } from "../services/dashboardAutomation";
import { ApiError, ExecuteResponse } from "../types/api";
import { ChartConfig } from "../types";

interface ConversationInterfaceWithDashboardProps {
  onSendMessage?: (message: string) => void;
  messages?: ChatMessage[];
  isProcessing?: boolean;
  suggestedQuestions?: string[];
  placeholder?: string;
  onFollowUpClick?: (question: string) => void;
  onError?: (error: ApiError) => void;
  onSuccess?: (response: any) => void;
  onDashboardUpdate?: (
    chartConfig: ChartConfig,
    queryResults?: ExecuteResponse,
    query?: string
  ) => void;
  onChartRecommendation?: (chartConfig: ChartConfig) => void;
  useBuiltInChat?: boolean;
  enableAutomaticDashboardUpdates?: boolean; // New prop to enable automatic dashboard updates
}

/**
 * Enhanced conversation interface that automatically updates the dashboard
 * when chart configurations are received from chat interactions.
 *
 * This component implements the seamless integration between chat responses
 * and dashboard updates as specified in task 8.
 */
export default function ConversationInterfaceWithDashboard({
  onSendMessage,
  messages: externalMessages,
  isProcessing: externalIsProcessing,
  suggestedQuestions = [],
  placeholder = "Ask me anything about your data...",
  onFollowUpClick,
  onError,
  onSuccess,
  onDashboardUpdate,
  onChartRecommendation,
  useBuiltInChat = false,
  enableAutomaticDashboardUpdates = true,
}: ConversationInterfaceWithDashboardProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Use enhanced chat hook with dashboard integration
  const chat = useChatWithDashboard({
    onError,
    onSuccess: (response) => {
      onSuccess?.(response);

      // Log automatic dashboard update activity
      if (response.chart_config && enableAutomaticDashboardUpdates) {
        console.log(
          "📊 Chat response includes chart configuration - automatic dashboard update triggered"
        );
      }
    },
    onDashboardUpdate: async (chartConfig, queryResults, query) => {
      if (!enableAutomaticDashboardUpdates) {
        console.log("🚫 Automatic dashboard updates disabled");
        return;
      }

      console.log("🔄 Processing automatic dashboard update from chat");

      try {
        // Use the dashboard automation service to process the chart recommendation
        const result =
          await dashboardAutomationService.processChartRecommendation(
            chartConfig,
            query,
            {
              executeQuery: true, // Execute query to get actual data
              onUpdate: (updateResult) => {
                if (updateResult.success && updateResult.queryResults) {
                  console.log("✅ Automatic dashboard update successful");
                  onDashboardUpdate?.(
                    updateResult.chartConfig,
                    updateResult.queryResults,
                    query
                  );
                }
              },
              onError: (error) => {
                console.error("❌ Automatic dashboard update failed:", error);
                // Still call the dashboard update callback with just the chart config
                onDashboardUpdate?.(chartConfig, queryResults, query);
              },
            }
          );

        // If the automation service didn't execute a query, still update with what we have
        if (!result.queryResults && queryResults) {
          onDashboardUpdate?.(result.chartConfig, queryResults, query);
        }
      } catch (error) {
        console.error(
          "❌ Failed to process automatic dashboard update:",
          error
        );
        // Fallback to basic dashboard update
        onDashboardUpdate?.(chartConfig, queryResults, query);
      }
    },
    onChartRecommendation: (chartConfig) => {
      console.log("📊 Chart recommendation received:", chartConfig);
      onChartRecommendation?.(chartConfig);
    },
  });

  const messages = useBuiltInChat ? chat.messages : externalMessages || [];
  const isProcessing = useBuiltInChat
    ? chat.isProcessing
    : externalIsProcessing || false;

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      if (useBuiltInChat) {
        console.log(
          "💬 Sending message with automatic dashboard updates enabled:",
          enableAutomaticDashboardUpdates
        );
        chat.sendMessage(input.trim());
      } else if (onSendMessage) {
        onSendMessage(input.trim());
      }
      setInput("");
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    if (!isProcessing) {
      if (useBuiltInChat) {
        console.log(
          "💬 Sending suggested question with automatic dashboard updates enabled:",
          enableAutomaticDashboardUpdates
        );
        chat.sendMessage(question);
      } else if (onSendMessage) {
        onSendMessage(question);
      }
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
      {/* Header with dashboard integration status */}
      {enableAutomaticDashboardUpdates && (
        <div className="border-b border-gray-200 px-4 py-2 bg-blue-50">
          <div className="flex items-center gap-2 text-sm text-blue-700">
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
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <span>Automatic dashboard updates enabled</span>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isProcessing ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-blue-600"
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
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Let's explore your data together
              </h3>
              <p className="text-gray-600 text-sm mb-4">
                Ask me questions in plain English and I'll help you discover
                insights from your data.
              </p>
              {enableAutomaticDashboardUpdates && (
                <p className="text-blue-600 text-xs">
                  📊 Charts will be automatically added to your dashboard when
                  appropriate
                </p>
              )}

              {/* Show suggested questions if available */}
              {suggestedQuestions.length > 0 && (
                <div className="mt-6">
                  <p className="text-sm font-medium text-gray-700 mb-3">
                    Try asking:
                  </p>
                  <div className="space-y-2">
                    {suggestedQuestions.slice(0, 3).map((question, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestedQuestion(question)}
                        className="block w-full text-left px-3 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                      >
                        "{question}"
                      </button>
                    ))}
                  </div>
                </div>
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

            {/* Enhanced typing indicator with dashboard update context */}
            {isProcessing && (
              <EnhancedTypingIndicator
                enableAutomaticDashboardUpdates={
                  enableAutomaticDashboardUpdates
                }
              />
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isProcessing}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
              data-testid="chat-input"
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            data-testid="send-button"
          >
            {isProcessing ? (
              <svg
                className="w-4 h-4 animate-spin"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
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
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
            <span className="hidden sm:inline">
              {isProcessing ? "Thinking..." : "Send"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
}

// Enhanced Typing Indicator Component with dashboard context
function EnhancedTypingIndicator({
  enableAutomaticDashboardUpdates,
}: {
  enableAutomaticDashboardUpdates: boolean;
}) {
  const [currentStatus, setCurrentStatus] = useState(0);

  const statusMessages = enableAutomaticDashboardUpdates
    ? [
        "Analyzing your question...",
        "Looking at the data...",
        "Preparing your answer...",
        "Creating visualization...",
        "Updating dashboard...",
      ]
    : [
        "Analyzing your question...",
        "Looking at the data...",
        "Preparing your answer...",
      ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStatus((prev) => (prev + 1) % statusMessages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [statusMessages.length]);

  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 border border-gray-200 px-4 py-3 rounded-lg max-w-[80%]">
        <div className="flex items-center gap-3">
          {/* Animated dots */}
          <div className="flex space-x-1">
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
