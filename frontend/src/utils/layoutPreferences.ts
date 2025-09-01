/**
 * Layout preferences management with localStorage persistence
 */

import { LayoutState, ViewType, Breakpoint } from "../types/layout";
import { LAYOUT_CONFIG } from "../config/layout";

export interface LayoutPreferences {
  chatPaneWidth: number;
  dashboardPaneWidth: number;
  currentView: ViewType;
  sidebarVisible: boolean;
  lastBreakpoint: Breakpoint;
  version: number; // For preference migration
}

export interface BreakpointPreferences {
  [key: string]: Partial<LayoutPreferences>;
}

const STORAGE_KEY = "dashly_layout_preferences";
const CURRENT_VERSION = 2; // Incremented to force reset of old preferences with 35% chat width

/**
 * Default preferences based on layout configuration
 */
const getDefaultPreferences = (breakpoint: Breakpoint): LayoutPreferences => {
  const sizes =
    LAYOUT_CONFIG.defaultSizes[
      breakpoint === "large-desktop" ? "desktop" : breakpoint
    ] || LAYOUT_CONFIG.defaultSizes.desktop;

  return {
    chatPaneWidth: sizes.chat,
    dashboardPaneWidth: sizes.dashboard,
    currentView: "data" as ViewType,
    sidebarVisible: false,
    lastBreakpoint: breakpoint,
    version: CURRENT_VERSION,
  };
};

/**
 * Validate layout preferences to ensure they are within acceptable bounds
 */
const validatePreferences = (
  preferences: Partial<LayoutPreferences>,
  breakpoint: Breakpoint
): LayoutPreferences => {
  const defaults = getDefaultPreferences(breakpoint);
  const { constraints } = LAYOUT_CONFIG;

  // Validate chat pane width
  let chatWidth = preferences.chatPaneWidth ?? defaults.chatPaneWidth;
  chatWidth = Math.min(
    Math.max(chatWidth, constraints.minChatWidth),
    constraints.maxChatWidth
  );

  // Ensure widths add up to 100%
  const dashboardWidth = 100 - chatWidth;

  // Validate view type
  const currentView =
    preferences.currentView === "dashboard" ||
    preferences.currentView === "data"
      ? preferences.currentView
      : defaults.currentView;

  // Validate sidebar visibility
  const sidebarVisible =
    typeof preferences.sidebarVisible === "boolean"
      ? preferences.sidebarVisible
      : defaults.sidebarVisible;

  return {
    chatPaneWidth: chatWidth,
    dashboardPaneWidth: dashboardWidth,
    currentView,
    sidebarVisible,
    lastBreakpoint: breakpoint,
    version: CURRENT_VERSION,
  };
};

/**
 * Load layout preferences from localStorage
 */
export const loadLayoutPreferences = (
  currentBreakpoint: Breakpoint
): LayoutPreferences => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return getDefaultPreferences(currentBreakpoint);
    }

    const parsed = JSON.parse(stored) as BreakpointPreferences;

    // Get preferences for current breakpoint
    const breakpointPrefs = parsed[currentBreakpoint];
    if (!breakpointPrefs) {
      return getDefaultPreferences(currentBreakpoint);
    }

    // Validate and return preferences
    return validatePreferences(breakpointPrefs, currentBreakpoint);
  } catch (error) {
    console.warn("Failed to load layout preferences:", error);
    return getDefaultPreferences(currentBreakpoint);
  }
};

/**
 * Save layout preferences to localStorage
 */
export const saveLayoutPreferences = (
  preferences: Partial<LayoutPreferences>,
  breakpoint: Breakpoint
): void => {
  try {
    // Load existing preferences
    const stored = localStorage.getItem(STORAGE_KEY);
    const existing: BreakpointPreferences = stored ? JSON.parse(stored) : {};

    // Validate the new preferences
    const validated = validatePreferences(preferences, breakpoint);

    // Update preferences for the current breakpoint
    existing[breakpoint] = validated;

    // Save back to localStorage
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
  } catch (error) {
    console.warn("Failed to save layout preferences:", error);
  }
};

