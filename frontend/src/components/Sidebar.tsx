import { useState } from "react";
import { Dashboard } from "../types";

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  savedDashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
  onNewDashboard: () => void;
  currentDashboardId?: string;
}

export default function Sidebar({
  isCollapsed,
  onToggle,
  savedDashboards,
  onLoadDashboard,
  onNewDashboard,
  currentDashboardId,
}: SidebarProps) {
  const [, setHoveredItem] = useState<string | null>(null);

  if (isCollapsed) {
    return (
      <div className="w-12 sidebar flex flex-col">
        <button
          onClick={onToggle}
          className="p-3 hover:bg-gray-800 transition-colors duration-200"
          aria-label="Expand sidebar"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 sidebar flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h1 className="text-lg font-semibold font-brand">dashly</h1>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-800 transition-colors duration-200"
          aria-label="Collapse sidebar"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      {/* New Dashboard Button */}
      <div className="p-4">
        <button
          onClick={onNewDashboard}
          className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-gray-800 transition-colors duration-200 border border-gray-600"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Dashboard
        </button>
      </div>

      {/* Dashboards List */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 pb-2">
          <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Recent Dashboards
          </h2>
        </div>

        {savedDashboards.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-400 text-sm">
            No dashboards yet
          </div>
        ) : (
          <div className="space-y-1 px-2">
            {savedDashboards.map((dashboard) => (
              <button
                key={dashboard.id}
                onClick={() => onLoadDashboard(dashboard)}
                onMouseEnter={() => setHoveredItem(dashboard.id)}
                onMouseLeave={() => setHoveredItem(null)}
                className={`w-full text-left px-3 py-2 transition-colors duration-200 ${
                  currentDashboardId === dashboard.id
                    ? "bg-gray-800 text-white"
                    : "hover:bg-gray-800 text-gray-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <svg
                    className="w-4 h-4 flex-shrink-0"
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
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">
                      {dashboard.name}
                    </div>
                    <div className="text-xs text-gray-400 truncate">
                      {dashboard.question}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400">
          {savedDashboards.length} dashboard
          {savedDashboards.length !== 1 ? "s" : ""}
        </div>
      </div>
    </div>
  );
}
