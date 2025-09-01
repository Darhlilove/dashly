/**
 * Settings modal for managing user preferences and layout settings
 */

import React, { useState } from "react";
import { useUserPreferences } from "../hooks/useUserPreferences";

import { LayoutState } from "../types/layout";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLayoutState: LayoutState;
  onLayoutReset: () => void;
  onAllLayoutReset: () => void;
}

type SettingsTab = "layout" | "animations" | "accessibility" | "ui";

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentLayoutState,
  onLayoutReset,
  onAllLayoutReset,
}) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>("layout");

  const {
    preferences,
    effectiveAnimations,
    updateAnimations,
    updateAccessibility,
    updateUI,
    resetToDefaults,
    animationsEnabled,
    reducedMotionActive,
    effectiveTheme,
  } = useUserPreferences();

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const tabs = [
    { id: "layout" as const, label: "Layout", icon: "⚡" },
    { id: "animations" as const, label: "Animations", icon: "🎬" },
    { id: "accessibility" as const, label: "Accessibility", icon: "♿" },
    { id: "ui" as const, label: "Interface", icon: "🎨" },
  ];

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={handleOverlayClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close settings"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="flex">
          {/* Sidebar */}
          <div className="w-48 bg-gray-50 border-r border-gray-200">
            <nav className="p-4 space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
            {activeTab === "layout" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Layout Preferences
                  </h3>

                  <div className="space-y-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium text-gray-900 mb-2">
                        Current Layout
                      </h4>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>
                          Chat pane:{" "}
                          {currentLayoutState.chatPaneWidth.toFixed(1)}%
                        </div>
                        <div>
                          Dashboard pane:{" "}
                          {currentLayoutState.dashboardPaneWidth.toFixed(1)}%
                        </div>
                        <div>
                          Current view: {currentLayoutState.currentView}
                        </div>
                        <div>
                          Breakpoint: {currentLayoutState.currentBreakpoint}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <button
                        onClick={onLayoutReset}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                      >
                        Reset Current Breakpoint to Defaults
                      </button>

                      <button
                        onClick={onAllLayoutReset}
                        className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                      >
                        Reset All Layout Preferences
                      </button>
                    </div>

                    <div className="text-sm text-gray-500">
                      <p>
                        Layout preferences are automatically saved as you resize
                        panes and change views.
                      </p>
                      <p className="mt-1">
                        Different preferences are saved for each screen size
                        (mobile, tablet, desktop).
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "animations" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Animation Settings
                  </h3>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Enable Animations
                        </label>
                        <p className="text-sm text-gray-500">
                          Turn on/off all interface animations
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.animations.enableAnimations}
                        onChange={(e) =>
                          updateAnimations({
                            enableAnimations: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Respect System Reduced Motion
                        </label>
                        <p className="text-sm text-gray-500">
                          Automatically disable animations if system prefers
                          reduced motion
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.animations.respectReducedMotion}
                        onChange={(e) =>
                          updateAnimations({
                            respectReducedMotion: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    {preferences.animations.enableAnimations && (
                      <div className="space-y-4 pl-4 border-l-2 border-gray-200">
                        <div>
                          <label className="block text-sm font-medium text-gray-900 mb-1">
                            Sidebar Animation Duration:{" "}
                            {preferences.animations.sidebarAnimationDuration}ms
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="500"
                            step="50"
                            value={
                              preferences.animations.sidebarAnimationDuration
                            }
                            onChange={(e) =>
                              updateAnimations({
                                sidebarAnimationDuration: parseInt(
                                  e.target.value
                                ),
                              })
                            }
                            className="w-full"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-900 mb-1">
                            View Switch Duration:{" "}
                            {preferences.animations.viewSwitchAnimationDuration}
                            ms
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="500"
                            step="50"
                            value={
                              preferences.animations.viewSwitchAnimationDuration
                            }
                            onChange={(e) =>
                              updateAnimations({
                                viewSwitchAnimationDuration: parseInt(
                                  e.target.value
                                ),
                              })
                            }
                            className="w-full"
                          />
                        </div>
                      </div>
                    )}

                    <div className="bg-blue-50 p-4 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">
                        Current Status
                      </h4>
                      <div className="text-sm text-blue-800 space-y-1">
                        <div>
                          Animations enabled: {animationsEnabled ? "Yes" : "No"}
                        </div>
                        <div>
                          Reduced motion active:{" "}
                          {reducedMotionActive ? "Yes" : "No"}
                        </div>
                        <div>
                          Effective sidebar duration:{" "}
                          {effectiveAnimations.sidebarAnimationDuration}ms
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "accessibility" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Accessibility Settings
                  </h3>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Reduced Motion
                        </label>
                        <p className="text-sm text-gray-500">
                          Minimize animations and transitions
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.reducedMotion}
                        onChange={(e) =>
                          updateAccessibility({
                            reducedMotion: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Enhanced Keyboard Navigation
                        </label>
                        <p className="text-sm text-gray-500">
                          Improve keyboard accessibility features
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.keyboardNavigation}
                        onChange={(e) =>
                          updateAccessibility({
                            keyboardNavigation: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          High Contrast Mode
                        </label>
                        <p className="text-sm text-gray-500">
                          Increase contrast for better visibility
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.accessibility.highContrast}
                        onChange={(e) =>
                          updateAccessibility({
                            highContrast: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Screen Reader Optimizations
                        </label>
                        <p className="text-sm text-gray-500">
                          Enhanced support for screen readers
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={
                          preferences.accessibility.screenReaderOptimizations
                        }
                        onChange={(e) =>
                          updateAccessibility({
                            screenReaderOptimizations: e.target.checked,
                          })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "ui" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Interface Settings
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-2">
                        Theme
                      </label>
                      <select
                        value={preferences.ui.theme}
                        onChange={(e) =>
                          updateUI({
                            theme: e.target.value as
                              | "light"
                              | "dark"
                              | "system",
                          })
                        }
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="system">System Default</option>
                        <option value="light">Light</option>
                        <option value="dark">Dark</option>
                      </select>
                      <p className="text-sm text-gray-500 mt-1">
                        Current effective theme: {effectiveTheme}
                      </p>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Compact Mode
                        </label>
                        <p className="text-sm text-gray-500">
                          Reduce spacing and padding for more content
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.ui.compactMode}
                        onChange={(e) =>
                          updateUI({ compactMode: e.target.checked })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Show Tooltips
                        </label>
                        <p className="text-sm text-gray-500">
                          Display helpful tooltips on hover
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.ui.showTooltips}
                        onChange={(e) =>
                          updateUI({ showTooltips: e.target.checked })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-gray-900">
                          Auto-save Preferences
                        </label>
                        <p className="text-sm text-gray-500">
                          Automatically save changes as you make them
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={preferences.ui.autoSave}
                        onChange={(e) =>
                          updateUI({ autoSave: e.target.checked })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Reset All Button */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <button
                onClick={() => {
                  resetToDefaults();
                  onAllLayoutReset();
                }}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
              >
                Reset All Settings to Defaults
              </button>
              <p className="text-sm text-gray-500 mt-2 text-center">
                This will reset all preferences including layout, animations,
                and accessibility settings.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
