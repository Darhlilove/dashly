import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ChartRenderer from "../ChartRenderer";
import { ChartData, ChartConfig } from "../../types";

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
});