/**
 * Performance monitoring utilities for layout components
 */

interface PerformanceMetrics {
  componentName: string;
  operation: string;
  duration: number;
  timestamp: number;
  metadata?: Record<string, any>;
}

interface PerformanceThresholds {
  render: number; // ms
  interaction: number; // ms
  dataProcessing: number; // ms
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private thresholds: PerformanceThresholds = {
    render: 16, // 60fps target
    interaction: 100, // Perceived as instant
    dataProcessing: 1000, // 1 second for data operations
  };
  private maxMetrics = 100; // Keep last 100 metrics

  /**
   * Start measuring performance for an operation
   */
  startMeasure(componentName: string, operation: string): () => void {
    const startTime = performance.now();

    return () => {
      const duration = performance.now() - startTime;
      this.recordMetric({
        componentName,
        operation,
        duration,
        timestamp: Date.now(),
      });
    };
  }

  /**
   * Measure a function execution time
   */
  measureFunction<T>(
    componentName: string,
    operation: string,
    fn: () => T,
    metadata?: Record<string, any>
  ): T {
    const startTime = performance.now();
    const result = fn();
    const duration = performance.now() - startTime;

    this.recordMetric({
      componentName,
      operation,
      duration,
      timestamp: Date.now(),
      metadata,
    });

    return result;
  }

