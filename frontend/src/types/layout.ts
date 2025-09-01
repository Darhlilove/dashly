/**
 * Layout configuration types for responsive design
 */

export type Breakpoint = "mobile" | "tablet" | "desktop" | "large-desktop";

export type ViewType = "dashboard" | "data";

export interface BreakpointConfig {
  mobile: number;
  tablet: number;
  desktop: number;
  largeDesktop: number;
}

export interface PaneSizes {
  chat: number;
  dashboard: number;
}

export interface LayoutSizes {
  desktop: PaneSizes;
  tablet: PaneSizes;
  mobile: PaneSizes;
}

export interface AnimationConfig {
  sidebarDuration: number;
  resizeDuration: number;
  viewSwitchDuration: number;
}

export interface LayoutConfig {
  breakpoints: BreakpointConfig;
  defaultSizes: LayoutSizes;
  animations: AnimationConfig;
  constraints: {
    minChatWidth: number;
    maxChatWidth: number;
    sidebarTriggerWidth: number;
    sidebarHideDelay: number;
  };
}

export interface LayoutState {
  sidebarVisible: boolean;
  chatPaneWidth: number;
  dashboardPaneWidth: number;
  currentView: ViewType;
  currentBreakpoint: Breakpoint;
  isResizing: boolean;
}

export interface ResizeConstraints {
  minWidth: number;
  maxWidth: number;
  snapThreshold: number;
}

export interface SidebarConfig {
  triggerWidth: number;
  hideDelay: number;
  showDelay: number;
  animationDuration: number;
}
