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

describe("Dashboard Integration with Automatic Execution", () => {
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
      ],
    });

    // Mock automatic execution response
    mockApiService.executeQueryAutomatically.mockResolvedValue({
      translationResult: {
        sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
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

    mockApiService.saveDashboard.mockResolvedValue({
      id: "dashboard-1",
      name: "Test Dashboard",
      question: "monthly sales",
      sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
      chartConfig: { type: "line", x: "date", y: "total_sales" },
      createdAt: "2023-01-01T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should render charts seamlessly with automatic execution", async () => {
    render(<App />);

    // Load demo data first
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Enter natural language query in automatic mode (default)
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "monthly sales" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    // Should automatically execute and render chart without showing SQL modal
    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    expect(mockApiService.executeQueryAutomatically).toHaveBeenCalledWith(
      "monthly sales"
    );
    expect(screen.queryByTestId("sql-modal")).not.toBeInTheDocument();

    // Verify chart displays correct data
    expect(screen.getByText("Chart Type: line")).toBeInTheDocument();
    expect(screen.getByText("Columns: date, total_sales")).toBeInTheDocument();
    expect(screen.getByText("Rows: 3")).toBeInTheDocument();
  });

  it("should maintain dashboard saving functionality after automatic execution", async () => {
    render(<App />);

    // Load demo data and execute query automatically
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "monthly sales" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    // Save Dashboard button should be available and functional
    const saveDashboardButton = screen.getByText("Save Dashboard");
    expect(saveDashboardButton).toBeInTheDocument();

    fireEvent.click(saveDashboardButton);

    await waitFor(() => {
      expect(mockApiService.saveDashboard).toHaveBeenCalledWith({
        name: "Test Dashboard",
        question: "monthly sales",
        sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
        chartConfig: expect.objectContaining({ type: "line" }),
      });
    });
  });

  it("should load saved dashboards with automatic execution enabled", async () => {
    const mockDashboard = {
      id: "dashboard-1",
      name: "Sales Dashboard",
      question: "monthly sales",
      sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
      chartConfig: { type: "line", x: "date", y: "total_sales" },
      createdAt: "2023-01-01T00:00:00Z",
    };

    mockApiService.getDashboards.mockResolvedValue([mockDashboard]);
    mockApiService.executeSQL.mockResolvedValue({
      columns: ["date", "total_sales"],
      rows: [
        ["2023-01-01", 1000],
        ["2023-02-01", 2000],
        ["2023-03-01", 1500],
      ],
      row_count: 3,
      runtime_ms: 45,
    });

    render(<App />);

    // Wait for dashboard to appear in sidebar
    await waitFor(() => {
      expect(screen.getByText("Sales Dashboard")).toBeInTheDocument();
    });

    // Click on dashboard card to load it
    const dashboardCard = screen.getByTestId("dashboard-card-dashboard-1");
    fireEvent.click(dashboardCard);

    // Should execute SQL and display dashboard
    await waitFor(() => {
      expect(mockApiService.executeSQL).toHaveBeenCalledWith(
        "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
        "monthly sales"
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    // Should show success notification
    await waitFor(() => {
      expect(
        screen.getByText(/Loaded dashboard "Sales Dashboard"/)
      ).toBeInTheDocument();
    });
  });

  it("should handle chart type selection with automatic execution", async () => {
    // Mock different chart types based on data
    mockApiService.executeQueryAutomatically.mockResolvedValue({
      translationResult: {
        sql: "SELECT category, SUM(sales) FROM demo_table GROUP BY category",
      },
      executionResult: {
        columns: ["category", "total_sales"],
        rows: [
          ["Electronics", 5000],
          ["Clothing", 3000],
          ["Books", 2000],
        ],
        row_count: 3,
        runtime_ms: 30,
      },
      executionTime: 120,
      fromCache: false,
    });

    render(<App />);

    // Load demo data
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Query for categorical data (should result in pie chart)
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "sales by category" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    // Chart should be automatically selected based on data shape
    expect(
      screen.getByText("Columns: category, total_sales")
    ).toBeInTheDocument();
    expect(screen.getByText("Rows: 3")).toBeInTheDocument();
  });

  it("should handle errors gracefully during automatic execution", async () => {
    mockApiService.executeQueryAutomatically.mockRejectedValue({
      message: "Column not found",
      code: "COLUMN_NOT_FOUND",
      phase: "execution",
    });

    render(<App />);

    // Load demo data
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Enter query that will fail
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "invalid column query" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    // Should show error message in conversation
    await waitFor(() => {
      expect(screen.getByText(/Column not found/)).toBeInTheDocument();
    });

    // Should not show chart renderer
    expect(screen.queryByTestId("chart-renderer")).not.toBeInTheDocument();
  });

  it("should switch between automatic and advanced modes correctly", async () => {
    render(<App />);

    // Load demo data
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Should be in automatic mode by default
    const advancedModeToggle = screen.getByTestId("advanced-mode-toggle");
    expect(advancedModeToggle).not.toBeChecked();

    // Switch to advanced mode
    fireEvent.click(advancedModeToggle);

    // Mock translation for advanced mode
    mockApiService.translateQuery.mockResolvedValue({
      sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
    });

    // Enter query in advanced mode
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "monthly sales" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    // Should show SQL modal in advanced mode
    await waitFor(() => {
      expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
    });

    expect(mockApiService.translateQuery).toHaveBeenCalledWith("monthly sales");
    expect(mockApiService.executeQueryAutomatically).not.toHaveBeenCalled();
  });

  it("should preserve dashboard functionality when switching modes", async () => {
    render(<App />);

    // Load demo data and create dashboard in automatic mode
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "monthly sales" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    // Save dashboard
    const saveDashboardButton = screen.getByText("Save Dashboard");
    fireEvent.click(saveDashboardButton);

    await waitFor(() => {
      expect(mockApiService.saveDashboard).toHaveBeenCalled();
    });

    // Switch to advanced mode
    const advancedModeToggle = screen.getByTestId("advanced-mode-toggle");
    fireEvent.click(advancedModeToggle);

    // Dashboard should still be visible and functional
    expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();

    // New query button should work
    const newQueryButton = screen.getByText("New Query");
    fireEvent.click(newQueryButton);

    // Should reset to query input
    expect(screen.getByTestId("query-input")).toHaveValue("");
  });

  it("should handle cached results with automatic execution", async () => {
    mockApiService.executeQueryAutomatically.mockResolvedValue({
      translationResult: {
        sql: "SELECT date, SUM(sales) FROM demo_table GROUP BY date ORDER BY date",
      },
      executionResult: {
        columns: ["date", "total_sales"],
        rows: [
          ["2023-01-01", 1000],
          ["2023-02-01", 2000],
        ],
        row_count: 2,
        runtime_ms: 5,
      },
      executionTime: 50,
      fromCache: true,
    });

    render(<App />);

    // Load demo data
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(screen.getByTestId("query-input")).toBeInTheDocument();
    });

    // Execute query
    const queryInput = screen.getByTestId("query-input");
    fireEvent.change(queryInput, { target: { value: "monthly sales" } });

    const generateButton = screen.getByTestId("generate-button");
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
    });

    // Should show cached result notification
    await waitFor(() => {
      expect(screen.getByText(/Using cached results/)).toBeInTheDocument();
    });

    // Chart should still render correctly
    expect(screen.getByText("Rows: 2")).toBeInTheDocument();
  });
});
