/**
 * ViewStateManager - Service for managing separate data and dashboard view states
 *
 * This service ensures that:
 * - Raw data view state is preserved independently from dashboard state
 * - Chat responses only update dashboard state, never data table state
 * - View switching preserves both states
 * - Data upload only affects data view state
 *
 * Requirements: 2.1, 2.2, 2.3, 2.4
 */

import { UploadResponse, ExecuteResponse } from "../types/api";
import { ChartConfig } from "../types/chart";
import { ViewType } from "../types/layout";

export interface DataViewState {
  tableInfo: UploadResponse | null;
  previewRows: any[][] | null;
  isLoading: boolean;
  error: string | null;
}

export interface DashboardViewState {
  queryResults: ExecuteResponse | null;
  charts: ChartConfig[];
  currentChart: ChartConfig | null;
  currentQuery: string;
  isLoading: boolean;
  error: string | null;
}

export interface ViewState {
  currentView: ViewType;
  dataView: DataViewState;
  dashboardView: DashboardViewState;
}

export type ViewStateListener = (state: ViewState) => void;

class ViewStateManager {
  private state: ViewState;
  private listeners: Set<ViewStateListener> = new Set();

  constructor() {
    this.state = {
      currentView: "data", // Default to data view as per requirements
      dataView: {
        tableInfo: null,
        previewRows: null,
        isLoading: false,
        error: null,
      },
      dashboardView: {
        queryResults: null,
        charts: [],
        currentChart: null,
        currentQuery: "",
        isLoading: false,
        error: null,
      },
    };
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: ViewStateListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Get current state (read-only)
   */
  getState(): Readonly<ViewState> {
    return { ...this.state };
  }

  /**
   * Get current view type
   */
  getCurrentView(): ViewType {
    return this.state.currentView;
  }

  /**
   * Get data view state
   */
  getDataViewState(): Readonly<DataViewState> {
    return { ...this.state.dataView };
  }

  /**
   * Get dashboard view state
   */
  getDashboardViewState(): Readonly<DashboardViewState> {
    return { ...this.state.dashboardView };
  }

  /**
   * Switch between data and dashboard views
   * Preserves both view states
   */
  switchView(view: ViewType): void {
    if (this.state.currentView !== view) {
      this.updateState({
        currentView: view,
      });
    }
  }

  /**
   * Update raw data state (from CSV upload)
   * Only affects data view, never dashboard view
   */
  updateRawData(data: UploadResponse, previewRows?: any[][]): void {
    this.updateState({
      dataView: {
        ...this.state.dataView,
        tableInfo: data,
        previewRows: previewRows || data.sample_rows || null,
        isLoading: false,
        error: null,
      },
    });
  }

  /**
   * Set data view loading state
   */
  setDataViewLoading(isLoading: boolean): void {
    this.updateState({
      dataView: {
        ...this.state.dataView,
        isLoading,
      },
    });
  }

  /**
   * Set data view error
   */
  setDataViewError(error: string | null): void {
    this.updateState({
      dataView: {
        ...this.state.dataView,
        error,
        isLoading: false,
      },
    });
  }

  /**
   * Update dashboard data (from chat query results)
   * Only affects dashboard view, never data view
   * Automatically switches to dashboard view when new visualizations are created
   */
  updateDashboardData(
    data: ExecuteResponse,
    chart?: ChartConfig,
    query?: string,
    autoSwitchView: boolean = true
  ): void {
    const newCharts = chart
      ? [
          ...this.state.dashboardView.charts.filter(
            (c) => !chart.id || c.id !== chart.id
          ),
          chart,
        ]
      : this.state.dashboardView.charts;

    const updates: Partial<ViewState> = {
      dashboardView: {
        ...this.state.dashboardView,
        queryResults: data,
        currentChart: chart || this.state.dashboardView.currentChart,
        currentQuery: query || this.state.dashboardView.currentQuery,
        charts: newCharts,
        isLoading: false,
        error: null,
      },
    };

    // Auto-switch to dashboard view when new visualizations are created
    if (autoSwitchView && chart && this.state.currentView === "data") {
      updates.currentView = "dashboard";
    }

    this.updateState(updates);
  }

  /**
   * Set dashboard view loading state
   */
  setDashboardViewLoading(isLoading: boolean): void {
    this.updateState({
      dashboardView: {
        ...this.state.dashboardView,
        isLoading,
      },
    });
  }

  /**
   * Set dashboard view error
   */
  setDashboardViewError(error: string | null): void {
    this.updateState({
      dashboardView: {
        ...this.state.dashboardView,
        error,
        isLoading: false,
      },
    });
  }

  /**
   * Update current query (for dashboard view)
   */
  updateCurrentQuery(query: string): void {
    this.updateState({
      dashboardView: {
        ...this.state.dashboardView,
        currentQuery: query,
      },
    });
  }

  /**
   * Add a chart to the dashboard without replacing existing ones
   */
  addChart(chart: ChartConfig): void {
    const existingCharts = this.state.dashboardView.charts.filter(
      (c) => !chart.id || c.id !== chart.id
    );
    this.updateState({
      dashboardView: {
        ...this.state.dashboardView,
        charts: [...existingCharts, chart],
        currentChart: chart,
      },
    });
  }

  /**
   * Remove a chart from the dashboard
   */
  removeChart(chartId: string): void {
    const filteredCharts = this.state.dashboardView.charts.filter(
      (c) => c.id !== chartId
    );
    const currentChart =
      this.state.dashboardView.currentChart?.id === chartId
        ? filteredCharts[filteredCharts.length - 1] || null
        : this.state.dashboardView.currentChart;

    this.updateState({
      dashboardView: {
        ...this.state.dashboardView,
        charts: filteredCharts,
        currentChart,
      },
    });
  }

  /**
   * Clear dashboard state (keep data view intact)
   */
  clearDashboard(): void {
    this.updateState({
      dashboardView: {
        queryResults: null,
        charts: [],
        currentChart: null,
        currentQuery: "",
        isLoading: false,
        error: null,
      },
    });
  }

  /**
   * Clear data view state (keep dashboard intact)
   */
  clearDataView(): void {
    this.updateState({
      dataView: {
        tableInfo: null,
        previewRows: null,
        isLoading: false,
        error: null,
      },
    });
  }

  /**
   * Reset all state to initial values
   */
  reset(): void {
    this.state = {
      currentView: "data",
      dataView: {
        tableInfo: null,
        previewRows: null,
        isLoading: false,
        error: null,
      },
      dashboardView: {
        queryResults: null,
        charts: [],
        currentChart: null,
        currentQuery: "",
        isLoading: false,
        error: null,
      },
    };
    this.notifyListeners();
  }

  /**
   * Check if data is available for analysis
   */
  hasData(): boolean {
    return this.state.dataView.tableInfo !== null;
  }

  /**
   * Check if dashboard has any visualizations
   */
  hasCharts(): boolean {
    return this.state.dashboardView.charts.length > 0;
  }

  /**
   * Check if currently loading any view
   */
  isLoading(): boolean {
    return this.state.dataView.isLoading || this.state.dashboardView.isLoading;
  }

  /**
   * Get combined error state from both views
   */
  getError(): string | null {
    return this.state.dataView.error || this.state.dashboardView.error;
  }

  /**
   * Internal method to update state and notify listeners
   */
  private updateState(updates: Partial<ViewState>): void {
    this.state = {
      ...this.state,
      ...updates,
    };
    this.notifyListeners();
  }

  /**
   * Notify all listeners of state changes
   */
  private notifyListeners(): void {
    const currentState = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(currentState);
      } catch (error) {
        console.error("Error in ViewStateManager listener:", error);
      }
    });
  }
}

// Create singleton instance
export const viewStateManager = new ViewStateManager();

// Export the class for testing
export { ViewStateManager };