  /**
   * Measure async function execution time
   */
  async measureAsync<T>(
    componentName: string,
    operation: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> {
    const startTime = performance.now();
    const result = await fn();
    const duration = performance.now() - startTime;

    this.recordMetric({
      componentName,
      operation,
      duration,
      timestamp: Date.now(),
      metadata,
    });

    return result;
  }

  /**
   * Record a performance metric
   */
  private recordMetric(metric: PerformanceMetrics): void {
    this.metrics.push(metric);

    // Keep only the last N metrics
    if (this.metrics.length > this.maxMetrics) {
      this.metrics = this.metrics.slice(-this.maxMetrics);
    }

    // Check if metric exceeds threshold
    this.checkThreshold(metric);
  }

  /**
   * Check if a metric exceeds performance thresholds
   */
  private checkThreshold(metric: PerformanceMetrics): void {
    let threshold: number;

    switch (metric.operation) {
      case "render":
      case "resize":
      case "animation":
        threshold = this.thresholds.render;
        break;
      case "click":
      case "hover":
      case "keyboard":
        threshold = this.thresholds.interaction;
        break;
      case "dataLoad":
      case "virtualScroll":
      case "sort":
      case "filter":
        threshold = this.thresholds.dataProcessing;
        break;
      default:
        threshold = this.thresholds.interaction;
    }

    if (metric.duration > threshold) {
      console.warn(
        `Performance warning: ${metric.componentName}.${
          metric.operation
        } took ${metric.duration.toFixed(2)}ms (threshold: ${threshold}ms)`,
        metric
      );

      // In production, report to monitoring service
      this.reportSlowOperation(metric, threshold);
    }
  }

  /**
   * Report slow operations to monitoring service
   */
  private reportSlowOperation(
    metric: PerformanceMetrics,
    threshold: number
  ): void {
    const report = {
      ...metric,
      threshold,
      severity: metric.duration > threshold * 2 ? "high" : "medium",
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    };

    // In production, send to monitoring service
    console.log("Slow operation report:", report);
  }

  /**
   * Get performance metrics for a component
   */
  getMetrics(componentName?: string): PerformanceMetrics[] {
    if (componentName) {
      return this.metrics.filter((m) => m.componentName === componentName);
    }
    return [...this.metrics];
  }

  /**
   * Get average performance for an operation
   */
  getAveragePerformance(componentName: string, operation: string): number {
    const relevantMetrics = this.metrics.filter(
      (m) => m.componentName === componentName && m.operation === operation
    );

    if (relevantMetrics.length === 0) return 0;

    const total = relevantMetrics.reduce((sum, m) => sum + m.duration, 0);
    return total / relevantMetrics.length;
  }

  /**
   * Clear all metrics
   */
  clearMetrics(): void {
    this.metrics = [];
  }

  /**
   * Update performance thresholds
   */
  updateThresholds(thresholds: Partial<PerformanceThresholds>): void {
    this.thresholds = { ...this.thresholds, ...thresholds };
  }
}

// Create singleton instance
export const performanceMonitor = new PerformanceMonitor();

/**
 * React hook for measuring component performance
 */
export function usePerformanceMonitor(componentName: string) {
  const measureRender = (operation: string = "render") => {
    return performanceMonitor.startMeasure(componentName, operation);
  };

  const measureFunction = <T>(
    operation: string,
    fn: () => T,
    metadata?: Record<string, any>
  ): T => {
    return performanceMonitor.measureFunction(
      componentName,
      operation,
      fn,
      metadata
    );
  };

  const measureAsync = <T>(
    operation: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> => {
    return performanceMonitor.measureAsync(
      componentName,
      operation,
      fn,
      metadata
    );
  };

  return {
    measureRender,
    measureFunction,
    measureAsync,
    getMetrics: () => performanceMonitor.getMetrics(componentName),
    getAveragePerformance: (operation: string) =>
      performanceMonitor.getAveragePerformance(componentName, operation),
  };
}

/**
 * Utility for detecting performance issues in large datasets
 */
export function detectDatasetPerformanceIssues(
  dataSize: number,
  operation: string
): { shouldOptimize: boolean; recommendations: string[] } {
  const recommendations: string[] = [];
  let shouldOptimize = false;

  // Large dataset thresholds
  const LARGE_DATASET = 1000;
  const VERY_LARGE_DATASET = 10000;
  const HUGE_DATASET = 100000;

  if (dataSize > LARGE_DATASET) {
    shouldOptimize = true;

    if (operation === "render" || operation === "scroll") {
      recommendations.push("Enable virtual scrolling for better performance");
    }

    if (operation === "sort" || operation === "filter") {
      recommendations.push("Consider server-side sorting/filtering");
    }

    if (dataSize > VERY_LARGE_DATASET) {
      recommendations.push("Implement pagination or lazy loading");

      if (dataSize > HUGE_DATASET) {
        recommendations.push("Consider data streaming or chunked loading");
        recommendations.push("Implement progressive rendering");
      }
    }
  }

  return { shouldOptimize, recommendations };
}

/**
 * Browser capability detection for graceful degradation
 */
export function detectBrowserCapabilities() {
  const capabilities = {
    cssGrid: CSS.supports("display", "grid"),
    cssFlexbox: CSS.supports("display", "flex"),
    cssTransforms: CSS.supports("transform", "translateX(0)"),
    cssTransitions: CSS.supports("transition", "all 0.3s"),
    resizeObserver: "ResizeObserver" in window,
    intersectionObserver: "IntersectionObserver" in window,
    requestAnimationFrame: "requestAnimationFrame" in window,
    touchEvents: "ontouchstart" in window,
    pointerEvents: "onpointerdown" in window,
    webGL: (() => {
      try {
        const canvas = document.createElement("canvas");
        return !!(
          canvas.getContext("webgl") || canvas.getContext("experimental-webgl")
        );
      } catch {
        return false;
      }
    })(),
  };

  return capabilities;
}

/**
 * Get fallback strategies based on browser capabilities
 */
export function getFallbackStrategies() {
  const capabilities = detectBrowserCapabilities();
  const strategies: Record<string, string> = {};

  if (!capabilities.cssGrid) {
    strategies.layout = "flexbox";
  }

  if (!capabilities.cssTransforms) {
    strategies.animations = "none";
  }

  if (!capabilities.resizeObserver) {
    strategies.resize = "window-resize-events";
  }

  if (!capabilities.intersectionObserver) {
    strategies.virtualScroll = "scroll-events";
  }

  if (!capabilities.touchEvents) {
    strategies.mobileInteraction = "mouse-only";
  }

  return strategies;
}
