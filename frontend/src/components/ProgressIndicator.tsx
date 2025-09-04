import React, { useState, useEffect } from "react";

interface ProgressStep {
  id: string;
  label: string;
  description?: string;
  status: "pending" | "active" | "completed" | "error";
  duration?: number; // Expected duration in ms
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentStepId?: string;
  showProgress?: boolean;
  showTimeEstimate?: boolean;
  className?: string;
  compact?: boolean;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  steps,
  currentStepId,
  showProgress = true,
  showTimeEstimate = false,
  className = "",
  compact = false,
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // Track elapsed time for current step
  useEffect(() => {
    if (currentStepId) {
      if (!startTime) {
        setStartTime(Date.now());
      }

      const interval = setInterval(() => {
        if (startTime) {
          setElapsedTime(Date.now() - startTime);
        }
      }, 100);

      return () => clearInterval(interval);
    } else {
      setStartTime(null);
      setElapsedTime(0);
    }
  }, [currentStepId, startTime]);

  // Calculate progress percentage
  const calculateProgress = () => {
    const currentIndex = steps.findIndex((step) => step.id === currentStepId);
    if (currentIndex === -1) return 0;

    const completedSteps = steps.slice(0, currentIndex).length;
    const totalSteps = steps.length;

    // Add partial progress for current step if it has duration
    const currentStep = steps[currentIndex];
    if (currentStep?.duration && elapsedTime > 0) {
      const stepProgress = Math.min(elapsedTime / currentStep.duration, 1);
      return ((completedSteps + stepProgress) / totalSteps) * 100;
    }

    return (completedSteps / totalSteps) * 100;
  };

  // Estimate remaining time
  const estimateRemainingTime = () => {
    if (!showTimeEstimate || !currentStepId) return null;

    const currentIndex = steps.findIndex((step) => step.id === currentStepId);
    if (currentIndex === -1) return null;

    const remainingSteps = steps.slice(currentIndex);
    const totalRemainingDuration = remainingSteps.reduce(
      (sum, step) => sum + (step.duration || 2000),
      0
    );

    const currentStep = steps[currentIndex];
    const currentStepRemaining = currentStep?.duration
      ? Math.max(0, currentStep.duration - elapsedTime)
      : 2000;

    const totalRemaining =
      totalRemainingDuration -
      (currentStep?.duration || 2000) +
      currentStepRemaining;

    return Math.max(0, totalRemaining);
  };

