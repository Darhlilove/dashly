import { CSS_VARIABLES } from "../config/layout";

/**
 * Utility functions for managing CSS custom properties
 */

/**
 * Set a CSS custom property value
 */
export const setCSSVariable = (
  property: string,
  value: string | number
): void => {
  const stringValue = typeof value === "number" ? `${value}` : value;
  document.documentElement.style.setProperty(property, stringValue);
};

/**
 * Get a CSS custom property value
 */
export const getCSSVariable = (property: string): string => {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(property)
    .trim();
};

/**
 * Set layout pane widths using CSS custom properties
 */
export const setLayoutWidths = (
  chatWidth: number,
  dashboardWidth: number
): void => {
  setCSSVariable(CSS_VARIABLES.chatWidth, `${chatWidth}%`);
  setCSSVariable(CSS_VARIABLES.dashboardWidth, `${dashboardWidth}%`);
};

/**
 * Get current layout widths from CSS custom properties
 */
export const getLayoutWidths = (): { chat: number; dashboard: number } => {
  const chatWidth =
    parseFloat(getCSSVariable(CSS_VARIABLES.chatWidth)) || 16.67;
  const dashboardWidth =
    parseFloat(getCSSVariable(CSS_VARIABLES.dashboardWidth)) || 83.33;

  return { chat: chatWidth, dashboard: dashboardWidth };
};

/**
 * Set animation duration for layout transitions
 */
export const setAnimationDuration = (duration: number): void => {
  setCSSVariable(CSS_VARIABLES.animationDuration, `${duration}ms`);
};

/**
 * Reset layout to default values
 */
export const resetLayoutToDefaults = (): void => {
  setCSSVariable(CSS_VARIABLES.chatWidth, "16.67%");
  setCSSVariable(CSS_VARIABLES.dashboardWidth, "83.33%");
  setCSSVariable(CSS_VARIABLES.animationDuration, "200ms");
};
