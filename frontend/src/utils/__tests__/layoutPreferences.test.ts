/**
 * Tests for layout preferences functionality
 */

import {
  loadLayoutPreferences,
  saveLayoutPreferences,
  resetLayoutPreferences,
  resetAllLayoutPreferences,
  hasLayoutPreferences,
  migrateLayoutPreferences,
} from "../layoutPreferences";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

describe("Layout Preferences", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  describe("loadLayoutPreferences", () => {
    it("should return default preferences when no stored preferences exist", () => {
      const preferences = loadLayoutPreferences("desktop");

      expect(preferences.chatPaneWidth).toBe(16.67);
      expect(preferences.dashboardPaneWidth).toBe(83.33);
      expect(preferences.currentView).toBe("data");
      expect(preferences.sidebarVisible).toBe(false);
      expect(preferences.version).toBe(1);
    });

    it("should load stored preferences for a breakpoint", () => {
      const testPreferences = {
        desktop: {
          chatPaneWidth: 25,
          dashboardPaneWidth: 75,
          currentView: "dashboard" as const,
          sidebarVisible: true,
          lastBreakpoint: "desktop" as const,
          version: 1,
        },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(testPreferences)
      );

      const preferences = loadLayoutPreferences("desktop");
      expect(preferences.chatPaneWidth).toBe(25);
      expect(preferences.dashboardPaneWidth).toBe(75);
      expect(preferences.currentView).toBe("dashboard");
      expect(preferences.sidebarVisible).toBe(true);
    });

    it("should validate and constrain invalid preferences", () => {
      const invalidPreferences = {
        desktop: {
          chatPaneWidth: 80, // Too large
          dashboardPaneWidth: 20,
          currentView: "invalid" as any,
          sidebarVisible: "not-boolean" as any,
          version: 1,
        },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(invalidPreferences)
      );

      const preferences = loadLayoutPreferences("desktop");
      expect(preferences.chatPaneWidth).toBe(50); // Constrained to max
      expect(preferences.dashboardPaneWidth).toBe(50); // Calculated from constrained chat width
      expect(preferences.currentView).toBe("data"); // Reset to default
      expect(preferences.sidebarVisible).toBe(false); // Reset to default
    });
  });

  describe("saveLayoutPreferences", () => {
    it("should save preferences for a specific breakpoint", () => {
      const preferences = {
        chatPaneWidth: 30,
        dashboardPaneWidth: 70,
        currentView: "dashboard" as const,
        sidebarVisible: true,
        lastBreakpoint: "desktop" as const,
        version: 1,
      };

      saveLayoutPreferences(preferences, "desktop");

      const stored = JSON.parse(
        localStorageMock.getItem("dashly_layout_preferences") || "{}"
      );
      expect(stored.desktop).toEqual(preferences);
    });

    it("should preserve existing preferences for other breakpoints", () => {
      // Set up existing preferences
      const existingPreferences = {
        mobile: {
          chatPaneWidth: 100,
          dashboardPaneWidth: 0,
          currentView: "data" as const,
          sidebarVisible: false,
          version: 1,
        },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(existingPreferences)
      );

      // Save new desktop preferences
      const desktopPreferences = {
        chatPaneWidth: 25,
        dashboardPaneWidth: 75,
        currentView: "dashboard" as const,
        sidebarVisible: true,
        lastBreakpoint: "desktop" as const,
        version: 1,
      };

      saveLayoutPreferences(desktopPreferences, "desktop");

      const stored = JSON.parse(
        localStorageMock.getItem("dashly_layout_preferences") || "{}"
      );
      expect(stored.mobile).toEqual(existingPreferences.mobile);
      expect(stored.desktop).toEqual(desktopPreferences);
    });
  });

  describe("resetLayoutPreferences", () => {
    it("should reset preferences for a specific breakpoint", () => {
      // Set up existing preferences
      const existingPreferences = {
        desktop: {
          chatPaneWidth: 30,
          dashboardPaneWidth: 70,
          currentView: "dashboard" as const,
          sidebarVisible: true,
          version: 1,
        },
        mobile: {
          chatPaneWidth: 100,
          dashboardPaneWidth: 0,
          currentView: "data" as const,
          sidebarVisible: false,
          version: 1,
        },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(existingPreferences)
      );

      const resetPrefs = resetLayoutPreferences("desktop");

      // Should return default preferences
      expect(resetPrefs.chatPaneWidth).toBe(16.67);
      expect(resetPrefs.dashboardPaneWidth).toBe(83.33);

      // Should preserve mobile preferences
      const stored = JSON.parse(
        localStorageMock.getItem("dashly_layout_preferences") || "{}"
      );
      expect(stored.mobile).toEqual(existingPreferences.mobile);
      expect(stored.desktop).toBeUndefined();
    });
  });

  describe("resetAllLayoutPreferences", () => {
    it("should remove all layout preferences", () => {
      const existingPreferences = {
        desktop: { chatPaneWidth: 30, version: 1 },
        mobile: { chatPaneWidth: 100, version: 1 },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(existingPreferences)
      );

      resetAllLayoutPreferences();

      expect(localStorageMock.getItem("dashly_layout_preferences")).toBeNull();
    });
  });

  describe("hasLayoutPreferences", () => {
    it("should return false when no preferences exist", () => {
      expect(hasLayoutPreferences("desktop")).toBe(false);
    });

    it("should return true when preferences exist for the breakpoint", () => {
      const preferences = {
        desktop: { chatPaneWidth: 30, version: 1 },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(preferences)
      );

      expect(hasLayoutPreferences("desktop")).toBe(true);
      expect(hasLayoutPreferences("mobile")).toBe(false);
    });
  });

  describe("migrateLayoutPreferences", () => {
    it("should migrate old format preferences to new format", () => {
      // Old format - direct LayoutPreferences object
      const oldFormat = {
        chatPaneWidth: 25,
        dashboardPaneWidth: 75,
        currentView: "dashboard",
        sidebarVisible: true,
        version: 1,
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(oldFormat)
      );

      migrateLayoutPreferences();

      const stored = JSON.parse(
        localStorageMock.getItem("dashly_layout_preferences") || "{}"
      );
      expect(stored.desktop).toEqual(oldFormat);
      expect(stored.tablet).toEqual(oldFormat);
      expect(stored.mobile).toEqual(oldFormat);
    });

    it("should not migrate already correct format", () => {
      const correctFormat = {
        desktop: {
          chatPaneWidth: 25,
          dashboardPaneWidth: 75,
          version: 1,
        },
      };

      localStorageMock.setItem(
        "dashly_layout_preferences",
        JSON.stringify(correctFormat)
      );

      migrateLayoutPreferences();

      const stored = JSON.parse(
        localStorageMock.getItem("dashly_layout_preferences") || "{}"
      );
      expect(stored).toEqual(correctFormat);
    });
  });
});
