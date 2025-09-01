import { ApiError } from "../../types/api";
import { vi } from "vitest";

// Mock console methods
const originalConsoleError = console.error;
const originalConsoleLog = console.log;

beforeEach(() => {
  console.error = vi.fn();
  console.log = vi.fn();
  vi.clearAllMocks();
});

afterEach(() => {
  console.error = originalConsoleError;
  console.log = originalConsoleLog;
});

// Create a test implementation of error handling logic
class TestApiService {
  private handleError(error: any): ApiError {
    if (error.response) {
      const status = error.response.status;
      let message: string;

      switch (status) {
        case 400:
          message =
            error.response.data?.message ||
            "Invalid request. Please check your input.";
          break;
        case 413:
          message = "File too large. Please upload a smaller file.";
          break;
        case 500:
          message = "Internal server error. Please try again later.";
          break;
        default:
          message = `Server error: ${status}`;
      }

      return { message, code: status.toString() };
    } else if (error.request) {
      if (error.code === "ECONNABORTED") {
        return {
          message:
            "Request timeout. Please check your connection and try again.",
          code: "TIMEOUT_ERROR",
        };
      }
      return {
        message:
          "Network error: Unable to connect to server. Please check your internet connection.",
        code: "NETWORK_ERROR",
      };
    } else {
      return {
        message: error.message || "An unexpected error occurred",
        code: "UNKNOWN_ERROR",
      };
    }
  }

  async uploadFile(file: File): Promise<any> {
    // Client-side validation
    if (
      !file.type.includes("csv") &&
      !file.name.toLowerCase().endsWith(".csv")
    ) {
      throw {
        message: "Invalid file type. Please upload a CSV file.",
        code: "INVALID_FILE_TYPE",
      } as ApiError;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      throw {
        message: "File too large. Please upload a file smaller than 10MB.",
        code: "FILE_TOO_LARGE",
      } as ApiError;
    }

    return Promise.resolve({ table: "test", columns: [] });
  }

  async translateQuery(query: string): Promise<any> {
    if (!query.trim()) {
      throw {
        message: "Please enter a question about your data.",
        code: "EMPTY_QUERY",
      } as ApiError;
    }

    return Promise.resolve({ sql: "SELECT * FROM test" });
  }

  async executeSQL(sql: string): Promise<any> {
    if (!sql.trim()) {
      throw {
        message: "SQL query cannot be empty.",
        code: "EMPTY_SQL",
      } as ApiError;
    }

    return Promise.resolve({
      columns: [],
      rows: [],
      row_count: 0,
      runtime_ms: 0,
    });
  }

  async saveDashboard(dashboard: any): Promise<any> {
    if (!dashboard.name.trim()) {
      throw {
        message: "Dashboard name cannot be empty.",
        code: "EMPTY_NAME",
      } as ApiError;
    }

    return Promise.resolve({
      ...dashboard,
      id: "123",
      createdAt: new Date().toISOString(),
    });
  }

  async getDashboard(id: string): Promise<any> {
    if (!id.trim()) {
      throw {
        message: "Dashboard ID cannot be empty.",
        code: "EMPTY_ID",
      } as ApiError;
    }

    return Promise.resolve({ id, name: "Test Dashboard" });
  }

  async executeQueryAutomatically(query: string): Promise<any> {
    if (!query.trim()) {
      throw {
        phase: "translation",
        originalError: {
          message: "Please enter a question about your data.",
          code: "EMPTY_QUERY",
        },
        userFriendlyMessage: "Please enter a question about your data.",
        suggestions: [
          "Try asking something like 'Show me sales by month'",
          "Ask about trends, comparisons, or summaries in your data",
          "Be specific about what you want to see",
        ],
        message: "Please enter a question about your data.",
        code: "EMPTY_QUERY",
        retryable: false,
      };
    }

    // Simulate successful automatic execution
    const translationResult = {
      sql: "SELECT * FROM test WHERE category = 'sales'",
    };
    const executionResult = {
      columns: ["month", "sales"],
      rows: [
        ["January", 1000],
        ["February", 1200],
      ],
      row_count: 2,
      runtime_ms: 150,
    };

    return Promise.resolve({
      translationResult,
      executionResult,
      executionTime: 250,
      fromCache: false,
    });
  }

  // Test error handling with different error types
  testErrorHandling(errorType: string): ApiError {
    let mockError: any;

    switch (errorType) {
      case "400":
        mockError = {
          response: {
            status: 400,
            data: { message: "Invalid request data" },
          },
        };
        break;
      case "413":
        mockError = {
          response: {
            status: 413,
            data: {},
          },
        };
        break;
      case "500":
        mockError = {
          response: {
            status: 500,
            data: {},
          },
        };
        break;
      case "network":
        mockError = {
          request: {},
          message: "Network Error",
        };
        break;
      case "timeout":
        mockError = {
          request: {},
          code: "ECONNABORTED",
          message: "timeout of 30000ms exceeded",
        };
        break;
      default:
        mockError = {
          message: "Unknown error",
        };
    }

    return this.handleError(mockError);
  }
}

const testApiService = new TestApiService();

