import React, { useState, useRef, useEffect } from "react";

// Chat-specific types for the simplified interface
export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: {
    insights?: string[];
    followUpQuestions?: string[];
  };
}

interface ConversationInterfaceProps {
  onSendMessage: (message: string) => void;
  messages: ChatMessage[];
  isProcessing: boolean;
  suggestedQuestions?: string[];
  placeholder?: string;
}

export default function ConversationInterface({
  onSendMessage,
  messages,
  isProcessing,
  suggestedQuestions = [],
  placeholder = "Ask me anything about your data...",
}: ConversationInterfaceProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      onSendMessage(input.trim());
      setInput("");
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    if (!isProcessing) {
      onSendMessage(question);
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
              <p className="text-gray-600 text-sm">
                Ask me questions in plain English and I'll help you discover
                insights from your data.
              </p>

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
              <MessageRenderer key={message.id} message={message} />
            ))}

            {/* Typing indicator */}
            {isProcessing && <TypingIndicator />}
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

// Message Renderer Component
interface MessageRendererProps {
  message: ChatMessage;
}

function MessageRenderer({ message }: MessageRendererProps) {
  const isUser = message.type === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-3 rounded-lg ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900 border border-gray-200"
        }`}
      >
        {/* Message content */}
        <div className="text-sm whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>

        {/* Insights (for assistant messages) */}
        {!isUser &&
          message.metadata?.insights &&
          message.metadata.insights.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs font-medium text-gray-600 mb-2">
                Key Insights:
              </div>
              <ul className="text-xs text-gray-700 space-y-1">
                {message.metadata.insights.map((insight, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">•</span>
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        {/* Follow-up questions (for assistant messages) */}
        {!isUser &&
          message.metadata?.followUpQuestions &&
          message.metadata.followUpQuestions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs font-medium text-gray-600 mb-2">
                You might also ask:
              </div>
              <div className="space-y-1">
                {message.metadata.followUpQuestions
                  .slice(0, 2)
                  .map((question, index) => (
                    <div key={index} className="text-xs text-blue-600 italic">
                      "{question}"
                    </div>
                  ))}
              </div>
            </div>
          )}

        {/* Timestamp */}
        <div
          className={`text-xs mt-2 ${
            isUser ? "text-blue-200" : "text-gray-500"
          }`}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })}
        </div>
      </div>
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
