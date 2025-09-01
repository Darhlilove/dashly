/**
 * User preference management for animations, accessibility, and UI settings
 */

export interface AnimationPreferences {
  enableAnimations: boolean;
  respectReducedMotion: boolean;
  sidebarAnimationDuration: number;
  resizeAnimationDuration: number;
  viewSwitchAnimationDuration: number;
}

export interface AccessibilityPreferences {
  highContrast: boolean;
  reducedMotion: boolean;
  keyboardNavigation: boolean;
  screenReaderOptimizations: boolean;
}

export interface UIPreferences {
  theme: "light" | "dark" | "system";
  compactMode: boolean;
  showTooltips: boolean;
  autoSave: boolean;
}

export interface UserPreferences {
  animations: AnimationPreferences;
  accessibility: AccessibilityPreferences;
  ui: UIPreferences;
  version: number;
}

const USER_PREFERENCES_KEY = "dashly_user_preferences";
const CURRENT_PREFERENCES_VERSION = 1;

/**
 * Default user preferences
 */
const getDefaultUserPreferences = (): UserPreferences => ({
  animations: {
    enableAnimations: true,
    respectReducedMotion: true,
    sidebarAnimationDuration: 200,
    resizeAnimationDuration: 0,
    viewSwitchAnimationDuration: 150,
  },
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    keyboardNavigation: true,
    screenReaderOptimizations: false,
  },
  ui: {
    theme: "system",
    compactMode: false,
    showTooltips: true,
    autoSave: true,
  },
  version: CURRENT_PREFERENCES_VERSION,
});

/**
 * Detect system preferences for reduced motion
 */
