import { vi } from "vitest";

// Mock the API service using a factory function
vi.mock("../services/api", () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
    translateQuery: vi.fn(),
    executeSQL: vi.fn(),
    saveDashboard: vi.fn(),
    getDashboards: vi.fn().mockResolvedValue([]),
  },
}));

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import { ApiError } from "../types/api";
import { apiService } from "../services/api";

// Mock console methods
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  console.error = vi.fn();
  console.warn = vi.fn();
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

describe("Error Handling Integration", () => {
  it("should handle file upload errors gracefully", async () => {
    const uploadError: ApiError = {
      message: "Internal server error",
      code: "500",
    };

    vi.mocked(apiService.uploadFile).mockRejectedValue(uploadError);

    render(<App />);

    // Create a test file
    const file = new File(["test,data\n1,2"], "test.csv", { type: "text/csv" });

    // Find file input and upload file
    const fileInput = screen.getByTestId("file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Click upload button
    const uploadButton = screen.getByTestId("upload-button");
    fireEvent.click(uploadButton);

    // Wait for error toast to appear
    await waitFor(() => {
      expect(
        screen.getByText(/upload failed.*internal server error/i)
      ).toBeInTheDocument();
    });

    // Should still be in upload phase
    expect(screen.getByTestId("upload-widget")).toBeInTheDocument();
  });

  it("should handle demo data loading errors", async () => {
    const demoError: ApiError = {
      message: "Internal server error",
      code: "500",
    };

    vi.mocked(apiService.useDemoData).mockRejectedValue(demoError);

    render(<App />);

    // Click demo data button
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    // Wait for error toast to appear
    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*internal server error/i)
      ).toBeInTheDocument();
    });

    // Should still be in upload phase
    expect(screen.getByTestId("upload-widget")).toBeInTheDocument();
  });

  it("should handle query translation errors", async () => {
    // Mock successful upload first
    mockApiService.useDemoData.mockResolvedValue({
      table: "test_table",
      columns: [
        { name: "id", type: "INTEGER" },
        { name: "name", type: "VARCHAR" },
      ],
    });

    const translationError: ApiError = {
      message: "Invalid query format",
      code: "422",
    };

    mockApiService.translateQuery.mockRejectedValue(translationError);

    render(<App />);

    // Upload demo data to get to query phase
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Enter a query
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "Show me the data" } });

    // Click generate button
    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    // Wait for error toast to appear
    await waitFor(() => {
      expect(
        screen.getByText(/query translation failed.*invalid query format/i)
      ).toBeInTheDocument();
    });

    // Should still be in query phase
    expect(screen.getByTestId("query-input")).toBeInTheDocument();
  });

  it("should show loading states during API calls", async () => {
    // Mock slow upload response
    mockApiService.useDemoData.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                table: "test_table",
                columns: [{ name: "id", type: "INTEGER" }],
              }),
            100
          )
        )
    );

    render(<App />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    // Should show loading state
    expect(screen.getByText("Loading demo data...")).toBeInTheDocument();
    expect(demoButton).toBeDisabled();

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("should handle network errors with appropriate messages", async () => {
    const networkError: ApiError = {
      message:
        "Network error: Unable to connect to server. Please check your internet connection.",
      code: "NETWORK_ERROR",
    };

    mockApiService.useDemoData.mockRejectedValue(networkError);

    render(<App />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*network error/i)
      ).toBeInTheDocument();
    });
  });

  it("should handle validation errors appropriately", async () => {
    const validationError: ApiError = {
      message: "Invalid file type. Please upload a CSV file.",
      code: "INVALID_FILE_TYPE",
    };

    mockApiService.uploadFile.mockRejectedValue(validationError);

    render(<App />);

    // Create an invalid file
    const file = new File(["test"], "test.txt", { type: "text/plain" });

    const fileInput = screen.getByTestId("file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    const uploadButton = screen.getByTestId("upload-button");
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(
        screen.getByText(/upload failed.*invalid file type/i)
      ).toBeInTheDocument();
    });
  });

  it("should recover from errors and allow retry", async () => {
    // First call fails, second succeeds
    mockApiService.useDemoData
      .mockRejectedValueOnce({
        message: "Temporary error",
        code: "500",
      })
      .mockResolvedValueOnce({
        table: "test_table",
        columns: [{ name: "id", type: "INTEGER" }],
      });

    render(<App />);

    const demoButton = screen.getByTestId("demo-data-button");

    // First attempt fails
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*temporary error/i)
      ).toBeInTheDocument();
    });

    // Should still be able to retry
    expect(demoButton).not.toBeDisabled();

    // Second attempt succeeds
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });
  });
});
