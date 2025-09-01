/**
 * Performance monitoring hook specifically for automatic execution pipeline
 */

import { useCallback, useRef, useEffect } from "react";
import { performanceMonitor } from "../utils/performance";
import { sessionCache } from "../utils/cache";

interface AutomaticExecutionMetrics {
  totalExecutions: number;
  successfulExecutions: number;
  failedExecutions: number;
  averageExecutionTime: number;
  cacheHitRate: number;
  slowExecutionsCount: number;
  lastExecutionTime?: number;
}

interface ExecutionPerformanceData {
  query: string;
  executionTime: number;
  success: boolean;
  fromCache: boolean;
  rowCount: number;
  errorPhase?: "translation" | "execution";
  timestamp: number;
}

export function useAutomaticExecutionPerformance() {
  const executionHistory = useRef<ExecutionPerformanceData[]>([]);
  const performanceThresholds = useRef({
    slowExecution: 5000, // 5 seconds
    verySlowExecution: 10000, // 10 seconds
    maxHistorySize: 50,
  });

  // Record execution performance data
  const recordExecution = useCallback(
    (data: Omit<ExecutionPerformanceData, "timestamp">) => {
      const executionData: ExecutionPerformanceData = {
        ...data,
        timestamp: Date.now(),
      };

      executionHistory.current.push(executionData);

      // Limit history size
      if (
        executionHistory.current.length >
        performanceThresholds.current.maxHistorySize
      ) {
        executionHistory.current = executionHistory.current.slice(
          -performanceThresholds.current.maxHistorySize
        );
      }

      // Log performance warnings
      if (
        data.executionTime > performanceThresholds.current.verySlowExecution
      ) {
        console.warn(
          `🐌 Very slow automatic execution: ${(
            data.executionTime / 1000
          ).toFixed(1)}s for "${data.query.substring(0, 50)}..."`
        );
      } else if (
        data.executionTime > performanceThresholds.current.slowExecution
      ) {
        console.warn(
          `⏳ Slow automatic execution: ${(data.executionTime / 1000).toFixed(
            1
          )}s for "${data.query.substring(0, 50)}..."`
        );
      }

      // Performance monitoring integration
      performanceMonitor.startTimer(
        `automatic_execution_${data.success ? "success" : "failure"}`
      );
      performanceMonitor.endTimer(
        `automatic_execution_${data.success ? "success" : "failure"}`
      );
    },
    []
  );

  // Get current performance metrics
  const getMetrics = useCallback((): AutomaticExecutionMetrics => {
    const history = executionHistory.current;

    if (history.length === 0) {
      return {
        totalExecutions: 0,
        successfulExecutions: 0,
        failedExecutions: 0,
        averageExecutionTime: 0,
        cacheHitRate: 0,
        slowExecutionsCount: 0,
      };
    }

    const totalExecutions = history.length;
    const successfulExecutions = history.filter((h) => h.success).length;
    const failedExecutions = totalExecutions - successfulExecutions;
    const cacheHits = history.filter((h) => h.fromCache).length;
    const cacheHitRate = cacheHits / totalExecutions;
    const slowExecutionsCount = history.filter(
      (h) => h.executionTime > performanceThresholds.current.slowExecution
    ).length;

    const totalExecutionTime = history.reduce(
      (sum, h) => sum + h.executionTime,
      0
    );
    const averageExecutionTime = totalExecutionTime / totalExecutions;

    const lastExecution = history[history.length - 1];

    return {
      totalExecutions,
      successfulExecutions,
      failedExecutions,
      averageExecutionTime,
      cacheHitRate,
      slowExecutionsCount,
      lastExecutionTime: lastExecution?.executionTime,
    };
  }, []);

  // Get performance recommendations
  const getPerformanceRecommendations = useCallback((): string[] => {
    const metrics = getMetrics();
    const recommendations: string[] = [];

    if (metrics.cacheHitRate < 0.3 && metrics.totalExecutions > 5) {
      recommendations.push(
        "Low cache hit rate - consider asking similar questions to benefit from caching"
      );
    }

    if (metrics.averageExecutionTime > 3000) {
      recommendations.push(
        "Slow average execution time - try asking simpler questions or check your internet connection"
      );
    }

    if (
      metrics.slowExecutionsCount / metrics.totalExecutions > 0.5 &&
      metrics.totalExecutions > 3
    ) {
      recommendations.push(
        "Many slow executions detected - consider simplifying queries or checking data size"
      );
    }

    if (
      metrics.failedExecutions / metrics.totalExecutions > 0.3 &&
      metrics.totalExecutions > 3
    ) {
      recommendations.push(
        "High failure rate - try being more specific about the data you want to see"
      );
    }

    const cacheMetrics = sessionCache.getCachePerformanceMetrics();
    if (cacheMetrics.totalRows > 50000) {
      recommendations.push(
        "Large amount of cached data - performance may improve after cache cleanup"
      );
    }

    return recommendations;
  }, [getMetrics]);

  // Log comprehensive performance summary
  const logPerformanceSummary = useCallback(() => {
    const metrics = getMetrics();
    const recommendations = getPerformanceRecommendations();
    const cacheMetrics = sessionCache.getCachePerformanceMetrics();

    console.group("🚀 Automatic Execution Performance Summary");

    // Execution metrics
    console.log(`📊 Total executions: ${metrics.totalExecutions}`);
    console.log(
      `✅ Success rate: ${(
        (metrics.successfulExecutions / metrics.totalExecutions) *
        100
      ).toFixed(1)}%`
    );
    console.log(
      `⏱️  Average time: ${(metrics.averageExecutionTime / 1000).toFixed(1)}s`
    );
    console.log(
      `🐌 Slow executions: ${metrics.slowExecutionsCount} (${(
        (metrics.slowExecutionsCount / metrics.totalExecutions) *
        100
      ).toFixed(1)}%)`
    );

    // Cache metrics
    console.log(
      `🎯 Cache hit rate: ${(metrics.cacheHitRate * 100).toFixed(1)}%`
    );
    console.log(`💾 Cache efficiency: ${cacheMetrics.cacheEfficiency}`);

    // Recent performance
    if (metrics.lastExecutionTime) {
      console.log(
        `🕐 Last execution: ${(metrics.lastExecutionTime / 1000).toFixed(1)}s`
      );
    }

    // Recommendations
    if (recommendations.length > 0) {
      console.group("💡 Performance Recommendations");
      recommendations.forEach((rec) => console.log(`• ${rec}`));
      console.groupEnd();
    }

    console.groupEnd();

    // Also log cache performance
    sessionCache.logCachePerformance();
  }, [getMetrics, getPerformanceRecommendations]);

  // Get execution history for analysis
  const getExecutionHistory = useCallback(() => {
    return [...executionHistory.current];
  }, []);

  // Clear performance history
  const clearHistory = useCallback(() => {
    executionHistory.current = [];
    console.log("🧹 Automatic execution performance history cleared");
  }, []);

  // Update performance thresholds
  const updateThresholds = useCallback(
    (newThresholds: Partial<typeof performanceThresholds.current>) => {
      performanceThresholds.current = {
        ...performanceThresholds.current,
        ...newThresholds,
      };
      console.log(
        "⚙️  Performance thresholds updated:",
        performanceThresholds.current
      );
    },
    []
  );

  // Periodic performance logging (every 10 executions)
  useEffect(() => {
    const history = executionHistory.current;
    if (history.length > 0 && history.length % 10 === 0) {
      console.log(
        `📈 Automatic execution milestone: ${history.length} executions completed`
      );

      // Log summary every 20 executions
      if (history.length % 20 === 0) {
        logPerformanceSummary();
      }
    }
  }, [logPerformanceSummary]);

  return {
    recordExecution,
    getMetrics,
    getPerformanceRecommendations,
    logPerformanceSummary,
    getExecutionHistory,
    clearHistory,
    updateThresholds,
  };
}

export default useAutomaticExecutionPerformance;
