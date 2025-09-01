import React, {
  memo,
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
} from "react";
import { UploadResponse } from "../types";
import LoadingSpinner from "./LoadingSpinner";
import { withLayoutErrorBoundary } from "./LayoutErrorBoundary";
import {
  usePerformanceMonitor,
  detectDatasetPerformanceIssues,
} from "../utils/performanceMonitor";
import { createFallbackProps } from "../utils/gracefulDegradation";

interface DataTableViewProps {
  tableInfo: UploadResponse;
  data?: any[][];
  maxRows?: number;
  className?: string;
  virtualScrolling?: boolean;
  isLoading?: boolean;
  onLoadMore?: () => void;
  enableSearch?: boolean;
  enableSort?: boolean;
  enableExport?: boolean;
}

type SortDirection = "asc" | "desc" | null;

interface SortConfig {
  column: number;
  direction: SortDirection;
}

/**
 * DataTableView component for displaying raw uploaded data with column type information
 * Designed specifically for showing table structure and sample data before analysis
 * Supports virtual scrolling, sorting, search, and export functionality
 */
const DataTableView: React.FC<DataTableViewProps> = memo(
  ({
    tableInfo,
    data = [],
    maxRows = 200,
    className = "",
    virtualScrolling = false,
    isLoading = false,
    onLoadMore,
    enableSearch = true,
    enableSort = true,
    enableExport = true,
  }) => {
    const { columns } = tableInfo;
    const containerRef = useRef<HTMLDivElement>(null);
    const [scrollTop, setScrollTop] = useState(0);
    const [containerHeight, setContainerHeight] = useState(400);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortConfig, setSortConfig] = useState<SortConfig>({
      column: -1,
      direction: null,
    });

    // Virtual scrolling configuration
    const ROW_HEIGHT = 48; // Height of each row in pixels
    const BUFFER_SIZE = 5; // Extra rows to render outside viewport

    // Filter data based on search term
    const filteredData = useMemo(() => {
      if (!enableSearch || !searchTerm.trim()) {
        return data;
      }

      const searchLower = searchTerm.toLowerCase();
      return data.filter((row) =>
        row.some((cell) => cell?.toString().toLowerCase().includes(searchLower))
      );
    }, [data, searchTerm, enableSearch]);

    // Sort filtered data
    const sortedData = useMemo(() => {
      if (!enableSort || sortConfig.column === -1 || !sortConfig.direction) {
        return filteredData;
      }

      const sorted = [...filteredData].sort((a, b) => {
        const aVal = a[sortConfig.column];
        const bVal = b[sortConfig.column];

        // Handle null/undefined values
        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return sortConfig.direction === "asc" ? -1 : 1;
        if (bVal == null) return sortConfig.direction === "asc" ? 1 : -1;

        // Convert to strings for comparison
        const aStr = aVal.toString();
        const bStr = bVal.toString();

        // Try numeric comparison first
        const aNum = parseFloat(aStr);
        const bNum = parseFloat(bStr);

        if (!isNaN(aNum) && !isNaN(bNum)) {
          return sortConfig.direction === "asc" ? aNum - bNum : bNum - aNum;
        }

        // Fall back to string comparison
        const comparison = aStr.localeCompare(bStr);
        return sortConfig.direction === "asc" ? comparison : -comparison;
      });

      return sorted;
    }, [filteredData, sortConfig, enableSort]);

    // Calculate visible rows for virtual scrolling
    const { visibleRows, totalHeight, startIndex } = useMemo(() => {
      const dataToUse = sortedData;

      if (!virtualScrolling || dataToUse.length <= maxRows) {
        return {
          visibleRows: dataToUse.slice(0, maxRows),
          totalHeight: Math.min(dataToUse.length, maxRows) * ROW_HEIGHT,
          startIndex: 0,
        };
      }

      const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
      const start = Math.floor(scrollTop / ROW_HEIGHT);
      const bufferedStart = Math.max(0, start - BUFFER_SIZE);
      const bufferedEnd = Math.min(
        dataToUse.length,
        start + visibleCount + BUFFER_SIZE
      );

      return {
        visibleRows: dataToUse.slice(bufferedStart, bufferedEnd),
        totalHeight: dataToUse.length * ROW_HEIGHT,
        startIndex: bufferedStart,
      };
    }, [sortedData, scrollTop, containerHeight, virtualScrolling, maxRows]);

    // Handle scroll events for virtual scrolling
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
      if (virtualScrolling) {
        setScrollTop(e.currentTarget.scrollTop);
      }
    };

    // Handle sorting
    const handleSort = useCallback(
      (columnIndex: number) => {
        if (!enableSort) return;

        setSortConfig((prev) => {
          if (prev.column === columnIndex) {
            // Cycle through: asc -> desc -> none
            const newDirection: SortDirection =
              prev.direction === "asc"
                ? "desc"
                : prev.direction === "desc"
                ? null
                : "asc";
            return {
              column: newDirection ? columnIndex : -1,
              direction: newDirection,
            };
          } else {
            return { column: columnIndex, direction: "asc" };
          }
        });
      },
      [enableSort]
    );

    // Handle export to CSV
    const handleExport = useCallback(() => {
      if (!enableExport) return;

      const csvContent = [
        // Header row
        columns.map((col) => `"${col.name}"`).join(","),
        // Data rows
        ...sortedData.map((row) =>
          row
            .map((cell) => `"${cell?.toString().replace(/"/g, '""') || ""}"`)
            .join(",")
        ),
      ].join("\n");

      try {
        const blob = new Blob([csvContent], {
          type: "text/csv;charset=utf-8;",
        });
        const link = document.createElement("a");

        // Check if URL.createObjectURL is available (not in test environment)
        if (typeof URL !== "undefined" && URL.createObjectURL) {
          const url = URL.createObjectURL(blob);
          link.setAttribute("href", url);
          link.setAttribute("download", `${tableInfo.table}_export.csv`);
          link.style.visibility = "hidden";
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        } else {
          // Fallback for test environments or unsupported browsers
          console.warn(
            "Export functionality not available in this environment"
          );
        }
      } catch (error) {
        console.error("Failed to export CSV:", error);
      }
    }, [enableExport, sortedData, columns, tableInfo.table]);

    // Update container height on resize
    useEffect(() => {
      const updateHeight = () => {
        if (containerRef.current) {
          setContainerHeight(containerRef.current.clientHeight);
        }
      };

      updateHeight();
      window.addEventListener("resize", updateHeight);
      return () => window.removeEventListener("resize", updateHeight);
    }, []);

    // Show empty state if no data
    if (!data || data.length === 0) {
      return (
        <div
          className={`bg-white border border-gray-200 rounded-lg ${className} flex items-center justify-center`}
        >
          <div className="p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 text-gray-300">
              <svg
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                className="w-full h-full"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Data Available
            </h3>
            <p className="text-gray-600">
              Upload a CSV file to see your data here
            </p>
          </div>
        </div>
      );
    }

    const displayingVirtualScroll =
      virtualScrolling && sortedData.length > maxRows;
    const hasMoreRows = !virtualScrolling && sortedData.length > maxRows;

    // Render sort icon
    const renderSortIcon = (columnIndex: number) => {
      if (!enableSort) return null;

      const isActive = sortConfig.column === columnIndex;
      const direction = isActive ? sortConfig.direction : null;

      return (
        <span className="ml-1 inline-flex flex-col">
          <svg
            className={`w-3 h-3 ${
              direction === "asc" ? "text-blue-600" : "text-gray-400"
            }`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
          <svg
            className={`w-3 h-3 -mt-1 ${
              direction === "desc" ? "text-blue-600" : "text-gray-400"
            }`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      );
    };

    return (
      <div
        className={`bg-white border border-gray-200 rounded-lg ${className}`}
      >
        {/* Table Header with Info and Controls */}
        <div className="border-b border-gray-200 p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Data Preview
              </h3>
              <p className="text-sm text-gray-600">
                {sortedData.length} rows × {columns.length} columns
                {displayingVirtualScroll && " (Virtual Scrolling)"}
                {searchTerm && ` (filtered from ${data.length} total)`}
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="text-sm text-gray-500">
                Table: {tableInfo.table}
              </div>
              {enableExport && (
                <button
                  onClick={handleExport}
                  className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 active:bg-blue-200 active:scale-95 focus:outline-none transition-all duration-150"
                >
                  Export CSV
                </button>
              )}
            </div>
          </div>

          {/* Search Bar */}
          {enableSearch && (
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg
                  className="h-4 w-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search data..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:border-gray-400 active:border-gray-400 text-sm"
              />
            </div>
          )}
        </div>

        {/* Table Content */}
        <div
          ref={containerRef}
          className="overflow-auto border border-gray-200 rounded-md"
          style={{ height: "calc(100vh - 280px)", minHeight: "500px" }}
          onScroll={handleScroll}
        >
          {displayingVirtualScroll ? (
            // Virtual scrolling container
            <div
              style={{
                height: totalHeight,
                position: "relative",
                minHeight: "100%",
              }}
            >
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    {columns.map((column, index) => (
                      <th
                        key={column.name}
                        scope="col"
                        className={`px-3 sm:px-6 py-3 text-left ${
                          enableSort ? "cursor-pointer hover:bg-gray-100" : ""
                        }`}
                        onClick={() => handleSort(index)}
                      >
                        <div className="flex flex-col">
                          <div className="flex items-center">
                            <span className="text-xs font-medium text-gray-900 uppercase tracking-wider">
                              {column.name}
                            </span>
                            {renderSortIcon(index)}
                          </div>
                          <span className="text-xs text-gray-500 font-normal mt-1">
                            {column.type}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody
                  className="bg-white divide-y divide-gray-200"
                  style={{
                    transform: `translateY(${startIndex * ROW_HEIGHT}px)`,
                  }}
                >
                  {/* Spacer for virtual scrolling */}
                  {startIndex > 0 && (
                    <tr style={{ height: startIndex * ROW_HEIGHT }}>
                      <td colSpan={columns.length}></td>
                    </tr>
                  )}
                  {visibleRows.map((row, rowIndex) => (
                    <tr
                      key={startIndex + rowIndex}
                      className="hover:bg-gray-50"
                      style={{ height: ROW_HEIGHT }}
                    >
                      {row.map((cell, cellIndex) => (
                        <td
                          key={cellIndex}
                          className="px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900"
                        >
                          <div
                            className="max-w-xs truncate"
                            title={cell?.toString() || ""}
                          >
                            {cell?.toString() || ""}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                  {/* Bottom spacer for virtual scrolling */}
                  {startIndex + visibleRows.length < sortedData.length && (
                    <tr
                      style={{
                        height:
                          (sortedData.length -
                            startIndex -
                            visibleRows.length) *
                          ROW_HEIGHT,
                      }}
                    >
                      <td colSpan={columns.length}></td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            // Regular table for smaller datasets
            <table
              className="min-w-full divide-y divide-gray-200"
              role="table"
              aria-label={`Data table for ${tableInfo.table}`}
            >
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  {columns.map((column, index) => (
                    <th
                      key={column.name}
                      scope="col"
                      className={`px-3 sm:px-6 py-3 text-left ${
                        enableSort ? "cursor-pointer hover:bg-gray-100" : ""
                      }`}
                      onClick={() => handleSort(index)}
                    >
                      <div className="flex flex-col">
                        <div className="flex items-center">
                          <span className="text-xs font-medium text-gray-900 uppercase tracking-wider">
                            {column.name}
                          </span>
                          {renderSortIcon(index)}
                        </div>
                        <span className="text-xs text-gray-500 font-normal mt-1">
                          {column.type}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {visibleRows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-900"
                      >
                        <div
                          className="max-w-xs truncate"
                          title={cell?.toString() || ""}
                        >
                          {cell?.toString() || ""}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="border-t border-gray-200 p-4 text-center">
            <LoadingSpinner size="sm" />
            <span className="ml-2 text-sm text-gray-500">
              Loading more data...
            </span>
          </div>
        )}

        {/* Footer with row count info or pagination */}
        {hasMoreRows && (
          <div className="border-t border-gray-200 p-4 text-center">
            <p className="text-sm text-gray-500 mb-2">
              Showing first {maxRows} rows of {sortedData.length} total rows
            </p>
            {onLoadMore && (
              <button
                onClick={onLoadMore}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Load More Rows
              </button>
            )}
          </div>
        )}
      </div>
    );
  }
);

DataTableView.displayName = "DataTableView";

// Wrap with error boundary (skip in tests to avoid interfering with existing tests)
const DataTableViewWithErrorBoundary =
  process.env.NODE_ENV === "test"
    ? DataTableView
    : withLayoutErrorBoundary(DataTableView, "DataTableView");

export default DataTableViewWithErrorBoundary;
