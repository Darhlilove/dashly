import React, { useCallback } from "react";
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
  const handleToggle = useCallback(() => {
    if (disabled) return;

    // Toggle between data and dashboard views
    if (currentView === "data" && hasCharts) {
      onViewChange("dashboard");
    } else if (currentView === "dashboard") {
      onViewChange("data");
    }
  }, [currentView, hasCharts, disabled, onViewChange]);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-sm text-gray-600">Data</span>
      <button
        onClick={handleToggle}
        disabled={disabled || !hasCharts}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2
          ${
            disabled || !hasCharts
              ? "opacity-50 cursor-not-allowed"
              : "cursor-pointer"
          }
          ${
            currentView === "dashboard" && hasCharts
              ? "bg-red-600"
              : "bg-gray-300"
          }
        `}
        aria-label={`Switch to ${
          currentView === "data" ? "dashboard" : "data"
        } view${!hasCharts ? " (no charts available)" : ""}`}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ease-in-out
            ${currentView === "dashboard" ? "translate-x-6" : "translate-x-1"}
          `}
        />
      </button>
      <span className="text-sm text-gray-600">Dashboard</span>
    </div>
  );
};

export default ViewToggle;
