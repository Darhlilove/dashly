import React from "react";
import { ChartRenderer } from "./ChartRenderer";
import { ChartConfig } from "../types/chart";

// Enhanced ChatMessage interface with chart support and dashboard update tracking
export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: {
    chartConfig?: ChartConfig;
    insights?: string[];
    followUpQuestions?: string[];
    chartData?: {
      columns: string[];
      rows: any[][];
    };
    dashboardUpdated?: boolean; // Flag to indicate if dashboard was automatically updated
  };
}

interface MessageRendererProps {
  message: ChatMessage;
  onFollowUpClick?: (question: string) => void;
}

export default function MessageRenderer({
  message,
  onFollowUpClick,
}: MessageRendererProps) {
  const isUser = message.type === "user";

  return (
    <article
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
      data-testid={`message-${message.type}`}
      role="article"
      aria-label={`${
        isUser ? "Your" : "Assistant"
      } message from ${message.timestamp.toLocaleTimeString()}`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[80%] md:max-w-[75%] ${
          isUser
            ? "bg-blue-600 text-white rounded-l-lg rounded-tr-lg"
            : "bg-white text-gray-900 border border-gray-200 rounded-r-lg rounded-tl-lg shadow-sm"
        } overflow-hidden`}
      >
        {/* Message content */}
        <div className="px-4 py-3">
          <div
            className="text-sm whitespace-pre-wrap leading-relaxed"
            role="text"
          >
            {message.content}
          </div>

          {/* Timestamp */}
          <time
            className={`text-xs mt-2 block ${
              isUser ? "text-blue-200" : "text-gray-500"
            }`}
            dateTime={message.timestamp.toISOString()}
            title={message.timestamp.toLocaleString()}
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            })}
          </time>
        </div>

        {/* Dashboard update indicator for assistant messages */}
        {!isUser && message.metadata?.dashboardUpdated && (
          <div
            className="border-t border-gray-100 px-4 py-3 bg-green-50"
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center gap-2">
              <svg
                className="w-4 h-4 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <span className="text-xs font-medium text-green-700">
                Dashboard automatically updated
              </span>
              {message.metadata?.chartConfig && (
                <span className="text-xs text-green-600">
                  • {message.metadata.chartConfig.type} chart added
                </span>
              )}
            </div>
          </div>
        )}

        {/* Chart preview for assistant messages */}
        {!isUser &&
          message.metadata?.chartConfig &&
          message.metadata?.chartData && (
            <section
              className="border-t border-gray-100 p-4 bg-gray-50"
              aria-labelledby={`chart-preview-${message.id}`}
            >
              <h3 id={`chart-preview-${message.id}`} className="mb-2">
                <span className="text-xs font-medium text-gray-600">
                  Visualization Preview
                </span>
              </h3>
              <div className="bg-white rounded-lg p-3 border border-gray-200">
                <div
                  role="img"
                  aria-label={`${message.metadata.chartConfig.type} chart showing data visualization`}
                >
                  <ChartRenderer
                    data={message.metadata.chartData}
                    config={message.metadata.chartConfig}
                    width={400}
                    height={250}
                  />
                </div>
              </div>
            </section>
          )}

        {/* Insights section for assistant messages */}
        {!isUser &&
          message.metadata?.insights &&
          message.metadata.insights.length > 0 && (
            <section
              className="border-t border-gray-100 px-4 py-3 bg-gray-50"
              aria-labelledby={`insights-${message.id}`}
            >
              <h3
                id={`insights-${message.id}`}
                className="flex items-center gap-2 mb-2"
              >
                <svg
                  className="w-4 h-4 text-blue-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
                <span className="text-xs font-medium text-gray-700">
                  Key Insights
                </span>
              </h3>
              <ul className="space-y-1" role="list">
                {message.metadata.insights.map((insight, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2"
                    role="listitem"
                  >
                    <span
                      className="text-blue-500 mt-1 text-xs"
                      aria-hidden="true"
                    >
                      •
                    </span>
                    <span className="text-xs text-gray-700 leading-relaxed">
                      {insight}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

        {/* Follow-up questions section for assistant messages */}
        {!isUser &&
          message.metadata?.followUpQuestions &&
          message.metadata.followUpQuestions.length > 0 && (
            <section
              className="border-t border-gray-100 px-4 py-3 bg-blue-50"
              aria-labelledby={`followup-${message.id}`}
            >
              <h3
                id={`followup-${message.id}`}
                className="flex items-center gap-2 mb-3"
              >
                <svg
                  className="w-4 h-4 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-xs font-medium text-blue-700">
                  You might also ask
                </span>
              </h3>
              <div className="space-y-2" role="list">
                {message.metadata.followUpQuestions
                  .slice(0, 3)
                  .map((question, index) => (
                    <button
                      key={index}
                      onClick={() => onFollowUpClick?.(question)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onFollowUpClick?.(question);
                        }
                      }}
                      className="block w-full text-left px-3 py-2 text-xs text-blue-700 bg-white hover:bg-blue-100 focus:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md transition-colors border border-blue-200 hover:border-blue-300"
                      data-testid={`follow-up-${index}`}
                      role="listitem"
                      aria-label={`Follow-up question: ${question}`}
                    >
                      <span className="font-medium">"{question}"</span>
                    </button>
                  ))}
              </div>
            </section>
          )}
      </div>
    </article>
  );
}
