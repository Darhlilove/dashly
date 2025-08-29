import { vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UploadWidget } from "../components";
import { ToastContainer } from "../components";
import { ApiError } from "../types/api";

// Mock the API service
const mockApiService = {
  uploadFile: vi.fn(),
  useDemoData: vi.fn(),
  translateQuery: vi.fn(),
  executeSQL: vi.fn(),
  saveDashboard: vi.fn(),
  getDashboards: vi.fn().mockResolvedValue([]),
};

vi.mock("../services/api", () => ({
  apiService: mockApiService,
}));

// Mock console methods
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  console.error = vi.fn();
  console.warn = vi.fn();
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

// Test component that includes error handling
const TestUploadComponent: React.FC = () => {
  const [notifications, setNotifications] = React.useState<any[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const addNotification = (
    type: "success" | "error" | "info",
    message: string
  ) => {
    const notification = {
      id: Date.now().toString(),
      type,
      message,
      duration: type === "error" ? 7000 : 5000,
    };
    setNotifications((prev) => [...prev, notification]);
  };

  const removeNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setError(null);

    try {
      await mockApiService.uploadFile(file);
      addNotification("success", `Successfully uploaded ${file.name}`);
    } catch (error) {
      const apiError = error as ApiError;
      setError(apiError.message);
      addNotification("error", `Upload failed: ${apiError.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await mockApiService.useDemoData();
      addNotification("success", "Demo data loaded successfully");
    } catch (error) {
      const apiError = error as ApiError;
      setError(apiError.message);
      addNotification("error", `Failed to load demo data: ${apiError.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <UploadWidget
        onFileUpload={handleFileUpload}
        onDemoData={handleDemoData}
        isLoading={isLoading}
        error={error}
      />
      <ToastContainer
        notifications={notifications}
        onDismiss={removeNotification}
      />
    </div>
  );
};

describe("Error Handling Integration", () => {
  it("should handle file upload errors gracefully", async () => {
    const uploadError: ApiError = {
      message: "Internal server error",
      code: "INTERNAL_ERROR",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.uploadFile.mockRejectedValue(uploadError);

    render(<TestUploadComponent />);

    // Create a test file
    const file = new File(["test,data\n1,2"], "test.csv", { type: "text/csv" });

    // Find file input and upload file
    const fileInput = screen.getByTestId("file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Wait for upload button to appear after file selection
    await waitFor(() => {
      expect(screen.getByTestId("upload-button")).toBeInTheDocument();
    });

    // Click upload button
    const uploadButton = screen.getByTestId("upload-button");
    fireEvent.click(uploadButton);

    // Wait for error toast to appear
    await waitFor(() => {
      expect(
        screen.getByText(/upload failed.*internal server error/i)
      ).toBeInTheDocument();
    });

    // Should still show upload widget
    expect(screen.getByTestId("upload-widget")).toBeInTheDocument();
  });

  it("should handle demo data loading errors", async () => {
    const demoError: ApiError = {
      message: "Internal server error",
      code: "INTERNAL_ERROR",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.useDemoData.mockRejectedValue(demoError);

    render(<TestUploadComponent />);

    // Click demo data button
    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    // Wait for error toast to appear
    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*internal server error/i)
      ).toBeInTheDocument();
    });

    // Should still show upload widget
    expect(screen.getByTestId("upload-widget")).toBeInTheDocument();
  });

  it("should show loading states during API calls", async () => {
    // Mock slow upload response
    mockApiService.useDemoData.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                table: "test_table",
                columns: [{ name: "id", type: "INTEGER" }],
              }),
            100
          )
        )
    );

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    // Should show loading state
    expect(screen.getByText("Loading demo data...")).toBeInTheDocument();
    expect(demoButton).toBeDisabled();

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(
          screen.getByText("Demo data loaded successfully")
        ).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("should handle network errors with appropriate messages", async () => {
    const networkError: ApiError = {
      message:
        "Network error: Unable to connect to server. Please check your internet connection.",
      code: "NETWORK_ERROR",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.useDemoData.mockRejectedValue(networkError);

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*network error/i)
      ).toBeInTheDocument();
    });
  });

  it("should handle validation errors appropriately", async () => {
    const validationError: ApiError = {
      message: "Invalid file format. File appears to be corrupted.",
      code: "VALIDATION_ERROR",
      retryable: false,
      timestamp: new Date().toISOString(),
    };

    mockApiService.uploadFile.mockRejectedValue(validationError);

    render(<TestUploadComponent />);

    // Create a valid CSV file (passes client-side validation) but server rejects it
    const file = new File(["invalid,csv,content"], "test.csv", {
      type: "text/csv",
    });

    const fileInput = screen.getByTestId("file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Wait for upload button to appear after file selection
    await waitFor(() => {
      expect(screen.getByTestId("upload-button")).toBeInTheDocument();
    });

    const uploadButton = screen.getByTestId("upload-button");
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(
        screen.getByText(/upload failed.*invalid file format/i)
      ).toBeInTheDocument();
    });
  });

  it("should recover from errors and allow retry", async () => {
    // First call fails, second succeeds
    mockApiService.useDemoData
      .mockRejectedValueOnce({
        message: "Temporary error",
        code: "INTERNAL_ERROR",
        retryable: true,
        timestamp: new Date().toISOString(),
      })
      .mockResolvedValueOnce({
        table: "test_table",
        columns: [{ name: "id", type: "INTEGER" }],
      });

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");

    // First attempt fails
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*temporary error/i)
      ).toBeInTheDocument();
    });

    // Should still be able to retry
    expect(demoButton).not.toBeDisabled();

    // Second attempt succeeds
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText("Demo data loaded successfully")
      ).toBeInTheDocument();
    });
  });

  it("should display error messages in the upload widget", async () => {
    const uploadError: ApiError = {
      message: "File too large",
      code: "FILE_TOO_LARGE",
      retryable: false,
      timestamp: new Date().toISOString(),
    };

    mockApiService.uploadFile.mockRejectedValue(uploadError);

    render(<TestUploadComponent />);

    const file = new File(["test,data\n1,2"], "test.csv", { type: "text/csv" });
    const fileInput = screen.getByTestId("file-input");
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByTestId("upload-button")).toBeInTheDocument();
    });

    const uploadButton = screen.getByTestId("upload-button");
    fireEvent.click(uploadButton);

    // Wait for error to appear in the widget
    await waitFor(() => {
      expect(screen.getByText("File too large")).toBeInTheDocument();
    });
  });

  it("should handle timeout errors with appropriate retry behavior", async () => {
    const timeoutError: ApiError = {
      message: "Request timeout. Please check your connection and try again.",
      code: "TIMEOUT_ERROR",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.useDemoData.mockRejectedValue(timeoutError);

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*request timeout/i)
      ).toBeInTheDocument();
    });

    // Should still be able to retry for timeout errors
    expect(demoButton).not.toBeDisabled();
  });

  it("should handle rate limit errors appropriately", async () => {
    const rateLimitError: ApiError = {
      message: "Too many requests. Please wait a moment and try again.",
      code: "RATE_LIMIT_ERROR",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.useDemoData.mockRejectedValue(rateLimitError);

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*too many requests/i)
      ).toBeInTheDocument();
    });
  });

  it("should handle service unavailable errors", async () => {
    const serviceError: ApiError = {
      message: "Service unavailable. Please try again later.",
      code: "SERVICE_UNAVAILABLE",
      retryable: true,
      timestamp: new Date().toISOString(),
    };

    mockApiService.useDemoData.mockRejectedValue(serviceError);

    render(<TestUploadComponent />);

    const demoButton = screen.getByTestId("demo-data-button");
    fireEvent.click(demoButton);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load demo data.*service unavailable/i)
      ).toBeInTheDocument();
    });
  });
});