  const formatTime = (ms: number) => {
    const seconds = Math.ceil(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getStepIcon = (step: ProgressStep) => {
    switch (step.status) {
      case "completed":
        return (
          <svg
            className="w-4 h-4 text-green-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "active":
        return (
          <svg
            className="w-4 h-4 text-blue-600 animate-spin"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        );
      case "error":
        return (
          <svg
            className="w-4 h-4 text-red-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        );
      default:
        return (
          <div className="w-4 h-4 border-2 border-gray-300 rounded-full" />
        );
    }
  };

  const getStepClasses = (step: ProgressStep) => {
    const baseClasses = "flex items-center";
    switch (step.status) {
      case "completed":
        return `${baseClasses} text-green-600`;
      case "active":
        return `${baseClasses} text-blue-600 font-medium`;
      case "error":
        return `${baseClasses} text-red-600`;
      default:
        return `${baseClasses} text-gray-500`;
    }
  };

  const progress = calculateProgress();
  const remainingTime = estimateRemainingTime();

  if (compact) {
    return (
      <div className={`${className}`}>
        {showProgress && (
          <div className="mb-2">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {currentStepId && (
          <div className="text-sm text-gray-700">
            {steps.find((s) => s.id === currentStepId)?.label}
            {remainingTime && (
              <span className="text-gray-500 ml-2">
                (~{formatTime(remainingTime)} remaining)
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      {showProgress && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Overall Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          {remainingTime && (
            <div className="text-xs text-gray-500 mt-1 text-right">
              Estimated time remaining: {formatTime(remainingTime)}
            </div>
          )}
        </div>
      )}

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={step.id} className={getStepClasses(step)}>
            <div className="flex-shrink-0 mr-3">{getStepIcon(step)}</div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{step.label}</div>
              {step.description && (
                <div className="text-xs text-gray-500 mt-1">
                  {step.description}
                </div>
              )}
              {step.status === "active" && step.duration && elapsedTime > 0 && (
                <div className="text-xs text-gray-500 mt-1">
                  {formatTime(elapsedTime)} elapsed
                  {step.duration && (
                    <span> / ~{formatTime(step.duration)} expected</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProgressIndicator;

// Specialized progress indicators for common workflows
export const DataUploadProgress: React.FC<{
  currentStage:
    | "validating"
    | "uploading"
    | "parsing"
    | "storing"
    | "complete"
    | "error";
  fileName?: string;
  progress?: number;
  error?: string;
}> = ({ currentStage, fileName, progress, error }) => {
  const steps: ProgressStep[] = [
    {
      id: "validating",
      label: "Validating File",
      description: fileName
        ? `Checking ${fileName}`
        : "Checking file format and size",
      status:
        currentStage === "validating"
          ? "active"
          : ["uploading", "parsing", "storing", "complete"].includes(
              currentStage
            )
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 1000,
    },
    {
      id: "uploading",
      label: "Uploading",
      description: "Transferring file to server",
      status:
        currentStage === "uploading"
          ? "active"
          : ["parsing", "storing", "complete"].includes(currentStage)
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 3000,
    },
    {
      id: "parsing",
      label: "Parsing Data",
      description: "Reading and interpreting CSV structure",
      status:
        currentStage === "parsing"
          ? "active"
          : ["storing", "complete"].includes(currentStage)
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 2000,
    },
    {
      id: "storing",
      label: "Storing Data",
      description: "Saving to database for analysis",
      status:
        currentStage === "storing"
          ? "active"
          : currentStage === "complete"
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 2000,
    },
  ];

  return (
    <div>
      <ProgressIndicator
        steps={steps}
        currentStepId={
          currentStage !== "complete" && currentStage !== "error"
            ? currentStage
            : undefined
        }
        showProgress={true}
        showTimeEstimate={true}
        compact={false}
      />
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
};

export const QueryExecutionProgress: React.FC<{
  currentStage:
    | "translating"
    | "executing"
    | "generating_chart"
    | "complete"
    | "error";
  queryText?: string;
  progress?: number;
  error?: string;
}> = ({ currentStage, queryText, progress, error }) => {
  const steps: ProgressStep[] = [
    {
      id: "translating",
      label: "Understanding Question",
      description: queryText
        ? `"${queryText.substring(0, 50)}${queryText.length > 50 ? "..." : ""}"`
        : "Converting natural language to SQL",
      status:
        currentStage === "translating"
          ? "active"
          : ["executing", "generating_chart", "complete"].includes(currentStage)
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 3000,
    },
    {
      id: "executing",
      label: "Running Query",
      description: "Executing SQL against your data",
      status:
        currentStage === "executing"
          ? "active"
          : ["generating_chart", "complete"].includes(currentStage)
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 2000,
    },
    {
      id: "generating_chart",
      label: "Creating Visualization",
      description: "Selecting best chart type and generating display",
      status:
        currentStage === "generating_chart"
          ? "active"
          : currentStage === "complete"
          ? "completed"
          : currentStage === "error"
          ? "error"
          : "pending",
      duration: 1500,
    },
  ];

  return (
    <div>
      <ProgressIndicator
        steps={steps}
        currentStepId={
          currentStage !== "complete" && currentStage !== "error"
            ? currentStage
            : undefined
        }
        showProgress={true}
        showTimeEstimate={true}
        compact={false}
      />
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
};