export const detectReducedMotionPreference = (): boolean => {
  if (typeof window === "undefined") return false;

  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

/**
 * Detect system color scheme preference
 */
export const detectColorSchemePreference = (): "light" | "dark" => {
  if (typeof window === "undefined") return "light";

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

/**
 * Validate user preferences
 */
const validateUserPreferences = (
  preferences: Partial<UserPreferences>
): UserPreferences => {
  const defaults = getDefaultUserPreferences();

  // Validate animations
  const animations: AnimationPreferences = {
    enableAnimations:
      preferences.animations?.enableAnimations ??
      defaults.animations.enableAnimations,
    respectReducedMotion:
      preferences.animations?.respectReducedMotion ??
      defaults.animations.respectReducedMotion,
    sidebarAnimationDuration: Math.max(
      0,
      Math.min(
        1000,
        preferences.animations?.sidebarAnimationDuration ??
          defaults.animations.sidebarAnimationDuration
      )
    ),
    resizeAnimationDuration: Math.max(
      0,
      Math.min(
        500,
        preferences.animations?.resizeAnimationDuration ??
          defaults.animations.resizeAnimationDuration
      )
    ),
    viewSwitchAnimationDuration: Math.max(
      0,
      Math.min(
        1000,
        preferences.animations?.viewSwitchAnimationDuration ??
          defaults.animations.viewSwitchAnimationDuration
      )
    ),
  };

  // Validate accessibility
  const accessibility: AccessibilityPreferences = {
    highContrast:
      preferences.accessibility?.highContrast ??
      defaults.accessibility.highContrast,
    reducedMotion:
      preferences.accessibility?.reducedMotion ??
      detectReducedMotionPreference(),
    keyboardNavigation:
      preferences.accessibility?.keyboardNavigation ??
      defaults.accessibility.keyboardNavigation,
    screenReaderOptimizations:
      preferences.accessibility?.screenReaderOptimizations ??
      defaults.accessibility.screenReaderOptimizations,
  };

  // Validate UI preferences
  const ui: UIPreferences = {
    theme: ["light", "dark", "system"].includes(preferences.ui?.theme || "")
      ? (preferences.ui!.theme as "light" | "dark" | "system")
      : defaults.ui.theme,
    compactMode: preferences.ui?.compactMode ?? defaults.ui.compactMode,
    showTooltips: preferences.ui?.showTooltips ?? defaults.ui.showTooltips,
    autoSave: preferences.ui?.autoSave ?? defaults.ui.autoSave,
  };

  return {
    animations,
    accessibility,
    ui,
    version: CURRENT_PREFERENCES_VERSION,
  };
};

/**
 * Load user preferences from localStorage
 */
export const loadUserPreferences = (): UserPreferences => {
  try {
    const stored = localStorage.getItem(USER_PREFERENCES_KEY);
    if (!stored) {
      return getDefaultUserPreferences();
    }

    const parsed = JSON.parse(stored) as Partial<UserPreferences>;
    return validateUserPreferences(parsed);
  } catch (error) {
    console.warn("Failed to load user preferences:", error);
    return getDefaultUserPreferences();
  }
};

/**
 * Save user preferences to localStorage
 */
export const saveUserPreferences = (
  preferences: Partial<UserPreferences>
): void => {
  try {
    const validated = validateUserPreferences(preferences);
    localStorage.setItem(USER_PREFERENCES_KEY, JSON.stringify(validated));
  } catch (error) {
    console.warn("Failed to save user preferences:", error);
  }
};

/**
 * Reset user preferences to defaults
 */
export const resetUserPreferences = (): UserPreferences => {
  try {
    localStorage.removeItem(USER_PREFERENCES_KEY);
    return getDefaultUserPreferences();
  } catch (error) {
    console.warn("Failed to reset user preferences:", error);
    return getDefaultUserPreferences();
  }
};

/**
 * Update specific preference category
 */
export const updateAnimationPreferences = (
  updates: Partial<AnimationPreferences>
): void => {
  const current = loadUserPreferences();
  const updated = {
    ...current,
    animations: { ...current.animations, ...updates },
  };
  saveUserPreferences(updated);
};

export const updateAccessibilityPreferences = (
  updates: Partial<AccessibilityPreferences>
): void => {
  const current = loadUserPreferences();
  const updated = {
    ...current,
    accessibility: { ...current.accessibility, ...updates },
  };
  saveUserPreferences(updated);
};

export const updateUIPreferences = (updates: Partial<UIPreferences>): void => {
  const current = loadUserPreferences();
  const updated = {
    ...current,
    ui: { ...current.ui, ...updates },
  };
  saveUserPreferences(updated);
};

/**
 * Get effective animation settings considering reduced motion preferences
 */
export const getEffectiveAnimationSettings = (
  preferences: UserPreferences
): AnimationPreferences => {
  const { animations, accessibility } = preferences;

  // If reduced motion is enabled (either by user or system), disable animations
  const shouldReduceMotion =
    accessibility.reducedMotion ||
    (animations.respectReducedMotion && detectReducedMotionPreference());

  if (shouldReduceMotion) {
    return {
      ...animations,
      enableAnimations: false,
      sidebarAnimationDuration: 0,
      resizeAnimationDuration: 0,
      viewSwitchAnimationDuration: 0,
    };
  }

  return animations;
};

/**
 * Apply CSS custom properties for animation durations
 */
export const applyCSSAnimationProperties = (
  preferences: UserPreferences
): void => {
  if (typeof document === "undefined") return;

  const effectiveAnimations = getEffectiveAnimationSettings(preferences);
  const root = document.documentElement;

  root.style.setProperty(
    "--sidebar-animation-duration",
    `${effectiveAnimations.sidebarAnimationDuration}ms`
  );
  root.style.setProperty(
    "--resize-animation-duration",
    `${effectiveAnimations.resizeAnimationDuration}ms`
  );
  root.style.setProperty(
    "--view-switch-animation-duration",
    `${effectiveAnimations.viewSwitchAnimationDuration}ms`
  );

  // Set a general animation state class
  if (effectiveAnimations.enableAnimations) {
    root.classList.add("animations-enabled");
    root.classList.remove("animations-disabled");
  } else {
    root.classList.add("animations-disabled");
    root.classList.remove("animations-enabled");
  }
};

/**
 * Listen for system preference changes
 */
export const createSystemPreferenceListeners = (
  onReducedMotionChange: (reducedMotion: boolean) => void,
  onColorSchemeChange: (scheme: "light" | "dark") => void
): (() => void) => {
  if (typeof window === "undefined") {
    return () => {}; // No-op for SSR
  }

  const reducedMotionQuery = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  );
  const colorSchemeQuery = window.matchMedia("(prefers-color-scheme: dark)");

  const handleReducedMotionChange = (e: MediaQueryListEvent) => {
    onReducedMotionChange(e.matches);
  };

  const handleColorSchemeChange = (e: MediaQueryListEvent) => {
    onColorSchemeChange(e.matches ? "dark" : "light");
  };

  // Add listeners
  reducedMotionQuery.addEventListener("change", handleReducedMotionChange);
  colorSchemeQuery.addEventListener("change", handleColorSchemeChange);

  // Return cleanup function
  return () => {
    reducedMotionQuery.removeEventListener("change", handleReducedMotionChange);
    colorSchemeQuery.removeEventListener("change", handleColorSchemeChange);
  };
};

/**
 * Migrate user preferences from older versions
 */
export const migrateUserPreferences = (): void => {
  try {
    const stored = localStorage.getItem(USER_PREFERENCES_KEY);
    if (!stored) return;

    const parsed = JSON.parse(stored);

    // Check version and migrate if necessary
    if (!parsed.version || parsed.version < CURRENT_PREFERENCES_VERSION) {
      console.log(
        "Migrating user preferences to version",
        CURRENT_PREFERENCES_VERSION
      );

      // For now, just validate and save - future versions can add specific migration logic
      const migrated = validateUserPreferences(parsed);
      saveUserPreferences(migrated);
    }
  } catch (error) {
    console.warn("Failed to migrate user preferences:", error);
    // If migration fails, reset to defaults
    resetUserPreferences();
  }
};
