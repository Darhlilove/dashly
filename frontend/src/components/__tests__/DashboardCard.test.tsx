import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import DashboardCard from "../DashboardCard";
import { Dashboard } from "../../types/dashboard";

// Mock Recharts components
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
}));

describe("DashboardCard", () => {
  const mockOnLoad = vi.fn();

  const mockDashboard: Dashboard = {
    id: "test-dashboard-1",
    name: "Sales Dashboard",
    question: "What are the monthly sales trends for the last 12 months?",
    sql: "SELECT month, sales FROM monthly_sales ORDER BY month",
    chartConfig: {
      type: "line",
      x: "month",
      y: "sales",
    },
    createdAt: "2024-01-15T10:30:00Z",
  };

  beforeEach(() => {
    mockOnLoad.mockClear();
  });

  it("renders dashboard card with correct information", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByText("Sales Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Created Jan 15, 2024")).toBeInTheDocument();
    expect(
      screen.getByText("What are the monthly sales trends for the last 12 months?")
    ).toBeInTheDocument();
    expect(screen.getByText("Line Chart")).toBeInTheDocument();
  });

  it("calls onLoad when card is clicked", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    fireEvent.click(card);

    expect(mockOnLoad).toHaveBeenCalledWith(mockDashboard);
    expect(mockOnLoad).toHaveBeenCalledTimes(1);
  });

  it("calls onLoad when Enter key is pressed", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: "Enter" });

    expect(mockOnLoad).toHaveBeenCalledWith(mockDashboard);
    expect(mockOnLoad).toHaveBeenCalledTimes(1);
  });

  it("calls onLoad when Space key is pressed", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: " " });

    expect(mockOnLoad).toHaveBeenCalledWith(mockDashboard);
    expect(mockOnLoad).toHaveBeenCalledTimes(1);
  });

  it("does not call onLoad for other keys", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: "Tab" });

    expect(mockOnLoad).not.toHaveBeenCalled();
  });

  it("renders line chart preview for line chart type", () => {
    const lineChartDashboard = {
      ...mockDashboard,
      chartConfig: { type: "line" as const, x: "month", y: "sales" },
    };

    render(<DashboardCard dashboard={lineChartDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByText("Line Chart")).toBeInTheDocument();
  });

  it("renders bar chart preview for bar chart type", () => {
    const barChartDashboard = {
      ...mockDashboard,
      chartConfig: { type: "bar" as const, x: "category", y: "value" },
    };

    render(<DashboardCard dashboard={barChartDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.getByText("Bar Chart")).toBeInTheDocument();
  });

  it("renders pie chart preview for pie chart type", () => {
    const pieChartDashboard = {
      ...mockDashboard,
      chartConfig: { type: "pie" as const, x: "category", y: "value" },
    };

    render(<DashboardCard dashboard={pieChartDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
    expect(screen.getByText("Pie Chart")).toBeInTheDocument();
  });

  it("renders table preview for table type", () => {
    const tableChartDashboard = {
      ...mockDashboard,
      chartConfig: { type: "table" as const },
    };

    render(<DashboardCard dashboard={tableChartDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByText("Table View")).toBeInTheDocument();
    expect(screen.getByText("Table Chart")).toBeInTheDocument();
  });

  it("handles invalid date gracefully", () => {
    const invalidDateDashboard = {
      ...mockDashboard,
      createdAt: "invalid-date",
    };

    render(<DashboardCard dashboard={invalidDateDashboard} onLoad={mockOnLoad} />);

    expect(screen.getByText(/Created.*Unknown date/)).toBeInTheDocument();
  });

  it("truncates long dashboard names", () => {
    const longNameDashboard = {
      ...mockDashboard,
      name: "This is a very long dashboard name that should be truncated",
    };

    render(<DashboardCard dashboard={longNameDashboard} onLoad={mockOnLoad} />);

    const titleElement = screen.getByText(longNameDashboard.name);
    expect(titleElement).toHaveClass("truncate");
  });

  it("truncates long questions with line-clamp", () => {
    const longQuestionDashboard = {
      ...mockDashboard,
      question: "This is a very long question that should be truncated with line clamp because it exceeds the maximum number of lines allowed in the dashboard card preview",
    };

    render(<DashboardCard dashboard={longQuestionDashboard} onLoad={mockOnLoad} />);

    const questionElement = screen.getByText(longQuestionDashboard.question);
    expect(questionElement).toHaveClass("line-clamp-2");
  });

  it("applies custom className", () => {
    const { container } = render(
      <DashboardCard
        dashboard={mockDashboard}
        onLoad={mockOnLoad}
        className="custom-class"
      />
    );

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass("custom-class");
  });

  it("has proper accessibility attributes", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    expect(card).toHaveAttribute("tabIndex", "0");
    expect(card).toHaveAttribute("aria-label", "Load dashboard: Sales Dashboard");
  });

  it("shows hover and focus styles", () => {
    render(<DashboardCard dashboard={mockDashboard} onLoad={mockOnLoad} />);

    const card = screen.getByRole("button");
    expect(card).toHaveClass("hover:border-blue-300");
    expect(card).toHaveClass("hover:shadow-md");
    expect(card).toHaveClass("focus:outline-none");
    expect(card).toHaveClass("focus:ring-2");
    expect(card).toHaveClass("focus:ring-blue-500");
  });
});