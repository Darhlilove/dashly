import {
  createUserFriendlyError,
  createErrorMessage,
  enhanceErrorMessage,
  generateContextualSuggestions,
  shouldAutoRetry,
  calculateRetryDelay,
} from "../errorHandling";
import { ApiError } from "../../types/api";

describe("Enhanced Error Handling", () => {
  describe("createUserFriendlyError", () => {
    it("should create user-friendly error for translation phase", () => {
      const apiError: ApiError = {
        message: "Failed to parse query",
        code: "TRANSLATION_FAILED",
        retryable: false,
      };

      const result = createUserFriendlyError(
        apiError,
        "translation",
        "show me sales data"
      );

      expect(result.phase).toBe("translation");
      expect(result.userFriendlyMessage).toBe(
        "I couldn't understand your question well enough to create a query."
      );
      expect(result.suggestions).toContain(
        "Try rephrasing your question more simply"
      );
      expect(result.recoveryActions).toBeDefined();
      expect(
        result.recoveryActions?.some((action) => action.type === "rephrase")
      ).toBe(true);
    });

    it("should create user-friendly error for execution phase", () => {
      const apiError: ApiError = {
        message: "Column 'invalid_column' not found",
        code: "COLUMN_NOT_FOUND",
        retryable: false,
      };

      const result = createUserFriendlyError(
        apiError,
        "execution",
        "show me invalid_column"
      );

      expect(result.phase).toBe("execution");
      expect(result.userFriendlyMessage).toBe(
        "I couldn't find a column that matches what you're asking about."
      );
      expect(result.suggestions).toContain(
        "Check the spelling of column names in your question"
      );
    });

    it("should create user-friendly error for network phase", () => {
      const apiError: ApiError = {
        message: "Network timeout",
        code: "NETWORK_ERROR",
        retryable: true,
      };

      const result = createUserFriendlyError(apiError, "network");

      expect(result.phase).toBe("network");
      expect(result.userFriendlyMessage).toBe(
        "I'm having trouble connecting to the server."
      );
      expect(result.retryable).toBe(true);
      expect(
        result.recoveryActions?.some((action) => action.type === "retry")
      ).toBe(true);
    });

    it("should enhance suggestions for long queries", () => {
      const longQuery =
        "show me all the sales data for the last 12 months broken down by region and product category with totals and averages";
      const apiError: ApiError = {
        message: "Query too complex",
        code: "TRANSLATION_FAILED",
        retryable: false,
      };

      const result = createUserFriendlyError(
        apiError,
        "translation",
        longQuery
      );

      expect(result.suggestions).toContain(
        "Your question is quite long - try making it shorter"
      );
    });

    it("should enhance suggestions for queries with multiple conditions", () => {
      const complexQuery = "show me sales and revenue and profit margins";
      const apiError: ApiError = {
        message: "Query too complex",
        code: "TRANSLATION_FAILED",
        retryable: false,
      };

      const result = createUserFriendlyError(
        apiError,
        "translation",
        complexQuery
      );

      expect(result.suggestions).toContain(
        "Try asking about one thing at a time instead of multiple things"
      );
    });
  });

  describe("createErrorMessage", () => {
    it("should create error message for conversation display", () => {
      const executionError = {
        message: "Column not found",
        code: "COLUMN_NOT_FOUND",
        phase: "execution" as const,
        originalError: { message: "Column 'test' not found" } as ApiError,
        userFriendlyMessage: "I couldn't find that column",
        suggestions: ["Check spelling", "Try different words"],
        retryable: false,
        recoveryActions: [
          {
            type: "rephrase" as const,
            label: "Rephrase",
            description: "Try asking differently",
          },
        ],
      };

      const result = createErrorMessage(executionError, "test query");

      expect(result.type).toBe("assistant");
      expect(result.isError).toBe(true);
      expect(result.errorPhase).toBe("execution");
      expect(result.userFriendlyMessage).toBe("I couldn't find that column");
      expect(result.suggestions).toEqual([
        "Check spelling",
        "Try different words",
      ]);
      expect(result.recoveryActions).toHaveLength(1);
    });
  });

  describe("enhanceErrorMessage", () => {
    it("should enhance SQL syntax errors", () => {
      const error: ApiError = {
        message: "Syntax error at line 1",
        code: "INVALID_SQL",
      };

      const result = enhanceErrorMessage(error, { phase: "execution" });

      expect(result).toBe(
        "I generated invalid SQL. This usually happens when the question is ambiguous or uses terms I don't recognize."
      );
    });

    it("should enhance column not found errors", () => {
      const error: ApiError = {
        message: "Column 'sales_amount' not found in table",
        code: "COLUMN_NOT_FOUND",
      };

      const result = enhanceErrorMessage(error);

      expect(result).toBe(
        'I couldn\'t find a column called "sales_amount" in your data. Check the spelling or try describing it differently.'
      );
    });

    it("should enhance timeout errors", () => {
      const error: ApiError = {
        message: "Query execution timeout",
        code: "TIMEOUT_ERROR",
      };

      const result = enhanceErrorMessage(error);

      expect(result).toBe(
        "Your query is taking too long to run. Try asking for less data or add filters to narrow down the results."
      );
    });

    it("should enhance network errors", () => {
      const error: ApiError = {
        message: "Network connection failed",
        code: "NETWORK_ERROR",
      };

      const result = enhanceErrorMessage(error);

      expect(result).toBe(
        "I'm having trouble connecting to the server. Please check your internet connection."
      );
    });

    it("should handle file upload errors", () => {
      const error: ApiError = {
        message: "File too large",
        code: "FILE_TOO_LARGE",
      };

      const result = enhanceErrorMessage(error);

      expect(result).toBe(
        "Your file is too large. Please upload a smaller CSV file (under 10MB)."
      );
    });
  });

  describe("generateContextualSuggestions", () => {
    it("should generate translation-specific suggestions", () => {
      const error: ApiError = {
        message: "Translation failed",
        code: "TRANSLATION_FAILED",
      };

      const suggestions = generateContextualSuggestions(
        error,
        "very long query with many words and complex structure",
        "translation"
      );

      // Check that we get translation-specific suggestions
      expect(suggestions.length).toBeGreaterThan(0);
      expect(
        suggestions.some(
          (s) =>
            s.includes("shorter") ||
            s.includes("simpler") ||
            s.includes("Show me")
        )
      ).toBe(true);
    });

    it("should generate execution-specific suggestions", () => {
      const error: ApiError = {
        message: "Column not found",
        code: "COLUMN_NOT_FOUND",
      };

      const suggestions = generateContextualSuggestions(
        error,
        "show me sales",
        "execution"
      );

      expect(suggestions).toContain(
        "Check if the column names in your question match your data"
      );
      expect(suggestions).toContain(
        "Try using different words to describe what you want"
      );
    });

    it("should generate network-specific suggestions", () => {
      const error: ApiError = {
        message: "Network error",
        code: "NETWORK_ERROR",
      };

      const suggestions = generateContextualSuggestions(
        error,
        undefined,
        "network"
      );

      expect(suggestions).toContain("Check your internet connection");
      expect(suggestions).toContain("Try again in a few moments");
    });

    it("should limit suggestions to 4 items", () => {
      const error: ApiError = {
        message: "Complex error",
        code: "UNKNOWN_ERROR",
      };

      const suggestions = generateContextualSuggestions(
        error,
        "test query",
        "translation"
      );

      expect(suggestions.length).toBeLessThanOrEqual(4);
    });
  });

  describe("shouldAutoRetry", () => {
    it("should auto-retry network errors", () => {
      const error: ApiError = {
        message: "Network error",
        code: "NETWORK_ERROR",
        retryable: true,
      };

      expect(shouldAutoRetry(error, 0)).toBe(true);
      expect(shouldAutoRetry(error, 1)).toBe(true);
      expect(shouldAutoRetry(error, 2)).toBe(false); // Max retries reached
    });

    it("should auto-retry server errors", () => {
      const error: ApiError = {
        message: "Internal server error",
        code: "INTERNAL_ERROR",
        retryable: true,
      };

      expect(shouldAutoRetry(error, 0)).toBe(true);
    });

    it("should not auto-retry validation errors", () => {
      const error: ApiError = {
        message: "Invalid SQL",
        code: "INVALID_SQL",
        retryable: false,
      };

      expect(shouldAutoRetry(error, 0)).toBe(false);
    });

    it("should not auto-retry after max attempts", () => {
      const error: ApiError = {
        message: "Network error",
        code: "NETWORK_ERROR",
        retryable: true,
      };

      expect(shouldAutoRetry(error, 3)).toBe(false);
    });
  });

  describe("calculateRetryDelay", () => {
    it("should calculate exponential backoff delay", () => {
      expect(calculateRetryDelay(0, 1000)).toBe(1000);
      expect(calculateRetryDelay(1, 1000)).toBe(2000);
      expect(calculateRetryDelay(2, 1000)).toBe(4000);
      expect(calculateRetryDelay(3, 1000)).toBe(8000);
    });

    it("should cap delay at maximum", () => {
      expect(calculateRetryDelay(10, 1000)).toBe(10000); // Capped at 10 seconds
    });

    it("should use default base delay", () => {
      expect(calculateRetryDelay(0)).toBe(1000);
      expect(calculateRetryDelay(1)).toBe(2000);
    });
  });
});
