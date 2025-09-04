// Tests for error message utilities

import {
  createUserFriendlyError,
  getErrorHelpText,
  shouldSuggestDataUpload,
} from "../errorMessages";
import { ApiError } from "../../types/api";

describe("Error Message Utilities", () => {
  describe("createUserFriendlyError", () => {
    it("should create user-friendly error for no data uploaded", () => {
      const apiError: ApiError = {
        message: "Table not found",
        code: "TABLE_NOT_FOUND",
        retryable: false,
      };

      const context = {
        hasData: false,
        userMessage: "Show me sales data",
      };

      const result = createUserFriendlyError(apiError, context);

      expect(result.errorPhase).toBe("data_not_found");
      expect(result.userFriendlyMessage).toContain("upload");
      expect(result.suggestions).toContain(
        "Click the upload button to add your CSV file"
      );
    });

    it("should create user-friendly error for column not found", () => {
      const apiError: ApiError = {
        message: "Column 'revenue' not found",
        code: "COLUMN_NOT_FOUND",
        retryable: false,
      };

      const context = {
        hasData: true,
        dataColumns: ["id", "date", "amount"],
        userMessage: "Show me revenue trends",
      };

      const result = createUserFriendlyError(apiError, context);

      expect(result.errorPhase).toBe("data_not_found");
      expect(result.userFriendlyMessage).toContain("specific information");
      expect(result.suggestions.some((s) => s.includes("different"))).toBe(
        true
      );
    });

    it("should create user-friendly error for timeout", () => {
      const apiError: ApiError = {
        message: "Query timeout after 30 seconds",
        code: "TIMEOUT_ERROR",
        retryable: true,
      };

      const context = {
        hasData: true,
        userMessage: "Show me complex analysis",
      };

      const result = createUserFriendlyError(apiError, context);

      expect(result.errorPhase).toBe("timeout");
      expect(result.userFriendlyMessage).toContain("longer to process");
      expect(result.retryable).toBe(true);
    });

    it("should create user-friendly error for network issues", () => {
      const apiError: ApiError = {
        message: "Network connection failed",
        code: "NETWORK_ERROR",
        retryable: true,
      };

      const context = {
        hasData: true, // Ensure we have data so it doesn't default to no-data case
      };

      const result = createUserFriendlyError(apiError, context);

      expect(result.errorPhase).toBe("network");
      expect(result.userFriendlyMessage).toContain("connection");
      expect(result.suggestions).toContain("Check your internet connection");
    });

    it("should generate recovery actions for retryable errors", () => {
      const apiError: ApiError = {
        message: "Service temporarily unavailable",
        code: "SERVICE_UNAVAILABLE",
        retryable: true,
      };

      const result = createUserFriendlyError(apiError);

      expect(result.recoveryActions).toBeDefined();
      expect(
        result.recoveryActions!.some((action) => action.type === "retry")
      ).toBe(true);
    });

    it("should generate context-specific suggestions", () => {
      const apiError: ApiError = {
        message: "Translation failed",
        code: "TRANSLATION_FAILED",
        retryable: false,
      };

      const context = {
        hasData: true,
        userMessage: "Show me sales data",
      };

      const result = createUserFriendlyError(apiError, context);

      expect(result.suggestions.some((s) => s.includes("sales"))).toBe(true);
    });
  });

  describe("getErrorHelpText", () => {
    it("should return help text for known error codes", () => {
      expect(getErrorHelpText("NO_DATA_UPLOADED")).toContain(
        "Upload a CSV file"
      );
      expect(getErrorHelpText("COLUMN_NOT_FOUND")).toContain("doesn't contain");
      expect(getErrorHelpText("TIMEOUT_ERROR")).toContain("too complex");
      expect(getErrorHelpText("NETWORK_ERROR")).toContain("connection issue");
    });

    it("should return null for unknown error codes", () => {
      expect(getErrorHelpText("UNKNOWN_ERROR_CODE")).toBeNull();
    });
  });

  describe("shouldSuggestDataUpload", () => {
    it("should suggest upload for no data errors", () => {
      const error: ApiError = {
        message: "No data available",
        code: "NO_DATA_UPLOADED",
      };

      expect(shouldSuggestDataUpload(error)).toBe(true);
    });

    it("should suggest upload for table not found errors", () => {
      const error: ApiError = {
        message: "Table not found",
        code: "TABLE_NOT_FOUND",
      };

      expect(shouldSuggestDataUpload(error)).toBe(true);
    });

    it("should not suggest upload for other errors", () => {
      const error: ApiError = {
        message: "Network error",
        code: "NETWORK_ERROR",
      };

      expect(shouldSuggestDataUpload(error)).toBe(false);
    });
  });
});
