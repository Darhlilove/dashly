import { useEffect, useCallback } from "react";

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
  preventDefault?: boolean;
}

export interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[];
  enabled?: boolean;
  target?: HTMLElement | Document;
}

/**
 * Hook for managing keyboard shortcuts with accessibility support
 */
export const useKeyboardShortcuts = ({
  shortcuts,
  enabled = true,
  target = document,
}: UseKeyboardShortcutsOptions) => {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts when user is typing in input fields
      const activeElement = document.activeElement;
      const isInputField =
        activeElement &&
        (activeElement.tagName === "INPUT" ||
          activeElement.tagName === "TEXTAREA" ||
          activeElement.getAttribute("contenteditable") === "true");

      // Allow shortcuts in input fields only if they use modifier keys
      const hasModifier = event.ctrlKey || event.metaKey || event.altKey;
      if (isInputField && !hasModifier) return;

      for (const shortcut of shortcuts) {
        const keyMatches =
          event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatches = !!shortcut.ctrlKey === event.ctrlKey;
        const metaMatches = !!shortcut.metaKey === event.metaKey;
        const shiftMatches = !!shortcut.shiftKey === event.shiftKey;
        const altMatches = !!shortcut.altKey === event.altKey;

        if (
          keyMatches &&
          ctrlMatches &&
          metaMatches &&
          shiftMatches &&
          altMatches
        ) {
          if (shortcut.preventDefault !== false) {
            event.preventDefault();
          }
          shortcut.action();
          break;
        }
      }
    },
    [shortcuts, enabled]
  );

  useEffect(() => {
    if (!enabled) return;

    target.addEventListener("keydown", handleKeyDown as EventListener);
    return () =>
      target.removeEventListener("keydown", handleKeyDown as EventListener);
  }, [handleKeyDown, enabled, target]);

  return {
    shortcuts: shortcuts.map((shortcut) => ({
      key: shortcut.key,
      modifiers: [
        shortcut.ctrlKey && "Ctrl",
        shortcut.metaKey && "Cmd",
        shortcut.shiftKey && "Shift",
        shortcut.altKey && "Alt",
      ]
        .filter(Boolean)
        .join("+"),
      description: shortcut.description,
    })),
  };
};
