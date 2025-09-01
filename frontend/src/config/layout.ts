import { LayoutConfig } from "../types/layout";

/**
 * Default layout configuration for responsive design
 */
export const LAYOUT_CONFIG: LayoutConfig = {
  breakpoints: {
    mobile: 768,
    tablet: 1024,
    desktop: 1200,
    largeDesktop: 1440,
  },

  defaultSizes: {
    desktop: {
      chat: 25, // 25% chat width as requested
      dashboard: 75, // 75% dashboard width
    },
    tablet: {
      chat: 30,
      dashboard: 70,
    },
    mobile: {
      chat: 100, // Full width when stacked
      dashboard: 100,
    },
  },

  animations: {
    sidebarDuration: 200, // milliseconds
    resizeDuration: 0, // immediate for smooth dragging
    viewSwitchDuration: 150,
  },

  constraints: {
    minChatWidth: 20, // minimum 20% width
    maxChatWidth: 60, // maximum 60% width
    sidebarTriggerWidth: 20, // 20px trigger zone
    sidebarHideDelay: 1000, // 1 second delay before hiding
  },
};

/**
 * CSS custom property names for dynamic layout sizing
 */
export const CSS_VARIABLES = {
  chatWidth: "--chat-pane-width",
  dashboardWidth: "--dashboard-pane-width",
  sidebarWidth: "--sidebar-width",
  sidebarTriggerWidth: "--sidebar-trigger-width",
  animationDuration: "--animation-duration",
  breakpointMobile: "--breakpoint-mobile",
  breakpointTablet: "--breakpoint-tablet",
  breakpointDesktop: "--breakpoint-desktop",
} as const;

/**
 * Media query strings for breakpoints
 */
export const MEDIA_QUERIES = {
  mobile: `(max-width: ${LAYOUT_CONFIG.breakpoints.mobile - 1}px)`,
  tablet: `(min-width: ${LAYOUT_CONFIG.breakpoints.mobile}px) and (max-width: ${
    LAYOUT_CONFIG.breakpoints.tablet - 1
  }px)`,
  desktop: `(min-width: ${
    LAYOUT_CONFIG.breakpoints.tablet
  }px) and (max-width: ${LAYOUT_CONFIG.breakpoints.desktop - 1}px)`,
  largeDesktop: `(min-width: ${LAYOUT_CONFIG.breakpoints.desktop}px)`,

  // Utility queries
  mobileAndUp: `(min-width: ${LAYOUT_CONFIG.breakpoints.mobile}px)`,
  tabletAndUp: `(min-width: ${LAYOUT_CONFIG.breakpoints.tablet}px)`,
  desktopAndUp: `(min-width: ${LAYOUT_CONFIG.breakpoints.desktop}px)`,
} as const;

/**
 * Z-index values for layered components
 */
export const Z_INDEX = {
  sidebar: 1000,
  sidebarOverlay: 999,
  resizeHandle: 100,
  modal: 2000,
  toast: 3000,
} as const;
