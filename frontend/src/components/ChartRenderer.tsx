import React, { useState, memo, useMemo, lazy, Suspense } from "react";
import { ChartConfig, ChartData } from "../types";
import { selectChartType, validateChartConfig } from "../utils/chartSelector";
import SaveDashboardModal from "./SaveDashboardModal";
import { LoadingSpinner } from "./";

// Lazy load chart components for better performance
const LineChartComponent = lazy(() => import("./charts/LineChartComponent"));
const BarChartComponent = lazy(() => import("./charts/BarChartComponent"));
const PieChartComponent = lazy(() => import("./charts/PieChartComponent"));

interface ChartRendererProps {
  data: ChartData;
  config?: ChartConfig;
  width?: number;
  height?: number;
  className?: string;
  onSaveDashboard?: (name: string) => void;
  isLoading?: boolean;
}

// Color palette for charts
const CHART_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Green
  "#F59E0B", // Yellow
  "#EF4444", // Red
  "#8B5CF6", // Purple
  "#06B6D4", // Cyan
  "#F97316", // Orange
  "#84CC16", // Lime
];

/**
 * ChartRenderer component with automatic chart selection
 * Renders appropriate chart type based on data shape or provided configuration
 * Memoized for performance optimization
 */
export const ChartRenderer: React.FC<ChartRendererProps> = memo(
  ({
    data,
    config,
    width,
    height = 400,
    className = "",
    onSaveDashboard,
    isLoading = false,
  }) => {
    const [showSaveModal, setShowSaveModal] = useState(false);

    // Memoize chart configuration to prevent unnecessary recalculations
    const chartConfig = useMemo(() => {
      return config || selectChartType(data);
    }, [config, data]);

    // Memoize chart data transformation to prevent unnecessary recalculations
    const chartData = useMemo(() => {
      return transformDataForChart(data, chartConfig);
    }, [data, chartConfig]);

    // Validate configuration
    if (!validateChartConfig(data, chartConfig)) {
      return (
        <div
          className={`p-4 border border-red-200 rounded-lg bg-red-50 ${className}`}
        >
          <p className="text-red-600">
            Invalid chart configuration for the provided data.
          </p>
        </div>
      );
    }

    // Handle dashboard save
    const handleSaveDashboard = (name: string) => {
      onSaveDashboard?.(name);
      setShowSaveModal(false);
    };

    // Check if save functionality is available
    const canSave = Boolean(onSaveDashboard);

    if (chartData.length === 0) {
      return (
        <div
          className={`p-4 border border-gray-200 rounded-lg bg-gray-50 ${className}`}
        >
          <p className="text-gray-600">
            No data available for chart rendering.
          </p>
        </div>
      );
    }

    const renderSaveButton = () => {
      if (!canSave) return null;

      return (
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setShowSaveModal(true)}
            disabled={isLoading}
            className="px-3 sm:px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
            aria-label="Save current dashboard configuration"
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <span className="hidden sm:inline">Save Dashboard</span>
            <span className="sm:hidden">Save</span>
          </button>
        </div>
      );
    };

    const chartFallback = (
      <div className="flex items-center justify-center" style={{ height }}>
        <LoadingSpinner size="md" />
      </div>
    );

    switch (chartConfig.type) {
      case "line":
        return (
          <div
            className={`w-full ${className}`}
            role="img"
            aria-label={`Line chart showing ${chartConfig.y} over ${chartConfig.x}`}
          >
            {renderSaveButton()}
            <div className="bg-white rounded-lg border border-gray-200 p-2 sm:p-4">
              <Suspense fallback={chartFallback}>
                <LineChartComponent
                  data={chartData}
                  config={chartConfig}
                  colors={CHART_COLORS}
                  height={height}
                />
              </Suspense>
            </div>
            <SaveDashboardModal
              isOpen={showSaveModal}
              onClose={() => setShowSaveModal(false)}
              onSave={handleSaveDashboard}
              isLoading={isLoading}
            />
          </div>
        );

      case "bar":
        return (
          <div
            className={`w-full ${className}`}
            role="img"
            aria-label={`Bar chart showing ${chartConfig.y || "value"} by ${
              chartConfig.x
            }`}
          >
            {renderSaveButton()}
            <div className="bg-white rounded-lg border border-gray-200 p-2 sm:p-4">
              <Suspense fallback={chartFallback}>
                <BarChartComponent
                  data={chartData}
                  config={chartConfig}
                  colors={CHART_COLORS}
                  height={height}
                />
              </Suspense>
            </div>
            <SaveDashboardModal
              isOpen={showSaveModal}
              onClose={() => setShowSaveModal(false)}
              onSave={handleSaveDashboard}
              isLoading={isLoading}
            />
          </div>
        );

      case "pie":
        return (
          <div
            className={`w-full ${className}`}
            role="img"
            aria-label={`Pie chart showing distribution of ${
              chartConfig.y || "value"
            } by ${chartConfig.x || "category"}`}
          >
            {renderSaveButton()}
            <div className="bg-white rounded-lg border border-gray-200 p-2 sm:p-4">
              <Suspense fallback={chartFallback}>
                <PieChartComponent
                  data={chartData}
                  config={chartConfig}
                  colors={CHART_COLORS}
                  height={height}
                />
              </Suspense>
            </div>
            <SaveDashboardModal
              isOpen={showSaveModal}
              onClose={() => setShowSaveModal(false)}
              onSave={handleSaveDashboard}
              isLoading={isLoading}
            />
          </div>
        );

      case "table":
      default:
        return (
          <div className={`w-full ${className}`}>
            {renderSaveButton()}
            <TableView data={data} className="" />
            <SaveDashboardModal
              isOpen={showSaveModal}
              onClose={() => setShowSaveModal(false)}
              onSave={handleSaveDashboard}
              isLoading={isLoading}
            />
          </div>
        );
    }
  },
  (prevProps, nextProps) => {
    // Custom comparison function for React.memo
    // Only re-render if data, config, or key props change
    return (
      prevProps.data === nextProps.data &&
      prevProps.config === nextProps.config &&
      prevProps.width === nextProps.width &&
      prevProps.height === nextProps.height &&
      prevProps.isLoading === nextProps.isLoading &&
      prevProps.onSaveDashboard === nextProps.onSaveDashboard
    );
  }
);

