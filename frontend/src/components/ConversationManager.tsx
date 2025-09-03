import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";
import { ConversationSummary, ApiError } from "../types/api";

interface ConversationManagerProps {
  currentConversationId?: string;
  onConversationSelect?: (conversationId: string) => void;
  onNewConversation?: () => void;
  onClearConversation?: (conversationId: string) => void;
}

export default function ConversationManager({
  currentConversationId,
  onConversationSelect,
  onNewConversation,
  onClearConversation,
}: ConversationManagerProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // For now, we'll just show the current conversation
  // In a full implementation, we'd need an endpoint to list all conversations
  useEffect(() => {
    if (currentConversationId) {
      loadConversationSummary(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversationSummary = async (conversationId: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const summary = await apiService.getConversationSummary(conversationId);
      setConversations([summary]);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || "Failed to load conversation");
      console.error("Failed to load conversation summary:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearConversation = async (conversationId: string) => {
    if (
      !window.confirm(
        "Are you sure you want to clear this conversation? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      await apiService.clearConversation(conversationId);
      setConversations([]);
      onClearConversation?.(conversationId);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || "Failed to clear conversation");
      console.error("Failed to clear conversation:", err);
    }
  };

  const handleNewConversation = () => {
    setConversations([]);
    onNewConversation?.();
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Unknown";
    try {
      return new Date(dateString).toLocaleDateString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Unknown";
    }
  };

  return (
    <div className="p-4 border-b border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">Conversations</h3>
        <button
          onClick={handleNewConversation}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          title="Start new conversation"
        >
          + New
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-4">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      {error && (
        <div className="text-xs text-red-600 mb-2 p-2 bg-red-50 rounded">
          {error}
        </div>
      )}

      {conversations.length === 0 && !isLoading && !error && (
        <div className="text-xs text-gray-500 text-center py-4">
          No active conversation
        </div>
      )}

      {conversations.map((conversation) => (
        <div
          key={conversation.id}
          className={`p-3 rounded-lg border mb-2 ${
            conversation.id === currentConversationId
              ? "bg-blue-50 border-blue-200"
              : "bg-gray-50 border-gray-200 hover:bg-gray-100"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-900 mb-1">
                {conversation.first_question || "New conversation"}
              </div>
              <div className="text-xs text-gray-500">
                {conversation.message_count} messages •{" "}
                {formatDate(conversation.last_updated)}
              </div>
            </div>

            {conversation.id === currentConversationId && (
              <button
                onClick={() => handleClearConversation(conversation.id)}
                className="ml-2 text-xs text-red-600 hover:text-red-700"
                title="Clear conversation"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      ))}

      {/* Session info */}
      {currentConversationId && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div className="flex items-center gap-1 mb-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
              Session Active
            </div>
            <div className="text-xs">
              Your conversation is automatically saved and will be restored when
              you return.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
