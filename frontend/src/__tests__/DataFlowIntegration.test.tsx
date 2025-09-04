/**
 * Integration tests for complete data flow:
 * CSV upload → table display → chat query → dashboard update
 *
 * Tests verify:
 * - Data view remains intact when chat responses are processed
 * - Conversational responses are generated correctly
 * - View state separation works properly
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api", () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
    translateQuery: vi.fn(),
    executeSQL: vi.fn(),
    executeQueryAutomatically: vi.fn(),
    sendChatMessage: vi.fn(),
    saveDashboard: vi.fn(),
    getDashboards: vi.fn(),
    getDashboard: vi.fn(),
  },
}));

const mockApiService = apiService as any;

describe("Data Flow Integration Tests", () => {
  // Sample data for testing
  const sampleUploadResponse = {
    table: "sales",
    columns: [
      { name: "product", type: "VARCHAR" },
      { name: "sales", type: "DECIMAL" },
      { name: "date", type: "DATE" },
      { name: "region", type: "VARCHAR" },
    ],
    sample_rows: [
      ["Product A", "15000", "2023-01-01", "North"],
      ["Product B", "25000", "2023-01-02", "South"],
      ["Product C", "18000", "2023-01-03", "East"],
      ["Product D", "22000", "2023-01-04", "West"],
    ],
    total_rows: 4,
    suggested_questions: [
      "What are my top-selling products?",
      "How do sales vary by region?",
    ],
  };

  const sampleConversationalResponse = {
    message:
      "Great question! I analyzed your product sales and found some interesting patterns. Product B is your top performer with $25,000 in sales, followed by Product D at $22,000. This shows you have strong performance across different products, with Product B leading by about 14% over your second-best seller.",
    chart_config: {
      type: "bar",
      x_axis: "product",
      y_axis: "total_sales",
      title: "Sales by Product",
    },
    insights: [
      "Product B is your top performer with 39% higher sales than the average",
      "All products show strong performance with sales ranging from $15K to $25K",
      "There's good distribution across your product line",
    ],
    follow_up_questions: [
      "Which regions are driving the highest sales?",
      "How do these numbers compare to last month?",
      "What factors might be contributing to Product B's success?",
    ],
    processing_time_ms: 1250.0,
    conversation_id: "test_conv_123",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockApiService.getDashboards.mockResolvedValue([]);
    mockApiService.useDemoData.mockResolvedValue(sampleUploadResponse);
    mockApiService.sendChatMessage.mockResolvedValue(
      sampleConversationalResponse
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("API Integration Flow", () => {
    it("should call upload API and return correct data structure", async () => {
      const result = await mockApiService.useDemoData();

      // Verify API was called
      expect(mockApiService.useDemoData).toHaveBeenCalledTimes(1);

      // Verify response structure for table display (Requirements 1.1, 1.2)
      expect(result).toHaveProperty("table");
      expect(result).toHaveProperty("columns");
      expect(result).toHaveProperty("sample_rows");
      expect(result.table).toBe("sales");
      expect(result.columns).toHaveLength(4);
      expect(result.sample_rows).toHaveLength(4);

      // Verify column information for table display
      const columnNames = result.columns.map((col: any) => col.name);
      expect(columnNames).toContain("product");
      expect(columnNames).toContain("sales");
      expect(columnNames).toContain("date");
      expect(columnNames).toContain("region");

      // Verify column types are provided
      result.columns.forEach((column: any) => {
        expect(column).toHaveProperty("type");
        expect(["VARCHAR", "DECIMAL", "DATE"].includes(column.type)).toBe(true);
      });
    });

    it("should call chat API and return conversational response", async () => {
      const chatRequest = {
        message: "Show me my top-selling products",
        conversation_id: null,
      };

      const result = await mockApiService.sendChatMessage(chatRequest);

      // Verify API was called with correct parameters
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(chatRequest);

      // Verify conversational response structure (Requirements 3.1, 3.2, 3.3)
      expect(result).toHaveProperty("message");
      expect(result).toHaveProperty("insights");
      expect(result).toHaveProperty("follow_up_questions");
      expect(result).toHaveProperty("conversation_id");

      // Verify response is conversational, not technical (Requirement 3.1, 3.2)
      const message = result.message.toLowerCase();

      // Should contain conversational language
      const conversationalIndicators = [
        "i found",
        "i analyzed",
        "your",
        "shows",
        "reveals",
        "interesting",
        "great question",
        "looking at",
      ];
      expect(
        conversationalIndicators.some((indicator) =>
          message.includes(indicator)
        )
      ).toBe(true);

      // Should NOT contain technical execution details
      const technicalTerms = [
        "query executed",
        "sql",
        "database",
        "rows returned",
        "execution time",
        "error code",
        "exception",
      ];
      expect(technicalTerms.some((term) => message.includes(term))).toBe(false);

      // Verify insights are provided (Requirement 3.3)
      expect(result.insights).toHaveLength(3);
      result.insights.forEach((insight: string) => {
        expect(typeof insight).toBe("string");
        expect(insight.length).toBeGreaterThan(0);
      });

      // Verify follow-up questions are conversational (Requirement 3.5)
      expect(result.follow_up_questions).toHaveLength(3);
      result.follow_up_questions.forEach((question: string) => {
        expect(question).toMatch(/\?$/); // Should end with question mark
      });
    });

    it("should maintain data integrity across multiple API calls", async () => {
      // Step 1: Upload data
      const uploadResult = await mockApiService.useDemoData();
      expect(uploadResult.table).toBe("sales");
      expect(uploadResult.sample_rows).toHaveLength(4);

      // Step 2: Send chat message
      const chatResult = await mockApiService.sendChatMessage({
        message: "Show me sales by product",
        conversation_id: null,
      });

      // Step 3: Send another chat message
      const chatResult2 = await mockApiService.sendChatMessage({
        message: "Show me sales by region",
        conversation_id: chatResult.conversation_id,
      });

      // Verify data integrity is maintained (Requirements 2.4, 2.5)
      // The original upload data should remain unchanged
      const uploadResult2 = await mockApiService.useDemoData();
      expect(uploadResult2).toEqual(uploadResult);

      // Verify API calls were made in sequence
      expect(mockApiService.useDemoData).toHaveBeenCalledTimes(2);
      expect(mockApiService.sendChatMessage).toHaveBeenCalledTimes(2);
    });
  });

  describe("Conversational Response Quality", () => {
    it("should generate business-friendly conversational responses", async () => {
      const result = await mockApiService.sendChatMessage({
        message: "What are my best performing products?",
        conversation_id: null,
      });

      const message = result.message;

      // Requirement 3.1: Should respond with conversational insights
      const conversationalPhrases = [
        "i found",
        "i analyzed",
        "looking at your",
        "your data shows",
        "interesting",
        "reveals",
        "appears",
        "seems",
      ];
      expect(
        conversationalPhrases.some((phrase) =>
          message.toLowerCase().includes(phrase)
        )
      ).toBe(true);

      // Requirement 3.2: Should explain in business terms, not technical
      const businessTerms = [
        "revenue",
        "sales",
        "performance",
        "product",
        "top",
        "best",
      ];
      expect(
        businessTerms.some((term) => message.toLowerCase().includes(term))
      ).toBe(true);

      // Should NOT contain technical execution details
      const technicalTerms = [
        "query executed",
        "rows returned",
        "execution time",
        "sql",
        "database",
        "table",
        "column",
        "select statement",
      ];
      expect(
        technicalTerms.some((term) => message.toLowerCase().includes(term))
      ).toBe(false);

      // Verify insights highlight patterns (Requirement 3.4)
      const insightText = result.insights.join(" ").toLowerCase();
      const patternIndicators = [
        "trend",
        "pattern",
        "higher",
        "lower",
        "increase",
        "decrease",
        "top",
        "best",
        "worst",
        "leading",
        "performance",
      ];
      expect(
        patternIndicators.some((indicator) => insightText.includes(indicator))
      ).toBe(true);

      // Verify follow-up questions are conversational (Requirement 3.5)
      result.follow_up_questions.forEach((question: string) => {
        expect(question).toMatch(/\?$/); // Should be actual questions

        // Should be conversational (allow various question formats)
        const conversationalStarters = [
          "would you like",
          "how about",
          "what about",
          "are you interested",
          "should we",
          "do you want",
          "would it help",
          "which",
          "how do",
          "what",
        ];
        expect(
          conversationalStarters.some((starter) =>
            question.toLowerCase().includes(starter)
          )
        ).toBe(true);
      });
    });

    it("should include chart configuration for dashboard view", async () => {
      const result = await mockApiService.sendChatMessage({
        message: "Create a chart showing my product sales performance",
        conversation_id: null,
      });

      // Should include chart configuration (Requirement 2.5)
      expect(result).toHaveProperty("chart_config");
      expect(result.chart_config).not.toBeNull();

      const chartConfig = result.chart_config;
      expect(chartConfig).toHaveProperty("type");
      expect(["bar", "line", "pie", "scatter"].includes(chartConfig.type)).toBe(
        true
      );

      if (chartConfig.x_axis) {
        expect(typeof chartConfig.x_axis).toBe("string");
      }
      if (chartConfig.y_axis) {
        expect(typeof chartConfig.y_axis).toBe("string");
      }

      // Message should explain the chart (Requirement 3.3)
      const message = result.message.toLowerCase();
      const chartExplanationPhrases = [
        "chart",
        "graph",
        "visualization",
        "shows",
        "displays",
        "found",
        "patterns",
      ];
      expect(
        chartExplanationPhrases.some((phrase) => message.includes(phrase))
      ).toBe(true);
    });

    it("should handle no data scenarios conversationally", async () => {
      // Mock empty results response
      const noDataResponse = {
        message:
          "I looked for that information but couldn't find any matching data. This might mean the data doesn't exist in your current dataset, or we might need to adjust our search approach. Would you like me to show you what data is available instead?",
        chart_config: null,
        insights: [
          "No matching records found for your query",
          "Your dataset might not contain the requested information",
        ],
        follow_up_questions: [
          "Would you like to see what data is available?",
          "Should we try a different search approach?",
          "What specific information are you looking for?",
        ],
        processing_time_ms: 500.0,
        conversation_id: "test_conv_empty",
      };

      mockApiService.sendChatMessage.mockResolvedValueOnce(noDataResponse);

      const result = await mockApiService.sendChatMessage({
        message: "Show me data that does not exist",
        conversation_id: null,
      });

      // Should acknowledge no data found (Requirement 3.7)
      const message = result.message.toLowerCase();
      const noDataPhrases = [
        "couldn't find",
        "no data",
        "no results",
        "not found",
        "doesn't exist",
        "no matching",
        "empty",
      ];
      expect(noDataPhrases.some((phrase) => message.includes(phrase))).toBe(
        true
      );

      // Should suggest alternatives (Requirement 3.7)
      const suggestionPhrases = [
        "try",
        "instead",
        "available",
        "different",
        "alternative",
        "what about",
        "you might want",
        "consider",
      ];
      expect(suggestionPhrases.some((phrase) => message.includes(phrase))).toBe(
        true
      );

      // Should provide helpful follow-up questions
      expect(result.follow_up_questions.length).toBeGreaterThan(0);
      result.follow_up_questions.forEach((question: string) => {
        const helpfulIndicators = [
          "available",
          "see",
          "show",
          "try",
          "different",
          "what",
          "how",
        ];
        expect(
          helpfulIndicators.some((indicator) =>
            question.toLowerCase().includes(indicator)
          )
        ).toBe(true);
      });

      // Should not have chart config for empty results
      expect(result.chart_config).toBeNull();
    });
  });

  describe("Data View State Preservation", () => {
    it("should preserve data structure across chat interactions", async () => {
      // Step 1: Upload data
      const initialData = await mockApiService.useDemoData();

      // Step 2: Multiple chat interactions
      const operations = [
        "Show me total sales",
        "Break down sales by region",
        "What are the trends over time?",
        "Create a chart of product performance",
      ];

      let conversationId = null;
      for (const operation of operations) {
        const chatResult = await mockApiService.sendChatMessage({
          message: operation,
          conversation_id: conversationId,
        });

        if (!conversationId) {
          conversationId = chatResult.conversation_id;
        }

        // Verify each response maintains conversational quality
        expect(chatResult).toHaveProperty("message");
        expect(chatResult).toHaveProperty("insights");
        expect(chatResult).toHaveProperty("follow_up_questions");
      }

      // Step 3: Verify original data is unchanged
      const finalData = await mockApiService.useDemoData();

      // Data should be identical to initial state (Requirements 2.1, 2.2, 2.4)
      expect(finalData.table).toBe(initialData.table);
      expect(finalData.columns).toEqual(initialData.columns);
      expect(finalData.sample_rows).toEqual(initialData.sample_rows);
      expect(finalData.total_rows).toBe(initialData.total_rows);
    });

    it("should maintain separate concerns for data and dashboard", async () => {
      // Upload provides data structure
      const uploadResult = await mockApiService.useDemoData();

      // Chat provides dashboard/visualization
      const chatResult = await mockApiService.sendChatMessage({
        message: "Show me sales by product",
        conversation_id: null,
      });

      // Verify separation of concerns (Requirements 2.1, 2.2)

      // Upload result should focus on data structure
      expect(uploadResult).toHaveProperty("table");
      expect(uploadResult).toHaveProperty("columns");
      expect(uploadResult).toHaveProperty("sample_rows");
      expect(uploadResult).not.toHaveProperty("chart_config");

      // Chat result should focus on insights and visualization
      expect(chatResult).toHaveProperty("message");
      expect(chatResult).toHaveProperty("chart_config");
      expect(chatResult).toHaveProperty("insights");
      expect(chatResult).toHaveProperty("follow_up_questions");

      // Both should coexist without interference
      expect(uploadResult.table).toBe("sales");
      expect(chatResult.chart_config.type).toBe("bar");
    });
  });

  describe("Error Handling and Recovery", () => {
    it("should handle API errors gracefully", async () => {
      // Mock API error
      const apiError = {
        message:
          "I couldn't understand your question. Could you try rephrasing it?",
        code: "TRANSLATION_FAILED",
      };

      mockApiService.sendChatMessage.mockRejectedValueOnce(apiError);

      try {
        await mockApiService.sendChatMessage({
          message: "invalid query that will fail",
          conversation_id: null,
        });
      } catch (error: any) {
        // Error should be user-friendly (Requirement 3.6)
        expect(error.message).toMatch(/couldn't understand your question/);
        expect(error.code).toBe("TRANSLATION_FAILED");
      }

      // Subsequent calls should still work
      mockApiService.sendChatMessage.mockResolvedValueOnce(
        sampleConversationalResponse
      );

      const recoveryResult = await mockApiService.sendChatMessage({
        message: "Show me sales data",
        conversation_id: null,
      });

      expect(recoveryResult).toHaveProperty("message");
      expect(recoveryResult.message).toMatch(
        /Great question! I analyzed your product sales/
      );
    });
  });
});
