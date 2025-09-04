import { useEffect, useState } from "react";
import { ChartRenderer } from "./ChartRenderer";
import ViewToggle from "./ViewToggle";
import DataTableView from "./DataTableView";
import ViewTransition from "./ViewTransition";
import { ChartConfig, ExecuteResponse } from "../types";
import { ViewType } from "../types/layout";
import { viewStateManager, ViewState } from "../services/viewStateManager";
import { DashboardLoadingOverlay, ViewTransitionLoading } from "./LoadingState";

interface DashboardWorkspaceProps {
  // Legacy props for backward compatibility - will be replaced by ViewStateManager
  tableInfo?: {
    table: string;
    columns: Array<{ name: string; type: string }>;
    sample_rows?: any[][];
    total_rows?: number;
  };
  queryResults?: ExecuteResponse | null;
  currentChart?: ChartConfig | null;
  currentQuery?: string;
  onSaveDashboard: (name: string) => void;
  onNewQuery?: () => void;
  isLoading?: boolean;
  currentView?: ViewType;
  onViewChange?: (view: ViewType) => void;
  loadingMessage?: string;
  isTransitioning?: boolean;
  transitionFromView?: string;
  transitionToView?: string;
}

export default function DashboardWorkspace({
  tableInfo: legacyTableInfo,
  queryResults: legacyQueryResults,
  currentChart: legacyCurrentChart,
  currentQuery: legacyCurrentQuery,
  onSaveDashboard,
  isLoading: legacyIsLoading,
  currentView: legacyCurrentView,
  onViewChange: legacyOnViewChange,
  loadingMessage,
  isTransitioning = false,
  transitionFromView,
  transitionToView,
}: DashboardWorkspaceProps) {
  // Use ViewStateManager for state management
  const [viewState, setViewState] = useState<ViewState>(
    viewStateManager.getState()
  );

  // Subscribe to ViewStateManager updates
  useEffect(() => {
    const unsubscribe = viewStateManager.subscribe(setViewState);
    return unsubscribe;
  }, []);

  // Extract state from ViewStateManager
  const { currentView, dataView, dashboardView } = viewState;
  const { tableInfo, previewRows, isLoading: dataLoading } = dataView;
  const {
    queryResults,
    currentChart,
    currentQuery,
    isLoading: dashboardLoading,
  } = dashboardView;

  // Determine loading state
  const isLoading = dataLoading || dashboardLoading || legacyIsLoading || false;

  // Handle view changes through ViewStateManager
  const handleViewChange = (view: ViewType) => {
    viewStateManager.switchView(view);
    // Also call legacy handler for backward compatibility
    if (legacyOnViewChange) {
      legacyOnViewChange(view);
    }
  };

  // Use ViewStateManager state, fallback to legacy props for backward compatibility
  const effectiveTableInfo = tableInfo || legacyTableInfo;
  const effectiveQueryResults = queryResults || legacyQueryResults;
  const effectiveCurrentChart = currentChart || legacyCurrentChart;
  const effectiveCurrentQuery = currentQuery || legacyCurrentQuery || "";
  const effectiveCurrentView = currentView || legacyCurrentView || "data";

  // Determine if we have charts available for the toggle
  const hasCharts = Boolean(effectiveQueryResults && effectiveCurrentChart);
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-black">
              {effectiveCurrentView === "dashboard" ? "Dashboard" : "Data"}
            </h2>
            {effectiveTableInfo && (
              <p className="text-sm text-gray-600">
                Table: {effectiveTableInfo.table} (
                {effectiveTableInfo.columns.length} columns)
              </p>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* View Toggle */}
            <ViewToggle
              currentView={effectiveCurrentView}
              onViewChange={handleViewChange}
              hasCharts={hasCharts}
            />

            <div className="flex gap-2">
              {hasCharts && effectiveCurrentView === "dashboard" && (
                <button
                  onClick={() => {
                    const name = prompt("Enter dashboard name:");
                    if (name) {
                      onSaveDashboard(name);
                    }
                  }}
                  disabled={isLoading}
                  className="btn-primary"
                >
                  Save Dashboard
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content with smooth transitions */}
      <div className="flex-1">
        {isTransitioning && (
          <ViewTransitionLoading
            isLoading={true}
            fromView={transitionFromView}
            toView={transitionToView}
          />
        )}
        <DashboardLoadingOverlay
          isLoading={isLoading && !isTransitioning}
          message={loadingMessage || "Loading workspace..."}
        >
          <ViewTransition
            currentView={effectiveCurrentView}
            isLoading={isLoading}
            transitionType="slide"
            animationDuration={200}
            className="h-full"
            dashboardContent={
              // Dashboard View - only show dashboard state, never data state
              effectiveQueryResults && effectiveCurrentChart ? (
                <div className="p-6 h-full overflow-auto">
                  {/* Query Info */}
                  <div className="mb-6">
                    <h3 className="font-medium text-black mb-2">
                      Current Query
                    </h3>
                    <p className="text-gray-600 bg-gray-50 p-3 border border-gray-200">
                      {effectiveCurrentQuery}
                    </p>
                  </div>

                  {/* Chart */}
                  <div className="mb-6">
                    <h3 className="font-medium text-black mb-4">
                      Visualization
                    </h3>
                    <div className="border border-gray-200 p-4">
                      <ChartRenderer
                        data={effectiveQueryResults}
                        config={effectiveCurrentChart}
                      />
                    </div>
                  </div>

                  {/* Results Summary */}
                  <div className="text-sm text-gray-600">
                    <p>
                      {effectiveQueryResults.row_count} rows returned in{" "}
                      {effectiveQueryResults.runtime_ms}ms
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 p-8">
                  <div className="text-center max-w-md">
                    <svg
                      className="w-16 h-16 mx-auto mb-4 text-gray-300"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Ready to create your dashboard
                    </h3>
                    <p className="text-gray-600">
                      Ask a question about your data in the conversation pane to
                      get started
                    </p>
                  </div>
                </div>
              )
            }
            dataContent={
              // Data Table View - only show data state, never dashboard state
              effectiveTableInfo ? (
                <div className="h-full flex flex-col">
                  <div className="flex-1 p-4 min-h-0">
                    <DataTableView
                      tableInfo={effectiveTableInfo}
                      data={previewRows || effectiveTableInfo.sample_rows || []}
                      isLoading={dataLoading}
                      className="h-full"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 p-8">
                  <div className="text-center max-w-md">
                    <svg
                      className="w-16 h-16 mx-auto mb-4 text-gray-300"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No Data Available
                    </h3>
                    <p className="text-gray-600">
                      Upload a CSV file to see your data here
                    </p>
                  </div>
                </div>
              )
            }
          />
        </DashboardLoadingOverlay>
      </div>
    </div>
  );
}
