import React from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { Dashboard } from "../types/dashboard";


interface DashboardCardProps {
  dashboard: Dashboard;
  onLoad: (dashboard: Dashboard) => void;
  className?: string;
}

// Simplified color palette for mini charts
const MINI_CHART_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Green
  "#F59E0B", // Yellow
  "#EF4444", // Red
  "#8B5CF6", // Purple
];

/**
 * DashboardCard component displays a saved dashboard as a clickable card
 * with title and mini-chart preview
 */
export const DashboardCard: React.FC<DashboardCardProps> = ({
  dashboard,
  onLoad,
  className = "",
}) => {
  const handleClick = () => {
    onLoad(dashboard);
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return "Unknown date";
      }
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "Unknown date";
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`
        bg-white border border-gray-200 rounded-lg p-4 cursor-pointer
        hover:border-blue-300 hover:shadow-md transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        ${className}
      `}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`Load dashboard: ${dashboard.name}`}
      data-testid={`dashboard-card-${dashboard.id}`}
    >
      {/* Header */}
      <div className="mb-3">
        <h3 className="text-lg font-semibold text-gray-900 truncate">
          {dashboard.name}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Created {formatDate(dashboard.createdAt)}
        </p>
      </div>

      {/* Mini Chart Preview */}
      <div className="h-32 mb-3 bg-gray-50 rounded border">
        <MiniChartPreview dashboard={dashboard} />
      </div>

      {/* Question Preview */}
      <div className="text-sm text-gray-600">
        <p className="line-clamp-2" title={dashboard.question}>
          {dashboard.question}
        </p>
      </div>

      {/* Chart Type Badge */}
      <div className="mt-3 flex justify-between items-center">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {dashboard.chartConfig.type.charAt(0).toUpperCase() + 
           dashboard.chartConfig.type.slice(1)} Chart
        </span>
        <svg
          className="w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </div>
    </div>
  );
};

/**
 * MiniChartPreview renders a simplified version of the chart for preview
 */
const MiniChartPreview: React.FC<{ dashboard: Dashboard }> = ({ dashboard }) => {
  const { chartConfig } = dashboard;

  // Generate sample data for preview (since we don't store actual data)
  const generateSampleData = () => {
    switch (chartConfig.type) {
      case "line":
        return [
          { x: "Jan", y: 20 },
          { x: "Feb", y: 35 },
          { x: "Mar", y: 25 },
          { x: "Apr", y: 45 },
          { x: "May", y: 40 },
        ];
      case "bar":
        return [
          { x: "A", y: 30 },
          { x: "B", y: 45 },
          { x: "C", y: 25 },
          { x: "D", y: 35 },
        ];
      case "pie":
        return [
          { name: "A", value: 30 },
          { name: "B", value: 25 },
          { name: "C", value: 20 },
          { name: "D", value: 25 },
        ];
      default:
        return [];
    }
  };

  const sampleData = generateSampleData();

  if (chartConfig.type === "table" || sampleData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <svg
            className="w-8 h-8 text-gray-400 mx-auto mb-2"
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
          <span className="text-xs text-gray-500">Table View</span>
        </div>
      </div>
    );
  }

  if (chartConfig.type === "line") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sampleData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <Line
            type="monotone"
            dataKey="y"
            stroke={MINI_CHART_COLORS[0]}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chartConfig.type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sampleData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <Bar dataKey="y" fill={MINI_CHART_COLORS[0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartConfig.type === "pie") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={sampleData}
            cx="50%"
            cy="50%"
            outerRadius={40}
            fill="#8884d8"
            dataKey="value"
          >
            {sampleData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={MINI_CHART_COLORS[index % MINI_CHART_COLORS.length]}
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return null;
};

export default DashboardCard;