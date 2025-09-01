import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api", () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
    translateQuery: vi.fn(),
    executeSQL: vi.fn(),
    saveDashboard: vi.fn(),
    getDashboards: vi.fn(),
    getDashboard: vi.fn(),
  },
}));

// Mock chart components to avoid Recharts rendering issues in tests
vi.mock("../components/ChartRenderer", () => ({
  default: ({ data, config }: any) => (
    <div data-testid="chart-renderer">
      <div>Chart Type: {config.type}</div>
      <div>Columns: {data.columns.join(", ")}</div>
      <div>Rows: {data.rows.length}</div>
    </div>
  ),
}));

const mockApiService = apiService as any;

describe("Layout Interactions Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockApiService.getDashboards.mockResolvedValue([]);
    mockApiService.uploadFile.mockResolvedValue({
      table: "test_table",
      columns: [
        { name: "date", type: "DATE" },
        { name: "revenue", type: "DECIMAL" },
        { name: "region", type: "VARCHAR" },
      ],
    });
    mockApiService.useDemoData.mockResolvedValue({
      table: "demo_table",
      columns: [
        { name: "date", type: "DATE" },
        { name: "sales", type: "DECIMAL" },
        { name: "category", type: "VARCHAR" },
      ],
    });
    mockApiService.translateQuery.mockResolvedValue({
      sql: "SELECT date, SUM(revenue) FROM test_table GROUP BY date ORDER BY date",
    });
    mockApiService.executeSQL.mockResolvedValue({
      columns: ["date", "total_revenue"],
      rows: [
        ["2023-01-01", 1000],
        ["2023-02-01", 2000],
        ["2023-03-01", 1500],
      ],
      row_count: 3,
      runtime_ms: 45,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Complete User Workflows", () => {
    it("should handle complete workflow: upload → resize panes → query → switch views", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Step 1: Upload file
      const fileInput = screen.getByTestId("file-input");
      const testFile = new File(["test,data"], "test.csv", {
        type: "text/csv",
      });

      await user.upload(fileInput, testFile);

      const uploadButton = screen.getByTestId("upload-button");
      await user.click(uploadButton);

      // Wait for transition to query phase
      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Step 2: Test pane resizing
      const resizeHandle = screen.getByTestId("resize-handle");
      expect(resizeHandle).toBeInTheDocument();

      // Simulate resize drag
      fireEvent.mouseDown(resizeHandle, { clientX: 300 });
      fireEvent.mouseMove(document, { clientX: 400 });
      fireEvent.mouseUp(document);

      // Layout should still be functional after resize
      expect(screen.getByTestId("chat-pane")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-pane")).toBeInTheDocument();

      // Step 3: Execute query
      const queryInput = screen.getByTestId("query-input");
      await user.type(queryInput, "monthly revenue");

      const generateButton = screen.getByTestId("generate-button");
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
      });

      const runQueryButton = screen.getByTestId("run-query-button");
      await user.click(runQueryButton);

      // Wait for results
      await waitFor(() => {
        expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      });

      // Step 4: Test view switching
      const viewToggle = screen.getByRole("tablist");
      expect(viewToggle).toBeInTheDocument();

      const dataViewButton = screen.getByRole("tab", { name: /data table/i });
      await user.click(dataViewButton);

      // Should show data table view
      await waitFor(() => {
        expect(screen.getByText("Data Preview")).toBeInTheDocument();
      });

      // Switch back to dashboard view
      const dashboardViewButton = screen.getByRole("tab", {
        name: /dashboard/i,
      });
      await user.click(dashboardViewButton);

      // Should show chart again
      await waitFor(() => {
        expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      });
    });

    it("should handle sidebar interactions during workflow", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Load demo data to get to query phase
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Test sidebar auto-hide functionality
      // Sidebar should be hidden initially in query phase
      const sidebar = screen.queryByText("dashly");
      if (sidebar) {
        const sidebarContainer = sidebar.closest('[role="complementary"]');
        expect(sidebarContainer).toHaveStyle("transform: translateX(-100%)");
      }

      // Simulate mouse move to trigger zone (left edge)
      fireEvent.mouseMove(document, { clientX: 10 });

      // Sidebar should become visible
      await waitFor(() => {
        const sidebarAfterHover = screen.getByText("dashly");
        const sidebarContainerAfterHover = sidebarAfterHover.closest(
          '[role="complementary"]'
        );
        expect(sidebarContainerAfterHover).toHaveStyle(
          "transform: translateX(0px)"
        );
      });

      // Test keyboard shortcut for sidebar
      await user.keyboard("{Control>}s{/Control}");

      // Sidebar should toggle (hide in this case)
      await waitFor(() => {
        const sidebarAfterKeyboard = screen.getByText("dashly");
        const sidebarContainerAfterKeyboard = sidebarAfterKeyboard.closest(
          '[role="complementary"]'
        );
        expect(sidebarContainerAfterKeyboard).toHaveStyle(
          "transform: translateX(-100%)"
        );
      });
    });
  });

  describe("Responsive Behavior", () => {
    it("should adapt layout for different screen sizes", async () => {
      // Mock window.matchMedia for different screen sizes
      const mockMatchMedia = (query: string) => ({
        matches: query.includes("max-width: 768px"), // Simulate mobile
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      });

      Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: mockMatchMedia,
      });

      const user = userEvent.setup();
      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // On mobile, layout should be different
      // Resize handle should not be visible or should behave differently
      const resizeHandle = screen.queryByTestId("resize-handle");
      if (resizeHandle) {
        // On mobile, resize handle might be hidden or have different behavior
        expect(resizeHandle).toBeInTheDocument();
      }

      // Test mobile sidebar behavior
      const mainContent = screen.getByTestId("main-content") || document.body;

      // Simulate touch at left edge
      fireEvent.touchStart(mainContent, {
        touches: [{ clientX: 10, clientY: 100 }],
      });

      // Should activate sidebar on mobile
      await waitFor(() => {
        const sidebar = screen.getByText("dashly");
        expect(sidebar).toBeInTheDocument();
      });
    });

    it("should handle orientation changes", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Load demo data and execute query
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      const queryInput = screen.getByTestId("query-input");
      await user.type(queryInput, "test query");

      const generateButton = screen.getByTestId("generate-button");
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
      });

      const runQueryButton = screen.getByTestId("run-query-button");
      await user.click(runQueryButton);

      await waitFor(() => {
        expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      });

      // Simulate orientation change by firing resize event
      fireEvent(window, new Event("resize"));

      // Layout should remain functional after orientation change
      expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation and Accessibility", () => {
    it("should support full keyboard navigation", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Test keyboard navigation to resize handle
      const resizeHandle = screen.getByTestId("resize-handle");
      resizeHandle.focus();
      expect(resizeHandle).toHaveFocus();

      // Test keyboard resize operations
      await user.keyboard("{ArrowRight}");
      await user.keyboard("{ArrowLeft}");
      await user.keyboard("{Home}");
      await user.keyboard("{End}");

      // Layout should remain functional
      expect(screen.getByTestId("chat-pane")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-pane")).toBeInTheDocument();

      // Test sidebar keyboard shortcuts
      await user.keyboard("{Control>}s{/Control}");

      // Test escape key to close sidebar
      await user.keyboard("{Escape}");

      // Execute query to test view toggle keyboard navigation
      const queryInput = screen.getByTestId("query-input");
      await user.type(queryInput, "test query");

      const generateButton = screen.getByTestId("generate-button");
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
      });

      const runQueryButton = screen.getByTestId("run-query-button");
      await user.click(runQueryButton);

      await waitFor(() => {
        expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      });

      // Test view toggle keyboard navigation
      const dashboardTab = screen.getByRole("tab", { name: /dashboard/i });
      dashboardTab.focus();
      expect(dashboardTab).toHaveFocus();

      // Navigate with arrow keys
      await user.keyboard("{ArrowRight}");

      const dataTab = screen.getByRole("tab", { name: /data table/i });
      expect(dataTab).toHaveFocus();

      // Activate with Enter
      await user.keyboard("{Enter}");

      await waitFor(() => {
        expect(screen.getByText("Data Preview")).toBeInTheDocument();
      });
    });

    it("should maintain proper focus management", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Focus an element in main content
      const queryInput = screen.getByTestId("query-input");
      queryInput.focus();
      expect(queryInput).toHaveFocus();

      // Open sidebar with keyboard shortcut
      await user.keyboard("{Control>}s{/Control}");

      // Focus should move to sidebar
      await waitFor(() => {
        const sidebar = screen.getByText("dashly");
        const sidebarContainer = sidebar.closest('[role="complementary"]');
        expect(sidebarContainer).toHaveAttribute("aria-expanded", "true");
      });

      // Close sidebar with Escape
      await user.keyboard("{Escape}");

      // Focus should return to previous element
      await waitFor(() => {
        expect(queryInput).toHaveFocus();
      });
    });

    it("should have proper ARIA attributes and screen reader support", async () => {
      render(<App />);

      // Load demo data to get to layout with all components
      const demoButton = screen.getByTestId("demo-data-button");
      fireEvent.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Check resize handle accessibility
      const resizeHandle = screen.getByTestId("resize-handle");
      expect(resizeHandle).toHaveAttribute("role", "separator");
      expect(resizeHandle).toHaveAttribute("aria-orientation", "vertical");
      expect(resizeHandle).toHaveAttribute("tabIndex", "0");
      expect(resizeHandle).toHaveAttribute("aria-label");

      // Check sidebar accessibility
      const sidebar = screen.getByText("dashly");
      const sidebarContainer = sidebar.closest('[role="complementary"]');
      expect(sidebarContainer).toHaveAttribute(
        "aria-label",
        "Navigation sidebar"
      );
      expect(sidebarContainer).toHaveAttribute("aria-hidden");
      expect(sidebarContainer).toHaveAttribute("aria-expanded");

      // Execute query to test view toggle accessibility
      const queryInput = screen.getByTestId("query-input");
      fireEvent.change(queryInput, { target: { value: "test query" } });

      const generateButton = screen.getByTestId("generate-button");
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId("sql-modal")).toBeInTheDocument();
      });

      const runQueryButton = screen.getByTestId("run-query-button");
      fireEvent.click(runQueryButton);

      await waitFor(() => {
        expect(screen.getByTestId("chart-renderer")).toBeInTheDocument();
      });

      // Check view toggle accessibility
      const tablist = screen.getByRole("tablist");
      expect(tablist).toHaveAttribute("aria-label");

      const dashboardTab = screen.getByRole("tab", { name: /dashboard/i });
      expect(dashboardTab).toHaveAttribute("aria-controls");
      expect(dashboardTab).toHaveAttribute("aria-selected");

      const dataTab = screen.getByRole("tab", { name: /data table/i });
      expect(dataTab).toHaveAttribute("aria-controls");
      expect(dataTab).toHaveAttribute("aria-selected");
    });
  });

  describe("Error Handling and Edge Cases", () => {
    it("should handle layout errors gracefully", async () => {
      const user = userEvent.setup();

      // Mock console.error to catch any errors
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Try extreme resize operations
      const resizeHandle = screen.getByTestId("resize-handle");

      // Extreme drag operations
      fireEvent.mouseDown(resizeHandle, { clientX: 100 });
      fireEvent.mouseMove(document, { clientX: -1000 }); // Way beyond bounds
      fireEvent.mouseUp(document);

      fireEvent.mouseDown(resizeHandle, { clientX: 100 });
      fireEvent.mouseMove(document, { clientX: 10000 }); // Way beyond bounds
      fireEvent.mouseUp(document);

      // Layout should remain functional
      expect(screen.getByTestId("chat-pane")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-pane")).toBeInTheDocument();

      // Should not have thrown any errors
      expect(consoleSpy).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it("should handle rapid user interactions", async () => {
      const user = userEvent.setup();
      render(<App />);

      // Load demo data
      const demoButton = screen.getByTestId("demo-data-button");
      await user.click(demoButton);

      await waitFor(() => {
        expect(screen.getByText("Ask a Question")).toBeInTheDocument();
      });

      // Rapid sidebar toggling
      for (let i = 0; i < 5; i++) {
        await user.keyboard("{Control>}s{/Control}");
        await new Promise((resolve) => setTimeout(resolve, 50));
      }

      // Rapid resize operations
      const resizeHandle = screen.getByTestId("resize-handle");
      for (let i = 0; i < 5; i++) {
        fireEvent.mouseDown(resizeHandle, { clientX: 100 + i * 10 });
        fireEvent.mouseMove(document, { clientX: 200 + i * 10 });
        fireEvent.mouseUp(document);
      }

      // Layout should remain stable
      expect(screen.getByTestId("chat-pane")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-pane")).toBeInTheDocument();
    });
  });
});
