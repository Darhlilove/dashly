import { useState, useCallback, useRef, useEffect } from "react";
import { apiService } from "../services/api";
import {
  ChatRequest,
  ConversationalResponse,
  ApiError,
  ConversationHistory,
} from "../types/api";
import { ChatMessage } from "../components/MessageRenderer";
import { generateId } from "../utils";

interface UseChatOptions {
  onError?: (error: ApiError) => void;
  onSuccess?: (response: ConversationalResponse) => void;
  persistHistory?: boolean; // Whether to persist conversation history
  conversationId?: string; // Existing conversation ID to restore
}

interface UseChatReturn {
  messages: ChatMessage[];
  isProcessing: boolean;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  conversationId: string | undefined;
  loadConversationHistory: (conversationId: string) => Promise<void>;
  isLoadingHistory: boolean;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const conversationIdRef = useRef<string | undefined>(options.conversationId);
  const { persistHistory = true } = options;

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  // Load conversation history on mount if conversation ID is provided
  useEffect(() => {
    if (options.conversationId && persistHistory) {
      loadConversationHistory(options.conversationId);
    }
  }, [options.conversationId, persistHistory]);

  // Save conversation ID to localStorage for session persistence
  useEffect(() => {
    if (conversationIdRef.current && persistHistory) {
      localStorage.setItem("dashly_conversation_id", conversationIdRef.current);
    }
  }, [conversationIdRef.current, persistHistory]);

  // Restore conversation ID from localStorage on mount
  useEffect(() => {
    if (persistHistory && !conversationIdRef.current) {
      const savedConversationId = localStorage.getItem(
        "dashly_conversation_id"
      );
      if (savedConversationId) {
        conversationIdRef.current = savedConversationId;
        loadConversationHistory(savedConversationId);
      }
    }
  }, [persistHistory]);

  const loadConversationHistory = useCallback(
    async (conversationId: string) => {
      if (!conversationId || !persistHistory) {
        return;
      }

      setIsLoadingHistory(true);
      try {
        const history = await apiService.getConversationHistory(conversationId);

        // Convert API messages to ChatMessage format
        const chatMessages: ChatMessage[] = history.messages.map((msg) => ({
          id: msg.id,
          type: msg.type,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          metadata: {
            chartConfig: msg.metadata?.chart_config,
            insights: msg.metadata?.insights,
            followUpQuestions: msg.metadata?.follow_up_questions,
          },
        }));

        setMessages(chatMessages);
        conversationIdRef.current = conversationId;

        console.log(
          `Loaded ${chatMessages.length} messages from conversation ${conversationId}`
        );
      } catch (error) {
        console.error("Failed to load conversation history:", error);
        // Don't show error to user for history loading failures
        // Just continue with empty conversation
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [persistHistory]
  );

  const sendMessage = useCallback(
    async (messageText: string) => {
      if (!messageText.trim() || isProcessing) {
        return;
      }

      setIsProcessing(true);

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: generateId(),
        type: "user",
        content: messageText.trim(),
        timestamp: new Date(),
      };
      addMessage(userMessage);

      try {
        // Send chat request
        const request: ChatRequest = {
          message: messageText.trim(),
          conversation_id: conversationIdRef.current,
        };

        const response = await apiService.sendChatMessage(request);

        // Store conversation ID for future messages
        conversationIdRef.current = response.conversation_id;

        // Add assistant response
        const assistantMessage: ChatMessage = {
          id: generateId(),
          type: "assistant",
          content: response.message,
          timestamp: new Date(),
          metadata: {
            chartConfig: response.chart_config,
            insights: response.insights,
            followUpQuestions: response.follow_up_questions,
          },
        };
        addMessage(assistantMessage);

        // Call success callback if provided
        options.onSuccess?.(response);
      } catch (error) {
        const apiError = error as ApiError;

        // Add error message to chat
        const errorMessage: ChatMessage = {
          id: generateId(),
          type: "assistant",
          content:
            apiError.message ||
            "I'm having trouble processing your message right now. Please try again.",
          timestamp: new Date(),
          metadata: {
            insights: ["There was an issue processing your request."],
            followUpQuestions: [
              "Try rephrasing your question",
              "What would you like to know about your data?",
              "Should we try a different approach?",
            ],
          },
        };
        addMessage(errorMessage);

        // Call error callback if provided
        options.onError?.(apiError);
      } finally {
        setIsProcessing(false);
      }
    },
    [isProcessing, addMessage, options]
  );

  const clearMessages = useCallback(async () => {
    // Clear from backend if we have a conversation ID and persistence is enabled
    if (conversationIdRef.current && persistHistory) {
      try {
        await apiService.clearConversation(conversationIdRef.current);
        localStorage.removeItem("dashly_conversation_id");
      } catch (error) {
        console.error("Failed to clear conversation from backend:", error);
        // Continue with local clearing even if backend fails
      }
    }

    setMessages([]);
    conversationIdRef.current = undefined;
  }, [persistHistory]);

  return {
    messages,
    isProcessing,
    sendMessage,
    clearMessages,
    conversationId: conversationIdRef.current,
    loadConversationHistory,
    isLoadingHistory,
  };
}
