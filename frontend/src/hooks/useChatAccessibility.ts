import { useEffect, useRef, useState } from "react";

export interface ChatAccessibilityOptions {
  announceNewMessages?: boolean;
  focusManagement?: boolean;
  keyboardNavigation?: boolean;
}

export interface ChatAccessibilityState {
  isScreenReaderActive: boolean;
  prefersReducedMotion: boolean;
  highContrast: boolean;
  announceMessage: (message: string) => void;
  focusInput: () => void;
  scrollToBottom: () => void;
}

/**
 * Hook for managing chat interface accessibility features
 */
export const useChatAccessibility = (
  options: ChatAccessibilityOptions = {}
): ChatAccessibilityState => {
  const {
    announceNewMessages = true,
    focusManagement = true,
    keyboardNavigation = true,
  } = options;

  const [isScreenReaderActive, setIsScreenReaderActive] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  const announcementRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Detect screen reader usage
  useEffect(() => {
    const detectScreenReader = () => {
      // Check for common screen reader indicators
      const hasScreenReader =
        window.navigator.userAgent.includes("NVDA") ||
        window.navigator.userAgent.includes("JAWS") ||
        window.speechSynthesis?.getVoices().length > 0 ||
        "speechSynthesis" in window;

      setIsScreenReaderActive(hasScreenReader);
    };

    detectScreenReader();

    // Listen for speech synthesis changes (indicates screen reader activity)
    if ("speechSynthesis" in window) {
      window.speechSynthesis.addEventListener(
        "voiceschanged",
        detectScreenReader
      );
      return () => {
        window.speechSynthesis.removeEventListener(
          "voiceschanged",
          detectScreenReader
        );
      };
    }
  }, []);

  // Detect user preferences
  useEffect(() => {
    const mediaQueries = {
      reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)"),
      highContrast: window.matchMedia("(prefers-contrast: high)"),
    };

    const updatePreferences = () => {
      setPrefersReducedMotion(mediaQueries.reducedMotion.matches);
      setHighContrast(mediaQueries.highContrast.matches);
    };

    updatePreferences();

    // Listen for changes
    mediaQueries.reducedMotion.addEventListener("change", updatePreferences);
    mediaQueries.highContrast.addEventListener("change", updatePreferences);

    return () => {
      mediaQueries.reducedMotion.removeEventListener(
        "change",
        updatePreferences
      );
      mediaQueries.highContrast.removeEventListener(
        "change",
        updatePreferences
      );
    };
  }, []);

  // Announce message function
  const announceMessage = (message: string) => {
    if (!announceNewMessages || !isScreenReaderActive) return;

    // Create a temporary announcement element
    const announcement = document.createElement("div");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = message;

    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  // Focus input function
  const focusInput = () => {
    if (focusManagement && inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Scroll to bottom function
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
      });
    }
  };

  return {
    isScreenReaderActive,
    prefersReducedMotion,
    highContrast,
    announceMessage,
    focusInput,
    scrollToBottom,
  };
};

/**
 * Hook for managing keyboard navigation in chat interface
 */
export const useChatKeyboardNavigation = (
  suggestions: string[],
  onSelectSuggestion: (suggestion: string) => void,
  enabled: boolean = true
) => {
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const suggestionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          setFocusedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
          break;
        case "ArrowUp":
          event.preventDefault();
          setFocusedIndex((prev) =>
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
          break;
        case "Enter":
          if (focusedIndex >= 0 && focusedIndex < suggestions.length) {
            event.preventDefault();
            onSelectSuggestion(suggestions[focusedIndex]);
            setFocusedIndex(-1);
          }
          break;
        case "Escape":
          event.preventDefault();
          setFocusedIndex(-1);
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [suggestions, focusedIndex, onSelectSuggestion, enabled]);

  // Focus management
  useEffect(() => {
    if (focusedIndex >= 0 && suggestionRefs.current[focusedIndex]) {
      suggestionRefs.current[focusedIndex]?.focus();
    }
  }, [focusedIndex]);

  return {
    focusedIndex,
    setFocusedIndex,
    suggestionRefs,
  };
};
