/**
 * Graceful degradation utilities for handling edge cases and unsupported features
 */

interface ViewportInfo {
  width: number;
  height: number;
  aspectRatio: number;
  isPortrait: boolean;
  isLandscape: boolean;
}

interface DegradationStrategy {
  component: string;
  reason: string;
  fallback: string;
  recommendations?: string[];
}

/**
 * Detect viewport constraints and recommend degradation strategies
 */
export function analyzeViewportConstraints(): {
  viewport: ViewportInfo;
  constraints: string[];
  strategies: DegradationStrategy[];
} {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const aspectRatio = width / height;

  const viewport: ViewportInfo = {
    width,
    height,
    aspectRatio,
    isPortrait: height > width,
    isLandscape: width > height,
  };

  const constraints: string[] = [];
  const strategies: DegradationStrategy[] = [];

  // Extremely small screens (< 320px width)
  if (width < 320) {
    constraints.push("extremely-narrow");
    strategies.push({
      component: "ResizableLayout",
      reason: "Screen too narrow for split layout",
      fallback: "single-column-stack",
      recommendations: [
        "Stack chat and dashboard vertically",
        "Hide sidebar by default",
        "Use full-width components",
      ],
    });
  }

  // Very small screens (< 480px width)
  if (width < 480) {
    constraints.push("very-narrow");
    strategies.push({
      component: "DataTableView",
      reason: "Insufficient width for table columns",
      fallback: "card-layout",
      recommendations: [
        "Display data as cards instead of table",
        "Show only essential columns",
        "Enable horizontal scrolling",
      ],
    });
  }

  // Short screens (< 400px height)
  if (height < 400) {
    constraints.push("very-short");
    strategies.push({
      component: "AutoHideSidebar",
      reason: "Insufficient height for sidebar content",
      fallback: "bottom-sheet",
      recommendations: [
        "Use bottom sheet instead of sidebar",
        "Minimize vertical spacing",
        "Collapse non-essential UI elements",
      ],
    });
  }

  // Extreme aspect ratios
  if (aspectRatio > 3 || aspectRatio < 0.33) {
    constraints.push("extreme-aspect-ratio");
    strategies.push({
      component: "ViewToggle",
      reason: "Extreme aspect ratio affects layout",
      fallback: "adaptive-layout",
      recommendations: [
        "Adjust component proportions",
        "Use different layout orientation",
        "Consider rotating device prompt",
      ],
    });
  }

  return { viewport, constraints, strategies };
}

/**
 * Check for browser feature support and provide fallbacks
 */
export function checkFeatureSupport(): {
  supported: Record<string, boolean>;
  fallbacks: Record<string, string>;
} {
  // Safe CSS.supports check with fallback for test environments
  const cssSupports = (property: string, value: string): boolean => {
    try {
      return (
        typeof CSS !== "undefined" &&
        CSS.supports &&
        CSS.supports(property, value)
      );
    } catch {
      return true; // Assume support in test environments
    }
  };

  const supported = {
    cssGrid: cssSupports("display", "grid"),
    cssFlexbox: cssSupports("display", "flex"),
    cssTransforms: cssSupports("transform", "translateX(0)"),
    cssTransitions: cssSupports("transition", "all 0.3s"),
    cssCustomProperties: cssSupports("color", "var(--test)"),
    resizeObserver: "ResizeObserver" in window,
    intersectionObserver: "IntersectionObserver" in window,
    requestAnimationFrame: "requestAnimationFrame" in window,
    touchEvents: "ontouchstart" in window,
    pointerEvents: "onpointerdown" in window,
    localStorage: (() => {
      try {
        localStorage.setItem("test", "test");
        localStorage.removeItem("test");
        return true;
      } catch {
        return false;
      }
    })(),
  };

  const fallbacks: Record<string, string> = {};

  if (!supported.cssGrid) {
    fallbacks.layout = "Use flexbox-based layout instead of CSS Grid";
  }

  if (!supported.cssTransforms) {
    fallbacks.animations = "Disable transform-based animations";
  }

  if (!supported.cssTransitions) {
    fallbacks.transitions = "Use instant state changes instead of transitions";
  }

  if (!supported.resizeObserver) {
    fallbacks.resize = "Use window resize events with throttling";
  }

  if (!supported.intersectionObserver) {
    fallbacks.virtualScroll = "Use scroll events for virtual scrolling";
  }

  if (!supported.localStorage) {
    fallbacks.persistence = "Use in-memory storage only";
  }

  return { supported, fallbacks };
}

/**
 * Detect performance constraints and suggest optimizations
 */
