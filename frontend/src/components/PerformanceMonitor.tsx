/**
 * Performance monitoring overlay component for automatic execution
 */

import React, { useState, useEffect } from "react";
import { sessionCache } from "../utils/cache";
import { performanceMonitor } from "../utils/performance";

interface PerformanceMonitorProps {
  isVisible: boolean;
  onClose: () => void;
  executionMetrics?: {
    totalExecutions: number;
    successfulExecutions: number;
    averageExecutionTime: number;
    cacheHitRate: number;
    slowExecutionsCount: number;
  };
}

export default function PerformanceMonitor({
  isVisible,
  onClose,
  executionMetrics,
}: PerformanceMonitorProps) {
  const [cacheMetrics, setCacheMetrics] = useState(
    sessionCache.getCachePerformanceMetrics()
  );
  const [cacheStats, setCacheStats] = useState(sessionCache.getCacheStats());
  const [generalMetrics, setGeneralMetrics] = useState(
    performanceMonitor.getMetrics()
  );

  // Refresh metrics every 5 seconds when visible
  useEffect(() => {
    if (!isVisible) return;

    const interval = setInterval(() => {
      setCacheMetrics(sessionCache.getCachePerformanceMetrics());
      setCacheStats(sessionCache.getCacheStats());
      setGeneralMetrics(performanceMonitor.getMetrics());
    }, 5000);

    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="fixed top-4 right-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 max-w-md z-50">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Performance Monitor
        </h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          ✕
        </button>
      </div>

      <div className="space-y-4 text-sm">
        {/* Automatic Execution Metrics */}
        {executionMetrics && (
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">
              Automatic Execution
            </h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Total:</span>
                <span className="ml-1 font-mono">
                  {executionMetrics.totalExecutions}
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">
                  Success:
                </span>
                <span className="ml-1 font-mono text-green-600">
                  {(
                    (executionMetrics.successfulExecutions /
                      executionMetrics.totalExecutions) *
                    100
                  ).toFixed(0)}
                  %
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">
                  Avg Time:
                </span>
                <span className="ml-1 font-mono">
                  {formatTime(executionMetrics.averageExecutionTime)}
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">
                  Cache Hit:
                </span>
                <span className="ml-1 font-mono text-blue-600">
                  {(executionMetrics.cacheHitRate * 100).toFixed(0)}%
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-600 dark:text-gray-400">
                  Slow Queries:
                </span>
                <span className="ml-1 font-mono text-orange-600">
                  {executionMetrics.slowExecutionsCount} (
                  {(
                    (executionMetrics.slowExecutionsCount /
                      executionMetrics.totalExecutions) *
                    100
                  ).toFixed(0)}
                  %)
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Cache Performance */}
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">
            Cache Performance
          </h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Entries:</span>
              <span className="ml-1 font-mono">{cacheStats.queryCount}</span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Size:</span>
              <span className="ml-1 font-mono">
                {formatBytes(cacheStats.totalSize)}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">
                Hit Rate:
              </span>
              <span className="ml-1 font-mono text-blue-600">
                {(cacheMetrics.hitRate * 100).toFixed(0)}%
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Avg Age:</span>
              <span className="ml-1 font-mono">
                {cacheMetrics.averageAge}min
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-600 dark:text-gray-400">
                Efficiency:
              </span>
              <span
                className={`ml-1 font-mono ${
                  cacheMetrics.cacheEfficiency === "Excellent"
                    ? "text-green-600"
                    : cacheMetrics.cacheEfficiency === "Good"
                    ? "text-blue-600"
                    : "text-orange-600"
                }`}
              >
                {cacheMetrics.cacheEfficiency}
              </span>
            </div>
          </div>
        </div>

        {/* General Performance */}
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">
            General Performance
          </h4>
          <div className="text-xs space-y-1">
            {generalMetrics.slice(0, 5).map((metric, index) => (
              <div key={index} className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400 truncate">
                  {metric.name}:
                </span>
                <span className="font-mono ml-2">
                  {formatTime(metric.duration)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {
              sessionCache.logCachePerformance();
              console.log("📊 Performance metrics logged to console");
            }}
            className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
          >
            Log Details
          </button>
          <button
            onClick={() => {
              sessionCache.clearAllCache();
              performanceMonitor.clearMetrics();
              console.log("🧹 Performance data cleared");
            }}
            className="px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-800"
          >
            Clear Data
          </button>
        </div>
      </div>
    </div>
  );
}
