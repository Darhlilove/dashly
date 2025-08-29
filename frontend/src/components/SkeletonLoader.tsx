import React from "react";

interface SkeletonLoaderProps {
  className?: string;
  variant?: "text" | "rectangular" | "circular" | "chart" | "table";
  width?: string | number;
  height?: string | number;
  lines?: number;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  className = "",
  variant = "text",
  width,
  height,
  lines = 1,
}) => {
  const baseClasses = "animate-pulse bg-gray-200 rounded";

  const getVariantClasses = () => {
    switch (variant) {
      case "text":
        return "h-4";
      case "rectangular":
        return "h-32";
      case "circular":
        return "rounded-full";
      case "chart":
        return "h-64";
      case "table":
        return "h-8";
      default:
        return "h-4";
    }
  };

  const getStyle = () => {
    const style: React.CSSProperties = {};
    if (width) style.width = typeof width === "number" ? `${width}px` : width;
    if (height)
      style.height = typeof height === "number" ? `${height}px` : height;
    return style;
  };

  if (variant === "text" && lines > 1) {
    return (
      <div className={className}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`${baseClasses} ${getVariantClasses()} ${
              index < lines - 1 ? "mb-2" : ""
            } ${index === lines - 1 ? "w-3/4" : ""}`}
            style={getStyle()}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${baseClasses} ${getVariantClasses()} ${className}`}
      style={getStyle()}
    />
  );
};

// Specialized skeleton components
export const ChartSkeleton: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <div
    className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}
  >
    <div className="flex justify-between items-center mb-4">
      <SkeletonLoader variant="text" width="40%" />
      <SkeletonLoader variant="rectangular" width="80px" height="32px" />
    </div>
    <SkeletonLoader variant="chart" />
  </div>
);

export const TableSkeleton: React.FC<{
  className?: string;
  rows?: number;
  columns?: number;
}> = ({ className = "", rows = 5, columns = 4 }) => (
  <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {Array.from({ length: columns }).map((_, index) => (
              <th key={index} className="px-6 py-3">
                <SkeletonLoader variant="text" width="80%" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4">
                  <SkeletonLoader variant="text" width="90%" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export const DashboardCardSkeleton: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <div
    className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}
  >
    <div className="mb-3">
      <SkeletonLoader variant="text" width="70%" />
    </div>
    <div className="mb-4">
      <SkeletonLoader variant="text" width="50%" lines={2} />
    </div>
    <SkeletonLoader variant="rectangular" height="120px" />
  </div>
);

export const QueryBoxSkeleton: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
    <div className="mb-4">
      <SkeletonLoader variant="text" width="60%" />
    </div>
    <div className="space-y-4">
      <SkeletonLoader variant="rectangular" height="80px" />
      <div className="flex justify-end">
        <SkeletonLoader variant="rectangular" width="100px" height="40px" />
      </div>
    </div>
  </div>
);

export const UploadWidgetSkeleton: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <div className={`w-full max-w-2xl mx-auto p-6 ${className}`}>
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
      <div className="flex flex-col items-center">
        <SkeletonLoader
          variant="circular"
          width="64px"
          height="64px"
          className="mb-4"
        />
        <SkeletonLoader variant="text" width="60%" className="mb-2" />
        <SkeletonLoader variant="text" width="40%" className="mb-4" />
        <SkeletonLoader variant="rectangular" width="120px" height="40px" />
      </div>
    </div>
    <div className="mt-8 text-center">
      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">or</span>
        </div>
      </div>
      <SkeletonLoader
        variant="rectangular"
        width="140px"
        height="44px"
        className="mx-auto"
      />
    </div>
  </div>
);

export default SkeletonLoader;