export function analyzePerformanceConstraints(): {
  deviceType: "high-end" | "mid-range" | "low-end";
  constraints: string[];
  optimizations: string[];
} {
  const hardwareConcurrency = navigator.hardwareConcurrency || 1;
  const memory = (navigator as any).deviceMemory || 1;
  const connection = (navigator as any).connection;

  let deviceType: "high-end" | "mid-range" | "low-end" = "mid-range";
  const constraints: string[] = [];
  const optimizations: string[] = [];

  // Determine device type based on available metrics
  if (hardwareConcurrency >= 8 && memory >= 4) {
    deviceType = "high-end";
  } else if (hardwareConcurrency >= 4 && memory >= 2) {
    deviceType = "mid-range";
  } else {
    deviceType = "low-end";
    constraints.push("limited-cpu");
    constraints.push("limited-memory");
  }

  // Network constraints
  if (connection) {
    if (
      connection.effectiveType === "slow-2g" ||
      connection.effectiveType === "2g"
    ) {
      constraints.push("slow-network");
      optimizations.push("Reduce data transfer");
      optimizations.push("Implement aggressive caching");
    }

    if (connection.saveData) {
      constraints.push("data-saver-mode");
      optimizations.push("Minimize resource usage");
      optimizations.push("Disable non-essential animations");
    }
  }

  // Low-end device optimizations
  if (deviceType === "low-end") {
    optimizations.push("Reduce virtual scrolling buffer size");
    optimizations.push("Disable complex animations");
    optimizations.push("Implement lazy loading for heavy components");
    optimizations.push("Use simpler layout algorithms");
  }

  return { deviceType, constraints, optimizations };
}

/**
 * Generate adaptive configuration based on constraints
 */
export function generateAdaptiveConfig(): {
  layout: {
    enableResize: boolean;
    enableAnimations: boolean;
    sidebarMode: "auto-hide" | "always-visible" | "overlay";
    tableMode: "virtual" | "paginated" | "simple";
  };
  performance: {
    virtualScrollBuffer: number;
    animationDuration: number;
    debounceDelay: number;
  };
  features: {
    enableSearch: boolean;
    enableSort: boolean;
    enableExport: boolean;
    enableColumnResize: boolean;
  };
} {
  const { viewport, constraints } = analyzeViewportConstraints();
  const { supported } = checkFeatureSupport();
  const { deviceType } = analyzePerformanceConstraints();

  const config = {
    layout: {
      enableResize: viewport.width >= 768 && supported.resizeObserver,
      enableAnimations: supported.cssTransitions && deviceType !== "low-end",
      sidebarMode:
        viewport.width < 768 ? ("overlay" as const) : ("auto-hide" as const),
      tableMode:
        deviceType === "low-end" ? ("simple" as const) : ("virtual" as const),
    },
    performance: {
      virtualScrollBuffer:
        deviceType === "low-end" ? 5 : deviceType === "mid-range" ? 10 : 20,
      animationDuration: deviceType === "low-end" ? 0 : 200,
      debounceDelay: deviceType === "low-end" ? 300 : 150,
    },
    features: {
      enableSearch: true,
      enableSort: deviceType !== "low-end",
      enableExport: true,
      enableColumnResize: viewport.width >= 1024 && supported.resizeObserver,
    },
  };

  // Apply constraint-specific overrides
  if (constraints.includes("extremely-narrow")) {
    config.layout.enableResize = false;
    config.layout.sidebarMode = "overlay";
    config.features.enableColumnResize = false;
  }

  if (constraints.includes("very-short")) {
    config.layout.sidebarMode = "overlay";
    config.performance.virtualScrollBuffer = Math.min(
      config.performance.virtualScrollBuffer,
      5
    );
  }

  if (constraints.includes("slow-network")) {
    config.layout.enableAnimations = false;
    config.performance.animationDuration = 0;
  }

  return config;
}

/**
 * Create fallback component props based on constraints
 */
export function createFallbackProps(
  componentName: string
): Record<string, any> {
  const config = generateAdaptiveConfig();
  const { viewport } = analyzeViewportConstraints();

  switch (componentName) {
    case "ResizableLayout":
      return {
        enableResize: config.layout.enableResize,
        animationDuration: config.performance.animationDuration,
        minChatWidth: viewport.width < 480 ? 100 : 200,
        maxChatWidth: viewport.width < 768 ? 80 : 50,
      };

    case "AutoHideSidebar":
      return {
        mode: config.layout.sidebarMode,
        enableAnimations: config.layout.enableAnimations,
        hideDelay: config.performance.debounceDelay * 3,
        triggerWidth: viewport.width < 480 ? 30 : 20,
      };

    case "DataTableView":
      return {
        virtualScrolling: config.layout.tableMode === "virtual",
        enableSearch: config.features.enableSearch,
        enableSort: config.features.enableSort,
        enableExport: config.features.enableExport,
        enableColumnResize: config.features.enableColumnResize,
        maxRows: config.layout.tableMode === "simple" ? 50 : 100,
        bufferSize: config.performance.virtualScrollBuffer,
      };

    case "ViewToggle":
      return {
        animationDuration: config.performance.animationDuration,
        enableKeyboardNavigation: true,
        compactMode: viewport.width < 480,
      };

    default:
      return {};
  }
}

/**
 * Monitor and report degradation events
 */
export function reportDegradationEvent(
  component: string,
  strategy: DegradationStrategy,
  metadata?: Record<string, any>
): void {
  const event = {
    component,
    strategy,
    timestamp: Date.now(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    userAgent: navigator.userAgent,
    metadata,
  };

  console.log("Graceful degradation applied:", event);

  // In production, send to analytics service
  // analytics.track('graceful_degradation', event);
}
