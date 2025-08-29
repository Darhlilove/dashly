import React from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ChartConfig, ChartData } from "../types";
import { selectChartType, validateChartConfig } from "../utils/chartSelector";

interface ChartRendererProps {
  data: ChartData;
  config?: ChartConfig;
  width?: number;
  height?: number;
  className?: string;
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
 */
export const ChartRenderer: React.FC<ChartRendererProps> = ({
  data,
  config,
  width,
  height = 400,
  className = "",
}) => {
  // Use provided config or automatically select chart type
  const chartConfig = config || selectChartType(data);

  // Validate configuration
  if (!validateChartConfig(data, chartConfig)) {
    return (
      <div className={`p-4 border border-red-200 rounded-lg bg-red-50 ${className}`}>
        <p className="text-red-600">
          Invalid chart configuration for the provided data.
        </p>
      </div>
    );
  }

  // Transform data for chart rendering
  const chartData = transformDataForChart(data, chartConfig);

  if (chartData.length === 0) {
    return (
      <div className={`p-4 border border-gray-200 rounded-lg bg-gray-50 ${className}`}>
        <p className="text-gray-600">No data available for chart rendering.</p>
      </div>
    );
  }

  const containerProps = {
    width: width || "100%",
    height,
  };

  switch (chartConfig.type) {
    case "line":
      return (
        <div className={`w-full ${className}`}>
          <ResponsiveContainer {...containerProps}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey={chartConfig.x} 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey={chartConfig.y}
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
              {chartConfig.groupBy && (
                <Line
                  type="monotone"
                  dataKey={chartConfig.groupBy}
                  stroke={CHART_COLORS[1]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      );

    case "bar":
      return (
        <div className={`w-full ${className}`}>
          <ResponsiveContainer {...containerProps}>
            <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey={chartConfig.x} 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey={chartConfig.y} fill={CHART_COLORS[0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );

    case "pie":
      return (
        <div className={`w-full ${className}`}>
          <ResponsiveContainer {...containerProps}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={Math.min(height * 0.35, 120)}
                fill="#8884d8"
                dataKey={chartConfig.y}
                nameKey={chartConfig.x}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );

    case "table":
    default:
      return <TableView data={data} className={className} />;
  }
};

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
      if (typeof value === "string" && !isNaN(Number(value)) && value.trim() !== "") {
        value = Number(value);
      }
      
      obj[col] = value;
    });
    return obj;
  });
}

/**
 * Fallback table view component
 */
const TableView: React.FC<{ data: ChartData; className?: string }> = ({ 
  data, 
  className = "" 
}) => {
  const { columns, rows } = data;

  if (rows.length === 0) {
    return (
      <div className={`p-4 text-center text-gray-500 ${className}`}>
        No data to display
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
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
                  className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                >
                  {cell?.toString() || ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && (
        <div className="p-4 text-center text-gray-500 text-sm">
          Showing first 100 rows of {rows.length} total rows
        </div>
      )}
    </div>
  );
};

export default ChartRenderer;