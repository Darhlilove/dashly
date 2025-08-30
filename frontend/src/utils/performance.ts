/**
 * Performance monitoring utilities for development
 */

interface PerformanceMetric {
  name: string;
  duration: number;
  timestamp: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private timers: Map<string, number> = new Map();

  startTimer(name: string): void {
    this.timers.set(name, performance.now());
  }

  endTimer(name: string): number {
    const startTime = this.timers.get(name);
    if (!startTime) {
      console.warn(`Timer "${name}" was not started`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.timers.delete(name);

    const metric: PerformanceMetric = {
      name,
      duration,
      timestamp: Date.now(),
    };

    this.metrics.push(metric);

    // Keep only last 100 metrics to prevent memory leaks
    if (this.metrics.length > 100) {
      this.metrics = this.metrics.slice(-100);
    }

    // Log slow operations in development
    if (process.env.NODE_ENV === "development" && duration > 100) {
      console.warn(
        `Slow operation detected: ${name} took ${duration.toFixed(2)}ms`
      );
    }

    return duration;
  }

  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  getAverageTime(name: string): number {
    const relevantMetrics = this.metrics.filter((m) => m.name === name);
    if (relevantMetrics.length === 0) return 0;

    const total = relevantMetrics.reduce((sum, m) => sum + m.duration, 0);
    return total / relevantMetrics.length;
  }

  clearMetrics(): void {
    this.metrics = [];
    this.timers.clear();
  }

  logSummary(): void {
    if (process.env.NODE_ENV !== "development") return;

    const uniqueNames = [...new Set(this.metrics.map((m) => m.name))];

    console.group("Performance Summary");
    uniqueNames.forEach((name) => {
      const avg = this.getAverageTime(name);
      const count = this.metrics.filter((m) => m.name === name).length;
      console.log(`${name}: ${avg.toFixed(2)}ms avg (${count} calls)`);
    });
    console.groupEnd();
  }
}

// Global performance monitor instance
export const performanceMonitor = new PerformanceMonitor();

// Performance measurement decorator for async functions
export function measurePerformance<T extends (...args: any[]) => Promise<any>>(
  name: string,
  fn: T
): T {
  return (async (...args: Parameters<T>) => {
    performanceMonitor.startTimer(name);
    try {
      const result = await fn(...args);
      return result;
    } finally {
      performanceMonitor.endTimer(name);
    }
  }) as T;
}

// Performance measurement hook for React components
export function useMeasureRender(componentName: string) {
  if (process.env.NODE_ENV === "development") {
    performanceMonitor.startTimer(`${componentName}_render`);

    // Use useEffect to measure render completion
    import("react").then(({ useEffect }) => {
      useEffect(() => {
        performanceMonitor.endTimer(`${componentName}_render`);
      });
    });
  }
}

// Bundle size analysis helper
export function analyzeBundleSize() {
  if (process.env.NODE_ENV !== "development") return;

  // Estimate bundle size based on loaded modules
  const scripts = Array.from(document.querySelectorAll("script[src]"));
  let totalSize = 0;

  scripts.forEach((script) => {
    const src = (script as HTMLScriptElement).src;
    if (src.includes("assets")) {
      // Rough estimation - in real app you'd use webpack-bundle-analyzer
      console.log(`Script: ${src.split("/").pop()}`);
    }
  });

  console.log("Use webpack-bundle-analyzer for detailed bundle analysis");
}

// Memory usage monitoring
export function logMemoryUsage() {
  if (process.env.NODE_ENV !== "development") return;

  if ("memory" in performance) {
    const memory = (performance as any).memory;
    console.log("Memory Usage:", {
      used: `${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
      total: `${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
      limit: `${(memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB`,
    });
  }
}
