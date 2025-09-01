import { useState } from "react";

interface AdvancedModeToggleProps {
  /**
   * Current execution mode
   */
  isAdvancedMode: boolean;

  /**
   * Callback when mode is toggled
   */
  onToggle: (enabled: boolean) => void;

  /**
   * Whether the toggle is disabled
   */
  disabled?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Size variant
   */
  size?: "sm" | "md" | "lg";

  /**
   * Show labels alongside the toggle
   */
  showLabels?: boolean;
}

export default function AdvancedModeToggle({
  isAdvancedMode,
  onToggle,
  disabled = false,
  className = "",
  size = "md",
  showLabels = true,
}: AdvancedModeToggleProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleToggle = () => {
    if (!disabled) {
      onToggle(!isAdvancedMode);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleToggle();
    }
  };

  // Size configurations
  const sizeConfig = {
    sm: {
      container: "text-xs",
      toggle: "w-8 h-4",
      thumb: "w-3 h-3",
      thumbTranslate: isAdvancedMode ? "translate-x-4" : "translate-x-0.5",
      padding: "p-0.5",
    },
    md: {
      container: "text-sm",
      toggle: "w-10 h-5",
      thumb: "w-4 h-4",
      thumbTranslate: isAdvancedMode ? "translate-x-5" : "translate-x-0.5",
      padding: "p-0.5",
    },
    lg: {
      container: "text-base",
      toggle: "w-12 h-6",
      thumb: "w-5 h-5",
      thumbTranslate: isAdvancedMode ? "translate-x-6" : "translate-x-0.5",
      padding: "p-0.5",
    },
  };

  const config = sizeConfig[size];

  return (
    <div className={`flex items-center gap-3 ${config.container} ${className}`}>
      {showLabels && (
        <span
          className={`font-medium transition-colors ${
            !isAdvancedMode ? "text-gray-900" : "text-gray-500"
          } ${disabled ? "opacity-50" : ""}`}
        >
          Automatic
        </span>
      )}

      <div className="relative">
        {/* Toggle Switch */}
        <button
          type="button"
          role="switch"
          aria-checked={isAdvancedMode}
          aria-label={`Switch to ${
            isAdvancedMode ? "automatic" : "advanced"
          } execution mode`}
          aria-describedby="execution-mode-description"
          disabled={disabled}
          onClick={handleToggle}
          onKeyDown={handleKeyDown}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          data-testid="advanced-mode-toggle"
          className={`
            relative inline-flex ${config.toggle} ${config.padding}
            rounded-full transition-all duration-200 ease-in-out
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            ${
              isAdvancedMode
                ? "bg-blue-600 hover:bg-blue-700"
                : "bg-gray-200 hover:bg-gray-300"
            }
            ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            ${isHovered && !disabled ? "shadow-md" : ""}
          `}
        >
          {/* Toggle Thumb */}
          <span
            className={`
              inline-block ${config.thumb} rounded-full bg-white shadow-lg
              transform transition-transform duration-200 ease-in-out
              ${config.thumbTranslate}
              ${disabled ? "" : "group-hover:shadow-xl"}
            `}
          />
        </button>

        {/* Tooltip on hover */}
        {isHovered && !disabled && (
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap z-10">
            {isAdvancedMode
              ? "Switch to automatic execution"
              : "Switch to manual SQL review"}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-2 border-r-2 border-t-2 border-transparent border-t-gray-900" />
          </div>
        )}
      </div>

      {showLabels && (
        <span
          className={`font-medium transition-colors ${
            isAdvancedMode ? "text-gray-900" : "text-gray-500"
          } ${disabled ? "opacity-50" : ""}`}
        >
          Advanced
        </span>
      )}

      {/* Screen reader description */}
      <span id="execution-mode-description" className="sr-only">
        {isAdvancedMode
          ? "Advanced mode: SQL queries will be shown for review before execution"
          : "Automatic mode: SQL queries will be executed immediately after generation"}
      </span>
    </div>
  );
}
