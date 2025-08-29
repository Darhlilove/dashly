import React from "react";
import { Dashboard } from "../types/dashboard";
import DashboardCard from "./DashboardCard";

interface DashboardGridProps {
  dashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
  isLoading?: boolean;
  className?: string;
}

/**
 * DashboardGrid component renders a responsive grid of dashboard cards
 * with empty state handling
 */
export const DashboardGrid: React.FC<DashboardGridProps> = ({
  dashboards,
  onLoadDashboard,
  isLoading = false,
  className = "",
}) => {
  if (isLoading) {
    return <DashboardGridSkeleton className={className} />;
  }

  if (dashboards.length === 0) {
    return <EmptyDashboardState className={className} />;
  }

  return (
    <div className={`w-full ${className}`}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {dashboards.map((dashboard) => (
          <DashboardCard
            key={dashboard.id}
            dashboard={dashboard}
            onLoad={onLoadDashboard}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * EmptyDashboardState component shown when no dashboards exist
 */
const EmptyDashboardState: React.FC<{ className?: string }> = ({
  className = "",
}) => {
  return (
    <div className={`w-full ${className}`}>
      <div className="text-center py-12">
        <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-12 h-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No dashboards yet
        </h3>
        <p className="text-gray-500 mb-6 max-w-sm mx-auto">
          Create your first dashboard by uploading data and asking a question.
          Your saved dashboards will appear here.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
          <div className="flex items-center text-sm text-gray-400">
            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            Upload CSV → Ask question → Save dashboard
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * DashboardGridSkeleton component shown while loading dashboards
 */
const DashboardGridSkeleton: React.FC<{ className?: string }> = ({
  className = "",
}) => {
  return (
    <div className={`w-full ${className}`}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            {/* Header skeleton */}
            <div className="mb-3">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </div>

            {/* Chart skeleton */}
            <div className="h-32 mb-3 bg-gray-100 rounded"></div>

            {/* Question skeleton */}
            <div className="mb-3">
              <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
              <div className="h-3 bg-gray-200 rounded w-2/3"></div>
            </div>

            {/* Badge skeleton */}
            <div className="flex justify-between items-center">
              <div className="h-5 bg-gray-200 rounded-full w-20"></div>
              <div className="h-4 w-4 bg-gray-200 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export { EmptyDashboardState, DashboardGridSkeleton };
export default DashboardGrid;