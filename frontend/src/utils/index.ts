// Utility functions for the dashly frontend

// Export chart selection utilities
export * from "./chartSelector";

// Export cache utilities
export * from "./cache";

// Generate unique IDs for components
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

// Format file size for display
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Validate file type
export function isValidCSVFile(file: File): boolean {
  const validTypes = ["text/csv", "application/csv", "text/plain"];
  const validExtensions = [".csv"];

  return (
    validTypes.includes(file.type) ||
    validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))
  );
}

// Debounce function for input handling
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Format runtime for display
export function formatRuntime(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  } else {
    return `${(ms / 1000).toFixed(2)}s`;
  }
}