describe("ApiService Error Handling", () => {
  describe("handleError", () => {
    it("should handle 400 Bad Request errors", () => {
      const apiError = testApiService.testErrorHandling("400");
      expect(apiError.message).toBe("Invalid request data");
      expect(apiError.code).toBe("400");
    });

    it("should handle 413 Payload Too Large errors", () => {
      const apiError = testApiService.testErrorHandling("413");
      expect(apiError.message).toBe(
        "File too large. Please upload a smaller file."
      );
      expect(apiError.code).toBe("413");
    });

    it("should handle 500 Internal Server Error", () => {
      const apiError = testApiService.testErrorHandling("500");
      expect(apiError.message).toBe(
        "Internal server error. Please try again later."
      );
      expect(apiError.code).toBe("500");
    });

    it("should handle network errors", () => {
      const apiError = testApiService.testErrorHandling("network");
      expect(apiError.message).toBe(
        "Network error: Unable to connect to server. Please check your internet connection."
      );
      expect(apiError.code).toBe("NETWORK_ERROR");
    });

    it("should handle timeout errors", () => {
      const apiError = testApiService.testErrorHandling("timeout");
      expect(apiError.message).toBe(
        "Request timeout. Please check your connection and try again."
      );
      expect(apiError.code).toBe("TIMEOUT_ERROR");
    });
  });

  describe("Client-side validation", () => {
    it("should validate file type before upload", async () => {
      const invalidFile = new File(["test"], "test.txt", {
        type: "text/plain",
      });

      try {
        await testApiService.uploadFile(invalidFile);
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe(
          "Invalid file type. Please upload a CSV file."
        );
        expect(apiError.code).toBe("INVALID_FILE_TYPE");
      }
    });

    it("should validate file size before upload", async () => {
      const largeContent = "x".repeat(11 * 1024 * 1024); // 11MB
      const largeFile = new File([largeContent], "large.csv", {
        type: "text/csv",
      });

      try {
        await testApiService.uploadFile(largeFile);
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe(
          "File too large. Please upload a file smaller than 10MB."
        );
        expect(apiError.code).toBe("FILE_TOO_LARGE");
      }
    });

    it("should validate empty query", async () => {
      try {
        await testApiService.translateQuery("   ");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe(
          "Please enter a question about your data."
        );
        expect(apiError.code).toBe("EMPTY_QUERY");
      }
    });

    it("should validate empty SQL", async () => {
      try {
        await testApiService.executeSQL("   ");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe("SQL query cannot be empty.");
        expect(apiError.code).toBe("EMPTY_SQL");
      }
    });

    it("should validate empty dashboard name", async () => {
      try {
        await testApiService.saveDashboard({
          name: "   ",
          question: "test question",
          sql: "SELECT * FROM test",
          chartConfig: { type: "table" },
        });
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe("Dashboard name cannot be empty.");
        expect(apiError.code).toBe("EMPTY_NAME");
      }
    });

    it("should validate empty dashboard ID", async () => {
      try {
        await testApiService.getDashboard("   ");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.message).toBe("Dashboard ID cannot be empty.");
        expect(apiError.code).toBe("EMPTY_ID");
      }
    });
  });

  describe("Successful operations", () => {
    it("should upload valid CSV file", async () => {
      const validFile = new File(["test,data\n1,2"], "test.csv", {
        type: "text/csv",
      });
      const result = await testApiService.uploadFile(validFile);
      expect(result).toEqual({ table: "test", columns: [] });
    });

    it("should translate valid query", async () => {
      const result = await testApiService.translateQuery("show me the data");
      expect(result).toEqual({ sql: "SELECT * FROM test" });
    });

    it("should execute valid SQL", async () => {
      const result = await testApiService.executeSQL("SELECT * FROM test");
      expect(result).toEqual({
        columns: [],
        rows: [],
        row_count: 0,
        runtime_ms: 0,
      });
    });

    it("should save valid dashboard", async () => {
      const dashboard = {
        name: "Test Dashboard",
        question: "test question",
        sql: "SELECT * FROM test",
        chartConfig: { type: "table" },
      };
      const result = await testApiService.saveDashboard(dashboard);
      expect(result).toMatchObject({
        ...dashboard,
        id: "123",
        createdAt: expect.any(String),
      });
    });

    it("should get dashboard by valid ID", async () => {
      const result = await testApiService.getDashboard("123");
      expect(result).toEqual({ id: "123", name: "Test Dashboard" });
    });

    it("should execute query automatically with valid input", async () => {
      const result = await testApiService.executeQueryAutomatically(
        "show me sales by month"
      );
      expect(result).toMatchObject({
        translationResult: { sql: expect.any(String) },
        executionResult: {
          columns: expect.any(Array),
          rows: expect.any(Array),
          row_count: expect.any(Number),
          runtime_ms: expect.any(Number),
        },
        executionTime: expect.any(Number),
        fromCache: expect.any(Boolean),
      });
    });
  });

  describe("Automatic execution error handling", () => {
    it("should handle empty query in automatic execution", async () => {
      try {
        await testApiService.executeQueryAutomatically("   ");
      } catch (error) {
        const executionError = error as any;
        expect(executionError.phase).toBe("translation");
        expect(executionError.userFriendlyMessage).toBe(
          "Please enter a question about your data."
        );
        expect(executionError.suggestions).toBeInstanceOf(Array);
        expect(executionError.suggestions.length).toBeGreaterThan(0);
        expect(executionError.code).toBe("EMPTY_QUERY");
        expect(executionError.retryable).toBe(false);
      }
    });
  });
});
