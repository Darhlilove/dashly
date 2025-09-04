/**
 * Tests for ViewStateManager service
 * Verifies proper view state separation and management
 */

import { vi } from "vitest";
import { ViewStateManager, viewStateManager } from "../viewStateManager";
import { UploadResponse, ExecuteResponse } from "../../types/api";
import { ChartConfig } from "../../types/chart";

describe("ViewStateManager", () => {
  let manager: ViewStateManager;

  beforeEach(() => {
    manager = new ViewStateManager();
  });

  describe("Initial State", () => {
    it("should initialize with correct default state", () => {
      const state = manager.getState();

      expect(state.currentView).toBe("data");
      expect(state.dataView.tableInfo).toBeNull();
      expect(state.dataView.previewRows).toBeNull();
      expect(state.dataView.isLoading).toBe(false);
      expect(state.dataView.error).toBeNull();
      expect(state.dashboardView.queryResults).toBeNull();
      expect(state.dashboardView.charts).toEqual([]);
      expect(state.dashboardView.currentChart).toBeNull();
      expect(state.dashboardView.currentQuery).toBe("");
      expect(state.dashboardView.isLoading).toBe(false);
      expect(state.dashboardView.error).toBeNull();
    });
  });

  describe("Data View Management", () => {
    it("should update raw data without affecting dashboard state", () => {
      const mockUploadResponse: UploadResponse = {
        table: "test_table",
        columns: [
          { name: "id", type: "INTEGER" },
          { name: "name", type: "TEXT" },
        ],
        sample_rows: [
          ["1", "John"],
          ["2", "Jane"],
        ],
        total_rows: 2,
      };

      manager.updateRawData(mockUploadResponse);

      const state = manager.getState();
      expect(state.dataView.tableInfo).toEqual(mockUploadResponse);
      expect(state.dataView.previewRows).toEqual(
        mockUploadResponse.sample_rows
      );
      expect(state.dataView.isLoading).toBe(false);
      expect(state.dataView.error).toBeNull();

      // Dashboard state should remain unchanged
      expect(state.dashboardView.queryResults).toBeNull();
      expect(state.dashboardView.charts).toEqual([]);
      expect(state.dashboardView.currentChart).toBeNull();
    });

    it("should set data view loading state", () => {
      manager.setDataViewLoading(true);

      const state = manager.getState();
      expect(state.dataView.isLoading).toBe(true);

      // Dashboard state should remain unchanged
      expect(state.dashboardView.isLoading).toBe(false);
    });

    it("should set data view error", () => {
      const errorMessage = "Upload failed";
      manager.setDataViewError(errorMessage);

      const state = manager.getState();
      expect(state.dataView.error).toBe(errorMessage);
      expect(state.dataView.isLoading).toBe(false);

      // Dashboard state should remain unchanged
      expect(state.dashboardView.error).toBeNull();
    });
  });

  describe("Dashboard View Management", () => {
    it("should update dashboard data without affecting data state", () => {
      // First set up some data state
      const mockUploadResponse: UploadResponse = {
        table: "test_table",
        columns: [{ name: "id", type: "INTEGER" }],
        sample_rows: [["1"], ["2"]],
        total_rows: 2,
      };
      manager.updateRawData(mockUploadResponse);

      // Now update dashboard state
      const mockExecuteResponse: ExecuteResponse = {
        columns: ["count"],
        rows: [["2"]],
        row_count: 1,
        runtime_ms: 50,
      };

      const mockChart: ChartConfig = {
        id: "chart1",
        type: "bar",
      };

      const query = "SELECT COUNT(*) as count FROM test_table";

      manager.updateDashboardData(mockExecuteResponse, mockChart, query, false);

      const state = manager.getState();

      // Dashboard state should be updated
      expect(state.dashboardView.queryResults).toEqual(mockExecuteResponse);
      expect(state.dashboardView.currentChart).toEqual(mockChart);
      expect(state.dashboardView.currentQuery).toBe(query);
      expect(state.dashboardView.charts).toContain(mockChart);
      expect(state.dashboardView.isLoading).toBe(false);
      expect(state.dashboardView.error).toBeNull();

      // Data state should remain unchanged
      expect(state.dataView.tableInfo).toEqual(mockUploadResponse);
      expect(state.dataView.previewRows).toEqual(
        mockUploadResponse.sample_rows
      );
    });

    it("should auto-switch to dashboard view when creating visualizations", () => {
      const mockExecuteResponse: ExecuteResponse = {
        columns: ["count"],
        rows: [["2"]],
        row_count: 1,
        runtime_ms: 50,
      };

      const mockChart: ChartConfig = {
        id: "chart1",
        type: "bar",
      };

      // Start in data view
      expect(manager.getCurrentView()).toBe("data");

      // Update dashboard with auto-switch enabled (default)
      manager.updateDashboardData(mockExecuteResponse, mockChart, "test query");

      // Should auto-switch to dashboard view
      expect(manager.getCurrentView()).toBe("dashboard");
    });

    it("should not auto-switch when disabled", () => {
      const mockExecuteResponse: ExecuteResponse = {
        columns: ["count"],
        rows: [["2"]],
        row_count: 1,
        runtime_ms: 50,
      };

      const mockChart: ChartConfig = {
        id: "chart1",
        type: "bar",
      };

      // Start in data view
      expect(manager.getCurrentView()).toBe("data");

      // Update dashboard with auto-switch disabled
      manager.updateDashboardData(
        mockExecuteResponse,
        mockChart,
        "test query",
        false
      );

      // Should remain in data view
      expect(manager.getCurrentView()).toBe("data");
    });
  });

  describe("View Switching", () => {
    it("should switch views while preserving both states", () => {
      // Set up both data and dashboard states
      const mockUploadResponse: UploadResponse = {
        table: "test_table",
        columns: [{ name: "id", type: "INTEGER" }],
        sample_rows: [["1"], ["2"]],
        total_rows: 2,
      };
      manager.updateRawData(mockUploadResponse);

      const mockExecuteResponse: ExecuteResponse = {
        columns: ["count"],
        rows: [["2"]],
        row_count: 1,
        runtime_ms: 50,
      };
      manager.updateDashboardData(
        mockExecuteResponse,
        undefined,
        "test query",
        false
      );

      // Switch to dashboard view
      manager.switchView("dashboard");
      expect(manager.getCurrentView()).toBe("dashboard");

      // Both states should be preserved
      const state = manager.getState();
      expect(state.dataView.tableInfo).toEqual(mockUploadResponse);
      expect(state.dashboardView.queryResults).toEqual(mockExecuteResponse);

      // Switch back to data view
      manager.switchView("data");
      expect(manager.getCurrentView()).toBe("data");

      // Both states should still be preserved
      const state2 = manager.getState();
      expect(state2.dataView.tableInfo).toEqual(mockUploadResponse);
      expect(state2.dashboardView.queryResults).toEqual(mockExecuteResponse);
    });
  });

  describe("State Listeners", () => {
    it("should notify listeners of state changes", () => {
      const listener = vi.fn();
      const unsubscribe = manager.subscribe(listener);

      manager.switchView("dashboard");

      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({
          currentView: "dashboard",
        })
      );

      unsubscribe();

      // Should not notify after unsubscribe
      listener.mockClear();
      manager.switchView("data");
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe("Utility Methods", () => {
    it("should correctly report data availability", () => {
      expect(manager.hasData()).toBe(false);

      const mockUploadResponse: UploadResponse = {
        table: "test_table",
        columns: [{ name: "id", type: "INTEGER" }],
        sample_rows: [["1"]],
        total_rows: 1,
      };
      manager.updateRawData(mockUploadResponse);

      expect(manager.hasData()).toBe(true);
    });

    it("should correctly report chart availability", () => {
      expect(manager.hasCharts()).toBe(false);

      const mockChart: ChartConfig = {
        id: "chart1",
        type: "bar",
      };
      manager.addChart(mockChart);

      expect(manager.hasCharts()).toBe(true);
    });

    it("should correctly report loading state", () => {
      expect(manager.isLoading()).toBe(false);

      manager.setDataViewLoading(true);
      expect(manager.isLoading()).toBe(true);

      manager.setDataViewLoading(false);
      manager.setDashboardViewLoading(true);
      expect(manager.isLoading()).toBe(true);

      manager.setDashboardViewLoading(false);
      expect(manager.isLoading()).toBe(false);
    });
  });

  describe("Singleton Instance", () => {
    it("should provide a singleton instance", () => {
      expect(viewStateManager).toBeInstanceOf(ViewStateManager);
    });
  });
});