/**
 * Reset layout preferences to defaults for a specific breakpoint
 */
export const resetLayoutPreferences = (
  breakpoint: Breakpoint
): LayoutPreferences => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const existing: BreakpointPreferences = stored ? JSON.parse(stored) : {};

    // Remove preferences for this breakpoint
    delete existing[breakpoint];

    // Save updated preferences
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));

    return getDefaultPreferences(breakpoint);
  } catch (error) {
    console.warn("Failed to reset layout preferences:", error);
    return getDefaultPreferences(breakpoint);
  }
};

/**
 * Reset all layout preferences to defaults
 */
export const resetAllLayoutPreferences = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
    console.log("All layout preferences have been reset to defaults");
  } catch (error) {
    console.warn("Failed to reset all layout preferences:", error);
  }
};

// Make reset function available globally for debugging
if (typeof window !== "undefined") {
  (window as any).resetDashlyLayoutPreferences = () => {
    resetAllLayoutPreferences();
    console.log(
      "Layout preferences reset! Please refresh the page to see changes."
    );
  };
}

/**
 * Check if layout preferences exist for a breakpoint
 */
export const hasLayoutPreferences = (breakpoint: Breakpoint): boolean => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return false;

    const parsed = JSON.parse(stored) as BreakpointPreferences;
    return Boolean(parsed[breakpoint]);
  } catch (error) {
    return false;
  }
};

/**
 * Migrate preferences from older versions
 */
export const migrateLayoutPreferences = (): void => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return;

    const parsed = JSON.parse(stored);

    // Check if this is an old format (direct LayoutPreferences instead of BreakpointPreferences)
    if (
      parsed.version !== undefined &&
      typeof parsed.chatPaneWidth === "number"
    ) {
      // This is old format - migrate to new breakpoint-based format
      const oldPrefs = parsed as LayoutPreferences;
      const newFormat: BreakpointPreferences = {
        desktop: oldPrefs,
        tablet: { ...oldPrefs },
        mobile: { ...oldPrefs },
      };

      localStorage.setItem(STORAGE_KEY, JSON.stringify(newFormat));
      console.log("Migrated layout preferences to new format");
      return;
    }

    // Check if we need to migrate to new version (reset preferences with old chat width)
    if (parsed && typeof parsed === "object") {
      let needsReset = false;

      // Check each breakpoint for old version or old chat width values
      Object.keys(parsed).forEach((breakpoint) => {
        const prefs = parsed[breakpoint];
        if (
          prefs &&
          (prefs.version < CURRENT_VERSION ||
            prefs.chatPaneWidth === 35 || // Old default was 35%
            prefs.chatPaneWidth === 16.67) // Even older default was 16.67%
        ) {
          needsReset = true;
        }
      });

      if (needsReset) {
        console.log(
          "Resetting layout preferences due to version upgrade (chat width changed from 35% to 25%)"
        );
        resetAllLayoutPreferences();
      }
    }
  } catch (error) {
    console.warn("Failed to migrate layout preferences:", error);
    // If migration fails, just clear the preferences
    resetAllLayoutPreferences();
  }
};

/**
 * Get layout state from preferences
 */
export const getLayoutStateFromPreferences = (
  preferences: LayoutPreferences,
  currentBreakpoint: Breakpoint
): Partial<LayoutState> => {
  return {
    chatPaneWidth: preferences.chatPaneWidth,
    dashboardPaneWidth: preferences.dashboardPaneWidth,
    currentView: preferences.currentView,
    sidebarVisible: preferences.sidebarVisible,
    currentBreakpoint,
    isResizing: false,
  };
};

/**
 * Create preferences from layout state
 */
export const createPreferencesFromLayoutState = (
  layoutState: LayoutState
): LayoutPreferences => {
  return {
    chatPaneWidth: layoutState.chatPaneWidth,
    dashboardPaneWidth: layoutState.dashboardPaneWidth,
    currentView: layoutState.currentView,
    sidebarVisible: layoutState.sidebarVisible,
    lastBreakpoint: layoutState.currentBreakpoint,
    version: CURRENT_VERSION,
  };
};
