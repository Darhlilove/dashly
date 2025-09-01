import { ChartRenderer } from "./ChartRenderer";
import ViewToggle from "./ViewToggle";
import DataTableView from "./DataTableView";
import ViewTransition from "./ViewTransition";
import { ChartConfig, ExecuteResponse } from "../types";
import { ViewType } from "../types/layout";

interface DashboardWorkspaceProps {
  tableInfo: {
    table: string;
    columns: Array<{ name: string; type: string }>;
  };
  queryResults: ExecuteResponse | null;
  currentChart: ChartConfig | null;
  currentQuery: string;
  onSaveDashboard: (name: string) => void;
  onNewQuery?: () => void;
  isLoading: boolean;
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
}

export default function DashboardWorkspace({
  tableInfo,
  queryResults,
  currentChart,
  currentQuery,
  onSaveDashboard,
  isLoading,
  currentView,
  onViewChange,
}: DashboardWorkspaceProps) {
  // Determine if we have charts available for the toggle
  const hasCharts = Boolean(queryResults && currentChart);
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-black">
              {currentView === "dashboard" ? "Dashboard" : "Data"}
            </h2>
            <p className="text-sm text-gray-600">
              Table: {tableInfo.table} ({tableInfo.columns.length} columns)
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* View Toggle */}
            <ViewToggle
              currentView={currentView}
              onViewChange={onViewChange}
              hasCharts={hasCharts}
            />

            <div className="flex gap-2">
              {hasCharts && currentView === "dashboard" && (
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
        <ViewTransition
          currentView={currentView}
          isLoading={isLoading}
          transitionType="slide"
          animationDuration={200}
          className="h-full"
          dashboardContent={
            // Dashboard View
            queryResults && currentChart ? (
              <div className="p-6 h-full overflow-auto">
                {/* Query Info */}
                <div className="mb-6">
                  <h3 className="font-medium text-black mb-2">Current Query</h3>
                  <p className="text-gray-600 bg-gray-50 p-3 border border-gray-200">
                    {currentQuery}
                  </p>
                </div>

                {/* Chart */}
                <div className="mb-6">
                  <h3 className="font-medium text-black mb-4">Visualization</h3>
                  <div className="border border-gray-200 p-4">
                    <ChartRenderer data={queryResults} config={currentChart} />
                  </div>
                </div>

                {/* Results Summary */}
                <div className="text-sm text-gray-600">
                  <p>
                    {queryResults.row_count} rows returned in{" "}
                    {queryResults.runtime_ms}ms
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
            // Data Table View
            <div className="h-full flex flex-col">
              <div className="flex-1 p-4 min-h-0">
                <DataTableView
                  tableInfo={tableInfo}
                  data={queryResults?.rows || []}
                  isLoading={isLoading}
                  className="h-full"
                />
              </div>
            </div>
          }
        />
      </div>
    </div>
  );
}
