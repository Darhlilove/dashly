import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import DataTableView from "../DataTableView";
import { UploadResponse } from "../../types";

describe("DataTableView", () => {
  const mockTableInfo: UploadResponse = {
    table: "test_table",
    columns: [
      { name: "id", type: "INTEGER" },
      { name: "name", type: "VARCHAR" },
      { name: "age", type: "INTEGER" },
      { name: "email", type: "VARCHAR" },
    ],
  };

  const mockData = [
    [1, "John Doe", 30, "john@example.com"],
    [2, "Jane Smith", 25, "jane@example.com"],
    [3, "Bob Johnson", 35, "bob@example.com"],
  ];

  it("renders table with column headers and data types", () => {
    render(<DataTableView tableInfo={mockTableInfo} data={mockData} />);

    // Check table headers with column names
    expect(screen.getByText("id")).toBeInTheDocument();
    expect(screen.getByText("name")).toBeInTheDocument();
    expect(screen.getByText("age")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();

    // Check data types are displayed
    expect(screen.getAllByText("INTEGER")).toHaveLength(2); // id and age columns
    expect(screen.getAllByText("VARCHAR")).toHaveLength(2); // name and email columns
  });

  it("renders table data correctly", () => {
    render(<DataTableView tableInfo={mockTableInfo} data={mockData} />);

    // Check data rows
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Bob Johnson")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("displays table info in header", () => {
    render(<DataTableView tableInfo={mockTableInfo} data={mockData} />);

    expect(screen.getByText("Data Preview")).toBeInTheDocument();
    expect(screen.getByText("3 rows × 4 columns")).toBeInTheDocument();
    expect(screen.getByText("Table: test_table")).toBeInTheDocument();
  });

  it("shows empty state when no data provided", () => {
    render(<DataTableView tableInfo={mockTableInfo} data={[]} />);

    expect(screen.getByText("No Data Available")).toBeInTheDocument();
    expect(
      screen.getByText("Upload a CSV file to see your data here")
    ).toBeInTheDocument();
  });

  it("shows virtual scrolling for large datasets", () => {
    const largeData = Array.from({ length: 150 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        maxRows={100}
        virtualScrolling={true}
      />
    );

    expect(
      screen.getByText("150 rows × 4 columns (Virtual Scrolling)")
    ).toBeInTheDocument();
  });

  it("shows pagination for large datasets when virtual scrolling is disabled", () => {
    const largeData = Array.from({ length: 150 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        maxRows={100}
        virtualScrolling={false}
      />
    );

    expect(
      screen.getByText("Showing first 100 rows of 150 total rows")
    ).toBeInTheDocument();
  });

  it("handles empty cells gracefully", () => {
    const dataWithNulls = [
      [1, "John", null, "john@example.com"],
      [2, null, 25, null],
    ];

    render(<DataTableView tableInfo={mockTableInfo} data={dataWithNulls} />);

    // Component should render without crashing
    expect(screen.getByText("John")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("shows loading state when isLoading is true", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        isLoading={true}
      />
    );

    expect(screen.getByText("Loading more data...")).toBeInTheDocument();
  });

  it("shows load more button when onLoadMore is provided", () => {
    const largeData = Array.from({ length: 150 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    const mockLoadMore = vi.fn();
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        maxRows={100}
        virtualScrolling={false}
        onLoadMore={mockLoadMore}
      />
    );

    expect(screen.getByText("Load More Rows")).toBeInTheDocument();
  });

  it("filters data when search term is entered", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableSearch={true}
      />
    );

    const searchInput = screen.getByPlaceholderText("Search data...");
    fireEvent.change(searchInput, { target: { value: "jane@example.com" } });

    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.queryByText("John Doe")).not.toBeInTheDocument();
    expect(screen.queryByText("Bob Johnson")).not.toBeInTheDocument();
  });

  it("sorts data when column header is clicked", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableSort={true}
      />
    );

    const nameHeader = screen.getByText("name");
    fireEvent.click(nameHeader);

    // After sorting by name ascending, Bob should come first
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Bob Johnson"); // First data row (index 1, after header)
  });

  it("shows export button when export is enabled", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableExport={true}
      />
    );

    expect(screen.getByText("Export CSV")).toBeInTheDocument();
  });

  it("hides search when enableSearch is false", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableSearch={false}
      />
    );

    expect(
      screen.queryByPlaceholderText("Search data...")
    ).not.toBeInTheDocument();
  });

  it("disables sorting when enableSort is false", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableSort={false}
      />
    );

    const nameHeader = screen.getByText("name");
    // Should not have cursor-pointer class when sorting is disabled
    expect(nameHeader.closest("th")).not.toHaveClass("cursor-pointer");
  });

  it("handles virtual scrolling performance optimization", () => {
    const largeData = Array.from({ length: 1000 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        virtualScrolling={true}
        maxRows={100}
      />
    );

    // Should indicate virtual scrolling is active
    expect(
      screen.getByText("1000 rows × 4 columns (Virtual Scrolling)")
    ).toBeInTheDocument();

    // Should not render all 1000 rows in DOM (performance optimization)
    const rows = screen.getAllByRole("row");
    // Should have header + visible rows (much less than 1000)
    expect(rows.length).toBeLessThan(200);
  });

  it("handles scroll events in virtual scrolling mode", () => {
    const largeData = Array.from({ length: 500 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        virtualScrolling={true}
      />
    );

    const tableContainer = screen.getByRole("table").closest("div");

    // Simulate scroll event
    fireEvent.scroll(tableContainer!, { target: { scrollTop: 1000 } });

    // Component should handle scroll without crashing
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("calls onLoadMore when reaching end of data", () => {
    const mockLoadMore = vi.fn();
    const largeData = Array.from({ length: 150 }, (_, i) => [
      i + 1,
      `User ${i + 1}`,
      20 + i,
      `user${i + 1}@example.com`,
    ]);

    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={largeData}
        maxRows={100}
        virtualScrolling={false}
        onLoadMore={mockLoadMore}
      />
    );

    const loadMoreButton = screen.getByText("Load More Rows");
    fireEvent.click(loadMoreButton);

    expect(mockLoadMore).toHaveBeenCalled();
  });

  it("handles data export functionality", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableExport={true}
      />
    );

    const exportButton = screen.getByText("Export CSV");
    expect(exportButton).toBeInTheDocument();

    // Test that clicking doesn't crash the component
    expect(() => {
      fireEvent.click(exportButton);
    }).not.toThrow();
  });

  it("handles column resizing when enabled", () => {
    render(
      <DataTableView
        tableInfo={mockTableInfo}
        data={mockData}
        enableColumnResize={true}
      />
    );

    // Component should render without crashing when column resize is enabled
    expect(screen.getByText("name")).toBeInTheDocument();
    expect(screen.getByText("age")).toBeInTheDocument();
  });
});
