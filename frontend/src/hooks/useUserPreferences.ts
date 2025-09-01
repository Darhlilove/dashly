/**
 * Custom hook for managing user preferences with system integration
 */

import { useState, useEffect, useCallback } from "react";
import {
  UserPreferences,
  AnimationPreferences,
  AccessibilityPreferences,
  UIPreferences,
  loadUserPreferences,
  resetUserPreferences,
  updateAnimationPreferences,
  updateAccessibilityPreferences,
  updateUIPreferences,
  getEffectiveAnimationSettings,
  applyCSSAnimationProperties,
  createSystemPreferenceListeners,
  migrateUserPreferences,
  detectReducedMotionPreference,
  detectColorSchemePreference,
} from "../utils/userPreferences";

interface UseUserPreferencesReturn {
  /**
   * Current user preferences
   */
  preferences: UserPreferences;

  /**
   * Effective animation settings (considering reduced motion)
   */
  effectiveAnimations: AnimationPreferences;

  /**
   * Update animation preferences
   */
  updateAnimations: (updates: Partial<AnimationPreferences>) => void;

  /**
   * Update accessibility preferences
   */
  updateAccessibility: (updates: Partial<AccessibilityPreferences>) => void;

  /**
   * Update UI preferences
   */
  updateUI: (updates: Partial<UIPreferences>) => void;

  /**
   * Reset all preferences to defaults
   */
  resetToDefaults: () => void;

  /**
   * Whether animations should be enabled
   */
  animationsEnabled: boolean;

  /**
   * Whether reduced motion is active
   */
  reducedMotionActive: boolean;

  /**
   * Current effective theme
   */
  effectiveTheme: "light" | "dark";
}

export const useUserPreferences = (): UseUserPreferencesReturn => {
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    // Initialize and migrate preferences
    migrateUserPreferences();
    return loadUserPreferences();
  });

  const [systemReducedMotion, setSystemReducedMotion] = useState(() =>
    detectReducedMotionPreference()
  );

  const [systemColorScheme, setSystemColorScheme] = useState(() =>
    detectColorSchemePreference()
  );

  // Calculate effective animation settings
  const effectiveAnimations = getEffectiveAnimationSettings(preferences);
  const animationsEnabled = effectiveAnimations.enableAnimations;
  const reducedMotionActive =
    preferences.accessibility.reducedMotion ||
    (preferences.animations.respectReducedMotion && systemReducedMotion);

  // Calculate effective theme
  const effectiveTheme =
    preferences.ui.theme === "system"
      ? systemColorScheme
      : preferences.ui.theme;

  // Apply CSS properties when preferences change
  useEffect(() => {
    applyCSSAnimationProperties(preferences);
  }, [preferences]);

  // Listen for system preference changes
  useEffect(() => {
    const cleanup = createSystemPreferenceListeners(
      (reducedMotion) => {
        setSystemReducedMotion(reducedMotion);

        // Auto-update accessibility preferences if user wants to respect system settings
        if (preferences.animations.respectReducedMotion) {
          updateAccessibility({ reducedMotion });
        }
      },
      (colorScheme) => {
        setSystemColorScheme(colorScheme);
      }
    );

    return cleanup;
  }, [preferences.animations.respectReducedMotion]);

  // Update animation preferences
  const updateAnimations = useCallback(
    (updates: Partial<AnimationPreferences>) => {
      updateAnimationPreferences(updates);
      setPreferences(loadUserPreferences());
    },
    []
  );

  // Update accessibility preferences
  const updateAccessibility = useCallback(
    (updates: Partial<AccessibilityPreferences>) => {
      updateAccessibilityPreferences(updates);
      setPreferences(loadUserPreferences());
    },
    []
  );

  // Update UI preferences
  const updateUI = useCallback((updates: Partial<UIPreferences>) => {
    updateUIPreferences(updates);
    setPreferences(loadUserPreferences());
  }, []);

  // Reset all preferences
  const resetToDefaults = useCallback(() => {
    const defaultPrefs = resetUserPreferences();
    setPreferences(defaultPrefs);
  }, []);

  return {
    preferences,
    effectiveAnimations,
    updateAnimations,
    updateAccessibility,
    updateUI,
    resetToDefaults,
    animationsEnabled,
    reducedMotionActive,
    effectiveTheme,
  };
};