/**
 * Transforms raw data into format suitable for chart rendering
 */
function transformDataForChart(data: ChartData, config: ChartConfig): any[] {
  const { columns, rows } = data;

  if (config.type === "table") {
    return rows.map((row) => {
      const obj: any = {};
      columns.forEach((col, index) => {
        obj[col] = row[index];
      });
      return obj;
    });
  }

  // Apply limit if specified
  const limitedRows = config.limit ? rows.slice(0, config.limit) : rows;

  return limitedRows.map((row) => {
    const obj: any = {};
    columns.forEach((col, index) => {
      let value = row[index];

      // Convert numeric strings to numbers for chart rendering
      if (
        typeof value === "string" &&
        !isNaN(Number(value)) &&
        value.trim() !== ""
      ) {
        value = Number(value);
      }

      obj[col] = value;
    });
    return obj;
  });
}

/**
 * Fallback table view component - memoized for performance
 */
const TableView: React.FC<{ data: ChartData; className?: string }> = memo(
  ({ data, className = "" }) => {
    const { columns, rows } = data;

    if (rows.length === 0) {
      return (
        <div
          className={`p-4 text-center text-gray-500 ${className}`}
          role="status"
        >
          No data to display
        </div>
      );
    }

    return (
      <div
        className={`bg-white rounded-lg border border-gray-200 ${className}`}
      >
        <div className="overflow-x-auto">
          <table
            className="min-w-full divide-y divide-gray-200"
            role="table"
            aria-label="Data table"
          >
            <thead className="bg-gray-50">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    scope="col"
                    className="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rows.slice(0, 100).map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-50">
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className="px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900"
                    >
                      {cell?.toString() || ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length > 100 && (
          <div
            className="p-4 text-center text-gray-500 text-sm border-t border-gray-200"
            role="status"
          >
            Showing first 100 rows of {rows.length} total rows
          </div>
        )}
      </div>
    );
  }
);

export { SaveDashboardModal };
export default ChartRenderer;
