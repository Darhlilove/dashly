import React, { useCallback, useRef } from "react";
import { ViewType } from "../types/layout";

export interface ViewToggleProps {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  hasCharts: boolean;
  disabled?: boolean;
  className?: string;
}

const ViewToggle: React.FC<ViewToggleProps> = ({
  currentView,
  onViewChange,
  hasCharts,
  disabled = false,
  className = "",
}) => {
  const dashboardButtonRef = useRef<HTMLButtonElement>(null);
  const dataButtonRef = useRef<HTMLButtonElement>(null);

  const handleViewChange = useCallback(
    (view: ViewType) => {
      if (disabled) return;

      // Don't allow switching to dashboard view if no charts exist
      if (view === "dashboard" && !hasCharts) return;

      onViewChange(view);
    },
    [disabled, hasCharts, onViewChange]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, view: ViewType) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        handleViewChange(view);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
        const targetView = view === "dashboard" ? "data" : "dashboard";

        // Only switch if the target view is available
        if (targetView === "dashboard" && !hasCharts) return;

        handleViewChange(targetView);

        // Focus the appropriate button
        const targetButton =
          targetView === "dashboard"
            ? dashboardButtonRef.current
            : dataButtonRef.current;
        targetButton?.focus();
      }
    },
    [handleViewChange, hasCharts]
  );

  const baseButtonClasses = `
    relative px-4 py-2 text-sm font-medium transition-all duration-200 ease-in-out
    border-b-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
    disabled:cursor-not-allowed disabled:opacity-50
  `;

  const activeButtonClasses = `
    text-blue-600 border-blue-600 bg-blue-50
  `;

  const inactiveButtonClasses = `
    text-gray-600 border-transparent hover:text-gray-800 hover:border-gray-300
    disabled:hover:text-gray-600 disabled:hover:border-transparent
  `;

  const isDashboardDisabled = disabled || !hasCharts;
  const isDataDisabled = disabled;

  return (
    <div
      className={`flex bg-white border-b border-gray-200 ${className}`}
      role="tablist"
      aria-label="View toggle between dashboard and data table"
    >
      <button
        ref={dashboardButtonRef}
        type="button"
        role="tab"
        aria-selected={currentView === "dashboard"}
        aria-controls="dashboard-panel"
        aria-label={`Switch to dashboard view${
          !hasCharts ? " (no charts available)" : ""
        }`}
        disabled={isDashboardDisabled}
        className={`
          ${baseButtonClasses}
          ${
            currentView === "dashboard"
              ? activeButtonClasses
              : inactiveButtonClasses
          }
        `}
        onClick={() => handleViewChange("dashboard")}
        onKeyDown={(e) => handleKeyDown(e, "dashboard")}
      >
        <span className="flex items-center gap-2">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          Dashboard
        </span>
        {!hasCharts && (
          <span className="ml-1 text-xs text-gray-400" aria-hidden="true">
            (No charts)
          </span>
        )}
      </button>

      <button
        ref={dataButtonRef}
        type="button"
        role="tab"
        aria-selected={currentView === "data"}
        aria-controls="data-panel"
        aria-label="Switch to data table view"
        disabled={isDataDisabled}
        className={`
          ${baseButtonClasses}
          ${
            currentView === "data" ? activeButtonClasses : inactiveButtonClasses
          }
        `}
        onClick={() => handleViewChange("data")}
        onKeyDown={(e) => handleKeyDown(e, "data")}
      >
        <span className="flex items-center gap-2">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          Data
        </span>
      </button>
    </div>
  );
};

export default ViewToggle;
