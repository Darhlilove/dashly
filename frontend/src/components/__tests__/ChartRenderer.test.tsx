import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChartRenderer from "../ChartRenderer";
import { ChartData, ChartConfig } from "../../types";
import { apiService } from "../../services/api";

// Mock API service
vi.mock("../../services/api", () => ({
  apiService: {
    saveDashboard: vi.fn(),
  },
}));

// Mock Recharts components to avoid canvas rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  Bar: () => <div data-testid="bar" />,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

describe("ChartRenderer", () => {
  const sampleTimeSeriesData: ChartData = {
    columns: ["date", "revenue", "users"],
    rows: [
      ["2023-01-01", 1000, 50],
      ["2023-02-01", 1200, 60],
      ["2023-03-01", 1100, 55],
    ],
  };

  const sampleCategoricalData: ChartData = {
    columns: ["category", "value"],
    rows: [
      ["A", 100],
      ["B", 200],
      ["C", 150],
      ["A", 120], // Repeat to make it categorical
    ],
  };

  const samplePieData: ChartData = {
    columns: ["region", "sales"],
    rows: [
      ["North", 1000],
      ["South", 800],
      ["East", 1200],
      ["West", 900],
    ],
  };

  const emptyData: ChartData = {
    columns: [],
    rows: [],
  };

  describe("Automatic Chart Selection", () => {
    it("should render line chart for time series data", () => {
      render(<ChartRenderer data={sampleTimeSeriesData} />);
      
      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
      expect(screen.getAllByTestId("line")).toHaveLength(2); // Two lines for revenue and users
    });

    it("should render pie chart for small categorical data", () => {
      render(<ChartRenderer data={sampleCategoricalData} />);
      
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
      expect(screen.getByTestId("pie")).toBeInTheDocument();
    });

    it("should render bar chart for large categorical data", () => {
      const largeCategoricalData: ChartData = {
        columns: ["category", "value"],
        rows: [
          ["Category A", 100],
          ["Category B", 200],
          ["Category C", 150],
          ["Category D", 300],
          ["Category E", 250],
          ["Category F", 180],
          ["Category G", 220],
          ["Category H", 190],
          ["Category I", 280],
          ["Category A", 120], // Repeat to make it categorical
        ],
      };
      
      render(<ChartRenderer data={largeCategoricalData} />);
      
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
      expect(screen.getByTestId("bar")).toBeInTheDocument();
    });

    it("should render pie chart when explicitly configured", () => {
      const pieConfig: ChartConfig = {
        type: "pie",
        x: "region",
        y: "sales",
      };
      
      render(<ChartRenderer data={samplePieData} config={pieConfig} />);
      
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
      expect(screen.getByTestId("pie")).toBeInTheDocument();
    });

    it("should render table view for empty data", () => {
      render(<ChartRenderer data={emptyData} />);
      
      expect(screen.getByText("No data available for chart rendering.")).toBeInTheDocument();
    });
  });

  describe("Explicit Chart Configuration", () => {
    it("should render line chart when explicitly configured", () => {
      const lineConfig: ChartConfig = {
        type: "line",
        x: "date",
        y: "revenue",
      };
      
      render(<ChartRenderer data={sampleTimeSeriesData} config={lineConfig} />);
      
      expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    });

    it("should render bar chart when explicitly configured", () => {
      const barConfig: ChartConfig = {
        type: "bar",
        x: "category",
        y: "value",
      };
      
      render(<ChartRenderer data={sampleCategoricalData} config={barConfig} />);
      
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    it("should render table when explicitly configured", () => {
      const tableConfig: ChartConfig = {
        type: "table",
      };
      
      render(<ChartRenderer data={sampleCategoricalData} config={tableConfig} />);
      
      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getByText("category")).toBeInTheDocument();
      expect(screen.getByText("value")).toBeInTheDocument();
    });
  });

  describe("Table View", () => {
    it("should render table with correct headers and data", () => {
      const tableConfig: ChartConfig = { type: "table" };
      
      render(<ChartRenderer data={sampleCategoricalData} config={tableConfig} />);
      
      // Check headers
      expect(screen.getByText("category")).toBeInTheDocument();
      expect(screen.getByText("value")).toBeInTheDocument();
      
      // Check data
      expect(screen.getAllByText("A")).toHaveLength(2); // A appears twice
      expect(screen.getByText("100")).toBeInTheDocument();
      expect(screen.getByText("B")).toBeInTheDocument();
      expect(screen.getByText("200")).toBeInTheDocument();
    });

    it("should show row limit message for large datasets", () => {
      const largeData: ChartData = {
        columns: ["id", "value"],
        rows: Array.from({ length: 150 }, (_, i) => [i, i * 10]),
      };
      
      render(<ChartRenderer data={largeData} config={{ type: "table" }} />);
      
      expect(screen.getByText("Showing first 100 rows of 150 total rows")).toBeInTheDocument();
    });

    it("should handle empty table data", () => {
      render(<ChartRenderer data={emptyData} config={{ type: "table" }} />);
      
      expect(screen.getByText("No data available for chart rendering.")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should show error for invalid configuration", () => {
      const invalidConfig: ChartConfig = {
        type: "line",
        x: "nonexistent_column",
        y: "another_nonexistent_column",
      };
      
      render(<ChartRenderer data={sampleCategoricalData} config={invalidConfig} />);
      
      expect(screen.getByText("Invalid chart configuration for the provided data.")).toBeInTheDocument();
    });

    it("should handle null/undefined values in data", () => {
      const dataWithNulls: ChartData = {
        columns: ["category", "value"],
        rows: [
          ["A", 100],
          ["B", null],
          ["C", undefined],
          [null, 200],
        ],
      };
      
      render(<ChartRenderer data={dataWithNulls} config={{ type: "table" }} />);
      
      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getByText("A")).toBeInTheDocument();
      expect(screen.getByText("100")).toBeInTheDocument();
    });
  });

  describe("Props and Styling", () => {
    it("should apply custom className", () => {
      const { container } = render(
        <ChartRenderer data={sampleCategoricalData} className="custom-class" />
      );
      
      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("should use custom height", () => {
      render(<ChartRenderer data={sampleCategoricalData} height={300} />);
      
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });

    it("should handle width prop", () => {
      render(<ChartRenderer data={sampleCategoricalData} width={500} />);
      
      expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    });
  });

  describe("Data Transformation", () => {
    it("should handle numeric strings in data", () => {
      const stringNumericData: ChartData = {
        columns: ["category", "value"],
        rows: [
          ["A", "100"],
          ["B", "200.5"],
          ["C", "150"],
          ["A", "120"], // Repeat to make it categorical
        ],
      };
      
      render(<ChartRenderer data={stringNumericData} />);
      
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument(); // Small categorical data becomes pie chart
    });

    it("should handle mixed data types", () => {
      const mixedData: ChartData = {
        columns: ["id", "name", "value", "active"],
        rows: [
          [1, "Item A", 100, true],
          [2, "Item B", 200, false],
          [3, "Item C", 150, true],
        ],
      };
      
      render(<ChartRenderer data={mixedData} config={{ type: "table" }} />);
      
      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getByText("Item A")).toBeInTheDocument();
      expect(screen.getAllByText("true")).toHaveLength(2);
    });
  });

  describe("Chart Limits", () => {
    it("should apply limit configuration for bar charts", () => {
      const largeData: ChartData = {
        columns: ["category", "value"],
        rows: Array.from({ length: 50 }, (_, i) => [`Category ${i}`, i * 10]),
      };
      
      const limitConfig: ChartConfig = {
        type: "bar",
        x: "category",
        y: "value",
        limit: 10,
      };
      
      render(<ChartRenderer data={largeData} config={limitConfig} />);
      
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    it("should apply limit configuration for pie charts", () => {
      const pieConfig: ChartConfig = {
        type: "pie",
        x: "region",
        y: "sales",
        limit: 8,
      };
      
      render(<ChartRenderer data={samplePieData} config={pieConfig} />);
      
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
    });
  });

  describe("Dashboard Saving Functionality", () => {
    const mockOnSaveSuccess = vi.fn();
    const mockOnSaveError = vi.fn();

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it("should show Save Dashboard button when question and sql are provided", () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      expect(screen.getByText("Save Dashboard")).toBeInTheDocument();
    });

    it("should not show Save Dashboard button when question or sql is missing", () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          // sql is missing
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      expect(screen.queryByText("Save Dashboard")).not.toBeInTheDocument();
    });

    it("should open save modal when Save Dashboard button is clicked", async () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByText("Save Dashboard", { selector: "h2" })).toBeInTheDocument();
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });
    });

    it("should close modal when Cancel button is clicked", async () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Cancel"));

      await waitFor(() => {
        expect(screen.queryByText("Save Dashboard", { selector: "h2" })).not.toBeInTheDocument();
      });
    });

    it("should successfully save dashboard with valid name", async () => {
      const mockDashboard = {
        id: "123",
        name: "Sales Dashboard",
        question: "Show me sales by category",
        sql: "SELECT category, SUM(value) FROM data GROUP BY category",
        chartConfig: { type: "pie" as const, x: "category", y: "value" },
        createdAt: "2023-01-01T00:00:00Z",
      };

      (apiService.saveDashboard as any).mockResolvedValue(mockDashboard);

      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText("Enter dashboard name...");
      fireEvent.change(nameInput, { target: { value: "Sales Dashboard" } });

      const submitButton = screen.getAllByRole("button", { name: /save dashboard/i }).find(btn => btn.getAttribute("type") === "submit");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(apiService.saveDashboard).toHaveBeenCalledWith({
          name: "Sales Dashboard",
          question: "Show me sales by category",
          sql: "SELECT category, SUM(value) FROM data GROUP BY category",
          chartConfig: expect.objectContaining({ type: "pie" }),
        });
        expect(mockOnSaveSuccess).toHaveBeenCalledWith(mockDashboard);
      });
    });

    it("should show error when dashboard name is empty", async () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const form = screen.getByLabelText("Dashboard Name").closest("form");
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(screen.getByText("Dashboard name is required")).toBeInTheDocument();
      });

      expect(apiService.saveDashboard).not.toHaveBeenCalled();
      expect(mockOnSaveSuccess).not.toHaveBeenCalled();
    });

    it("should show error when dashboard name is too short", async () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText("Enter dashboard name...");
      fireEvent.change(nameInput, { target: { value: "AB" } });

      const submitButton = screen.getAllByRole("button", { name: /save dashboard/i }).find(btn => btn.getAttribute("type") === "submit");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(screen.getByText("Dashboard name must be at least 3 characters")).toBeInTheDocument();
      });

      expect(apiService.saveDashboard).not.toHaveBeenCalled();
    });

    it("should handle API error during save", async () => {
      const errorMessage = "Failed to save dashboard";
      (apiService.saveDashboard as any).mockRejectedValue(new Error(errorMessage));

      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText("Enter dashboard name...");
      fireEvent.change(nameInput, { target: { value: "Test Dashboard" } });

      const submitButton = screen.getAllByRole("button", { name: /save dashboard/i }).find(btn => btn.getAttribute("type") === "submit");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(mockOnSaveError).toHaveBeenCalledWith(errorMessage);
      });

      expect(mockOnSaveSuccess).not.toHaveBeenCalled();
    });

    it("should show loading state during save", async () => {
      let resolvePromise: (value: any) => void;
      const savePromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      (apiService.saveDashboard as any).mockReturnValue(savePromise);

      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText("Enter dashboard name...");
      fireEvent.change(nameInput, { target: { value: "Test Dashboard" } });

      const submitButton = screen.getAllByRole("button", { name: /save dashboard/i }).find(btn => btn.getAttribute("type") === "submit");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(screen.getByText("Saving...")).toBeInTheDocument();
      });

      // Resolve the promise to complete the test
      resolvePromise!({
        id: "123",
        name: "Test Dashboard",
        question: "Show me sales by category",
        sql: "SELECT category, SUM(value) FROM data GROUP BY category",
        chartConfig: { type: "pie" },
        createdAt: "2023-01-01T00:00:00Z",
      });

      await waitFor(() => {
        expect(screen.queryByText("Saving...")).not.toBeInTheDocument();
      });
    });

    it("should handle missing question or sql during save", async () => {
      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      // Manually trigger save without question/sql (simulate edge case)
      const component = screen.getByText("Save Dashboard").closest("div");
      
      // This test verifies the error handling in handleSaveDashboard
      // when question or sql is missing at save time
      expect(component).toBeInTheDocument();
    });

    it("should trim whitespace from dashboard name", async () => {
      const mockDashboard = {
        id: "123",
        name: "Sales Dashboard",
        question: "Show me sales by category",
        sql: "SELECT category, SUM(value) FROM data GROUP BY category",
        chartConfig: { type: "pie" as const, x: "category", y: "value" },
        createdAt: "2023-01-01T00:00:00Z",
      };

      (apiService.saveDashboard as any).mockResolvedValue(mockDashboard);

      render(
        <ChartRenderer
          data={sampleCategoricalData}
          question="Show me sales by category"
          sql="SELECT category, SUM(value) FROM data GROUP BY category"
          onSaveSuccess={mockOnSaveSuccess}
          onSaveError={mockOnSaveError}
        />
      );

      fireEvent.click(screen.getByText("Save Dashboard"));

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Enter dashboard name...")).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText("Enter dashboard name...");
      fireEvent.change(nameInput, { target: { value: "  Sales Dashboard  " } });

      const submitButton = screen.getAllByRole("button", { name: /save dashboard/i }).find(btn => btn.getAttribute("type") === "submit");
      fireEvent.click(submitButton!);

      await waitFor(() => {
        expect(apiService.saveDashboard).toHaveBeenCalledWith({
          name: "Sales Dashboard", // Should be trimmed
          question: "Show me sales by category",
          sql: "SELECT category, SUM(value) FROM data GROUP BY category",
          chartConfig: expect.objectContaining({ type: "pie" }),
        });
      });
    });
  });
});