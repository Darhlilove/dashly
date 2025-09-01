import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import App from "../App";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api", () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
    translateQuery: vi.fn(),
    executeSQL: vi.fn(),
    executeQueryAutomatically: vi.fn(),
    saveDashboard: vi.fn(),
    getDashboards: vi.fn(),
    getDashboard: vi.fn(),
  },
}));

// Mock chart components to avoid Recharts rendering issues in tests
vi.mock("../components/ChartRenderer", () => ({
  default: ({ data, config, onSaveDashboard }: any) => (
    <div data-testid="chart-renderer">
      <div>Chart Type: {config?.type || "auto"}</div>
      <div>Columns: {data?.columns?.join(", ") || "none"}</div>
      <div>Rows: {data?.rows?.length || 0}</div>
      {onSaveDashboard && (
        <button onClick={() => onSaveDashboard("Test Dashboard")}>
          Save Dashboard
        </button>
      )}
    </div>
  ),
}));

const mockApiService = apiService as any;

describe("End-to-End Automatic Query Execution Integration Tests", () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();

    // Default mock implementations
    mockApiService.getDashboards.mockResolvedValue([]);
    mockApiService.useDemoData.mockResolvedValue({
      table: "demo_table",
      columns: [
        { name: "date", type: "DATE" },
        { name: "sales", type: "DECIMAL" },
        { name: "category", type: "VARCHAR" },
        { name: "region", type: "VARCHAR" },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Complete Flow: Natural Language → Dashboard Display", () => {
    it("should execute complete automatic flow from query to dashboard", async () => {
      // Mock successful automatic execution
      mockApiService.executeQueryAutomatically.mockResolvedValue({
        translationResult: {
          sql: "SELECT date, SUM(sales) as total_sales FROM demo_table GROUP BY date ORDER BY date",
        },
        executionResult: {
          columns: ["date", "total_sales"],
          rows: [
            ["2023-01-01", 1000],
            ["2023-02-01", 2000],
            ["2023-03-01", 1500],
          ],
          row_count: 3,
          runtime_ms: 45,
        },
        executionTime: 150,
        fromCache: false,
      });

      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      // Enter natural language query
      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, {
        target: { value: "monthly sales trend" },
      });

      // Execute query
      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      // Verify automatic execution was called (core requirement)
      await waitFor(() => {
        expect(mockApiService.executeQueryAutomatically).toHaveBeenCalledWith(
          "monthly sales trend"
        );
      });

      // Verify dashboard is rendered (main end-to-end requirement)
      await waitFor(
        () => {
          expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
        },
        { timeout: 10000 }
      );

      // Verify chart displays correct data
      expect(
        screen.getByText("Columns: date, total_sales")
      ).toBeInTheDocument();
      expect(screen.getByText("Rows: 3")).toBeInTheDocument();

      // Verify no SQL modal was shown (key automatic execution behavior)
      expect(screen.queryByTestId("sql-modal")).not.toBeInTheDocument();
    });
  });

  describe("Error Handling Scenarios in Automatic Execution", () => {
    it("should handle translation errors gracefully without showing chart", async () => {
      mockApiService.executeQueryAutomatically.mockRejectedValue({
        message: "Unable to translate query: ambiguous column reference",
        code: "TRANSLATION_ERROR",
        phase: "translation",
        retryable: true,
      });

      render(<App />);

      // Load demo data and execute problematic query
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, {
        target: { value: "show me the data for that thing" },
      });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      // Verify automatic execution was attempted
      await waitFor(() => {
        expect(mockApiService.executeQueryAutomatically).toHaveBeenCalled();
      });

      // Should not show chart renderer on error (key error handling requirement)
      await new Promise((resolve) => setTimeout(resolve, 500));
      expect(screen.queryByTestId("chart-renderer")).not.toBeInTheDocument();
    });

    it("should handle execution errors gracefully without showing chart", async () => {
      mockApiService.executeQueryAutomatically.mockRejectedValue({
        message: "Column 'invalid_column' not found in table",
        code: "COLUMN_NOT_FOUND",
        phase: "execution",
        retryable: false,
      });

      render(<App />);

      // Execute query that will fail during execution
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, {
        target: { value: "show me invalid_column data" },
      });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      // Verify automatic execution was attempted
      await waitFor(() => {
        expect(mockApiService.executeQueryAutomatically).toHaveBeenCalled();
      });

      // Should not show chart renderer on error (key error handling requirement)
      await new Promise((resolve) => setTimeout(resolve, 500));
      expect(screen.queryByTestId("chart-renderer")).not.toBeInTheDocument();
    });
  });

  describe("Mode Switching Between Automatic and Advanced", () => {
    it("should switch from automatic to advanced mode correctly", async () => {
      // Mock translation for advanced mode
      mockApiService.translateQuery.mockResolvedValue({
        sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
      });

      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      // Find and click the advanced mode toggle
      const advancedModeToggle = screen.getByTestId("advanced-mode-toggle");
      fireEvent.click(advancedModeToggle);

      // Enter query in advanced mode
      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, { target: { value: "monthly sales" } });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      // Should show SQL modal in advanced mode (key mode switching requirement)
      await waitFor(() => {
        expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
      });

      // Should call translateQuery, not executeQueryAutomatically
      expect(mockApiService.translateQuery).toHaveBeenCalledWith(
        "monthly sales"
      );
      expect(mockApiService.executeQueryAutomatically).not.toHaveBeenCalled();
    });

    it("should switch back to automatic mode correctly", async () => {
      mockApiService.executeQueryAutomatically.mockResolvedValue({
        translationResult: {
          sql: "SELECT category, COUNT(*) as count FROM demo_table GROUP BY category",
        },
        executionResult: {
          columns: ["category", "count"],
          rows: [
            ["Electronics", 50],
            ["Clothing", 30],
          ],
          row_count: 2,
          runtime_ms: 15,
        },
        executionTime: 80,
        fromCache: false,
      });

      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      // Switch to advanced mode first, then back to automatic
      const advancedModeToggle = screen.getByTestId("advanced-mode-toggle");
      fireEvent.click(advancedModeToggle); // Switch to advanced
      fireEvent.click(advancedModeToggle); // Switch back to automatic

      // Enter query in automatic mode
      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, { target: { value: "count by category" } });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      // Should execute automatically (key mode switching requirement)
      await waitFor(() => {
        expect(mockApiService.executeQueryAutomatically).toHaveBeenCalledWith(
          "count by category"
        );
      });

      // Should not show SQL modal
      expect(screen.queryByTestId("sql-modal")).not.toBeInTheDocument();

      // Should show dashboard directly
      await waitFor(
        () => {
          expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
        },
        { timeout: 10000 }
      );
    });
  });

  describe("Dashboard Integration with Automatic Execution", () => {
    it("should save dashboards created through automatic execution", async () => {
      mockApiService.executeQueryAutomatically.mockResolvedValue({
        translationResult: {
          sql: "SELECT region, SUM(sales) as total FROM demo_table GROUP BY region",
        },
        executionResult: {
          columns: ["region", "total"],
          rows: [
            ["North", 5000],
            ["South", 4000],
          ],
          row_count: 2,
          runtime_ms: 30,
        },
        executionTime: 120,
        fromCache: false,
      });

      mockApiService.saveDashboard.mockResolvedValue({
        id: "dashboard-1",
        name: "Regional Sales",
        question: "sales by region",
        sql: "SELECT region, SUM(sales) as total FROM demo_table GROUP BY region",
        chartConfig: { type: "bar", x: "region", y: "total" },
        createdAt: "2023-01-01T00:00:00Z",
      });

      render(<App />);

      // Execute automatic query
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, { target: { value: "sales by region" } });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      await waitFor(
        () => {
          expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
        },
        { timeout: 10000 }
      );

      // Save dashboard (key dashboard integration requirement)
      const saveDashboardButton = screen.getByText("Save Dashboard");
      fireEvent.click(saveDashboardButton);

      await waitFor(() => {
        expect(mockApiService.saveDashboard).toHaveBeenCalledWith({
          name: "Regional Sales",
          question: "sales by region",
          sql: "SELECT region, SUM(sales) as total FROM demo_table GROUP BY region",
          chartConfig: expect.objectContaining({ type: "bar" }),
        });
      });
    });

    it("should verify mode toggle exists and is functional", async () => {
      render(<App />);

      // Load demo data to get to query interface
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByTestId("query-input")).toBeInTheDocument();
      });

      // Verify advanced mode toggle exists (key mode switching requirement)
      const advancedModeToggle = screen.getByTestId("advanced-mode-toggle");
      expect(advancedModeToggle).toBeInTheDocument();

      // Verify toggle is functional
      const initialChecked = advancedModeToggle.getAttribute("aria-checked");
      fireEvent.click(advancedModeToggle);

      // Should change state
      await waitFor(() => {
        const newChecked = advancedModeToggle.getAttribute("aria-checked");
        expect(newChecked).not.toBe(initialChecked);
      });
    });
  });
});
