/**
 * Custom hook for managing layout preferences with localStorage persistence
 */

import { useCallback, useEffect, useRef } from "react";
import { LayoutState, Breakpoint } from "../types/layout";
import {
  loadLayoutPreferences,
  saveLayoutPreferences,
  resetLayoutPreferences,
  resetAllLayoutPreferences,
  migrateLayoutPreferences,
  createPreferencesFromLayoutState,
  getLayoutStateFromPreferences,
} from "../utils/layoutPreferences";

interface UseLayoutPreferencesOptions {
  /**
   * Debounce delay for saving preferences (in milliseconds)
   * Default: 500ms
   */
  saveDelay?: number;

  /**
   * Whether to automatically save preferences when layout state changes
   * Default: true
   */
  autoSave?: boolean;
}

interface UseLayoutPreferencesReturn {
  /**
   * Load preferences for the current breakpoint
   */
  loadPreferences: (breakpoint: Breakpoint) => Partial<LayoutState>;

  /**
   * Save current layout state as preferences
   */
  savePreferences: (layoutState: LayoutState) => void;

  /**
   * Reset preferences for current breakpoint to defaults
   */
  resetPreferences: (breakpoint: Breakpoint) => Partial<LayoutState>;

  /**
   * Reset all preferences to defaults
   */
  resetAllPreferences: () => void;

  /**
   * Manually trigger preference migration
   */
  migratePreferences: () => void;
}

export const useLayoutPreferences = (
  options: UseLayoutPreferencesOptions = {}
): UseLayoutPreferencesReturn => {
  // Options are available for future use
  // const { saveDelay = 500, autoSave = true } = options;

  // Debounce timer for saving preferences
  const saveTimeoutRef = useRef<number | null>(null);

  // Initialize preferences migration on first use
  useEffect(() => {
    migrateLayoutPreferences();
  }, []);

  /**
   * Load preferences for a specific breakpoint
   */
  const loadPreferences = useCallback(
    (breakpoint: Breakpoint): Partial<LayoutState> => {
      const preferences = loadLayoutPreferences(breakpoint);
      return getLayoutStateFromPreferences(preferences, breakpoint);
    },
    []
  );

  /**
   * Immediately save preferences without debouncing
   */
  const savePreferencesImmediate = useCallback((layoutState: LayoutState) => {
    // Clear any pending debounced save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }

    const preferences = createPreferencesFromLayoutState(layoutState);
    saveLayoutPreferences(preferences, layoutState.currentBreakpoint);
  }, []);

  /**
   * Reset preferences for a specific breakpoint
   */
  const resetPreferences = useCallback(
    (breakpoint: Breakpoint): Partial<LayoutState> => {
      const defaultPreferences = resetLayoutPreferences(breakpoint);
      return getLayoutStateFromPreferences(defaultPreferences, breakpoint);
    },
    []
  );

  /**
   * Reset all preferences
   */
  const resetAllPreferences = useCallback(() => {
    resetAllLayoutPreferences();
  }, []);

  /**
   * Manually trigger preference migration
   */
  const migratePreferences = useCallback(() => {
    migrateLayoutPreferences();
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  return {
    loadPreferences,
    savePreferences: savePreferencesImmediate, // Expose immediate save as main method
    resetPreferences,
    resetAllPreferences,
    migratePreferences,
  };
};
