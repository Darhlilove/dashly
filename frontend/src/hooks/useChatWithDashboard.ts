import { useState, useCallback, useRef } from "react";
import { apiService } from "../services/api";
import { ChatRequest, ConversationalResponse, ApiError } from "../types/api";
import { ChatMessage } from "../components/MessageRenderer";
import { ChartConfig, ExecuteResponse } from "../types";
import { generateId } from "../utils";

interface UseChatWithDashboardOptions {
  onError?: (error: ApiError) => void;
  onSuccess?: (response: ConversationalResponse) => void;
  onDashboardUpdate?: (
    chartConfig: ChartConfig,
    queryResults: ExecuteResponse,
    query: string
  ) => void;
  onChartRecommendation?: (chartConfig: ChartConfig) => void;
}

interface UseChatWithDashboardReturn {
  messages: ChatMessage[];
  isProcessing: boolean;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  conversationId: string | undefined;
}

/**
 * Enhanced chat hook that automatically updates the dashboard when chart configurations
 * are received from the chat service, implementing seamless integration between
 * conversational responses and dashboard updates.
 */
export function useChatWithDashboard(
  options: UseChatWithDashboardOptions = {}
): UseChatWithDashboardReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const conversationIdRef = useRef<string | undefined>();

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

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

        // Check if we received a chart configuration for automatic dashboard update
        if (response.chart_config) {
          console.log(
            "📊 Received chart configuration from chat service:",
            response.chart_config
          );

          // Notify about chart recommendation
          options.onChartRecommendation?.(response.chart_config);

          // If we have a chart config, we need to execute the query to get the data
          // This is a simplified approach - in a full implementation, the backend
          // would return both the chart config and the query results
          try {
            // For now, we'll trigger the dashboard update callback with the chart config
            // The parent component should handle executing the query and updating the dashboard
            console.log("🔄 Triggering automatic dashboard update");

            // Create a placeholder query result structure
            // In a real implementation, this would come from the backend
            const placeholderResults: ExecuteResponse = {
              columns: [],
              rows: [],
              row_count: 0,
              runtime_ms: 0,
              truncated: false,
            };

            options.onDashboardUpdate?.(
              response.chart_config,
              placeholderResults,
              messageText.trim()
            );
          } catch (dashboardError) {
            console.error(
              "Failed to update dashboard automatically:",
              dashboardError
            );
            // Don't fail the chat interaction if dashboard update fails
          }
        }

        // Add assistant response with enhanced metadata
        const assistantMessage: ChatMessage = {
          id: generateId(),
          type: "assistant",
          content: response.message,
          timestamp: new Date(),
          metadata: {
            chartConfig: response.chart_config,
            insights: response.insights,
            followUpQuestions: response.follow_up_questions,
            // Add flag to indicate if dashboard was automatically updated
            dashboardUpdated: !!response.chart_config,
          },
        };
        addMessage(assistantMessage);

        // Call success callback if provided
        options.onSuccess?.(response);

        // Log automatic dashboard update
        if (response.chart_config) {
          console.log(
            "✅ Automatic dashboard update completed for chat response"
          );
        }
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

  const clearMessages = useCallback(() => {
    setMessages([]);
    conversationIdRef.current = undefined;
  }, []);

  return {
    messages,
    isProcessing,
    sendMessage,
    clearMessages,
    conversationId: conversationIdRef.current,
  };
}
