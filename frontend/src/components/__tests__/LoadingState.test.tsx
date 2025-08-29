import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import LoadingState, {
  FileUploadLoading,
  QueryProcessingLoading,
  DashboardLoadingOverlay,
} from "../LoadingState";

// Mock LoadingSpinner component
vi.mock("../LoadingSpinner", () => ({
  default: ({ size, className }: { size: string; className: string }) => (
    <div data-testid="loading-spinner" data-size={size} className={className}>
      Loading...
    </div>
  ),
}));

describe("LoadingState", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should render children when not loading", () => {
    render(
      <LoadingState isLoading={false}>
        <div>Content</div>
      </LoadingState>
    );

    expect(screen.getByText("Content")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-spinner")).not.toBeInTheDocument();
  });

  it("should render loading state when loading", () => {
    render(
      <LoadingState isLoading={true} message="Loading data...">
        <div>Content</div>
      </LoadingState>
    );

    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    expect(screen.getByText("Loading data...")).toBeInTheDocument();
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });

  it("should show progress bar when progress is provided", () => {
    render(
      <LoadingState
        isLoading={true}
        progress={75}
        showProgress={true}
        message="Uploading..."
      />
    );

    expect(screen.getByText("75% complete")).toBeInTheDocument();

    // Check for progress bar (it should have width style)
    const progressBar = screen.getByRole("progressbar", { hidden: true });
    expect(progressBar).toHaveStyle({ width: "75%" });
  });

  it("should show elapsed time after 5 seconds", async () => {
    render(<LoadingState isLoading={true} message="Processing..." />);

    // Initially no elapsed time
    expect(screen.queryByText(/elapsed:/i)).not.toBeInTheDocument();

    // Fast-forward 6 seconds
    vi.advanceTimersByTime(6000);

    await waitFor(() => {
      expect(screen.getByText(/elapsed: 6s/i)).toBeInTheDocument();
    });
  });

  it("should show elapsed time in minutes and seconds format", async () => {
    render(<LoadingState isLoading={true} message="Processing..." />);

    // Fast-forward 75 seconds (1m 15s)
    vi.advanceTimersByTime(75000);

    await waitFor(() => {
      expect(screen.getByText(/elapsed: 1m 15s/i)).toBeInTheDocument();
    });
  });

  it("should update message with elapsed time after 10 seconds", async () => {
    render(<LoadingState isLoading={true} message="Processing..." />);

    // Fast-forward 12 seconds
    vi.advanceTimersByTime(12000);

    await waitFor(() => {
      expect(screen.getByText(/processing.*12s/i)).toBeInTheDocument();
    });
  });

  it("should call onTimeout and show timeout message", async () => {
    const mockOnTimeout = vi.fn();

    render(
      <LoadingState
        isLoading={true}
        message="Processing..."
        timeout={5000}
        onTimeout={mockOnTimeout}
      />
    );

    // Fast-forward past timeout
    vi.advanceTimersByTime(6000);

    await waitFor(() => {
      expect(mockOnTimeout).toHaveBeenCalledTimes(1);
      expect(
        screen.getByText("This is taking longer than expected...")
      ).toBeInTheDocument();
    });

    // Should show timeout warning
    expect(
      screen.getByText(/operation is taking longer than usual/i)
    ).toBeInTheDocument();
  });

  it("should render as overlay when overlay prop is true", () => {
    render(
      <LoadingState isLoading={true} overlay={true} message="Loading...">
        <div>Background content</div>
      </LoadingState>
    );

    expect(screen.getByText("Background content")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
  });

  it("should handle different sizes correctly", () => {
    const { rerender } = render(<LoadingState isLoading={true} size="sm" />);

    expect(screen.getByTestId("loading-spinner")).toHaveAttribute(
      "data-size",
      "sm"
    );

    rerender(<LoadingState isLoading={true} size="lg" />);
    expect(screen.getByTestId("loading-spinner")).toHaveAttribute(
      "data-size",
      "lg"
    );
  });

  it("should clean up timers when unmounted", () => {
    const { unmount } = render(
      <LoadingState isLoading={true} timeout={5000} />
    );

    // Start some timers
    vi.advanceTimersByTime(1000);

    // Unmount component
    unmount();

    // Advance time further - should not cause any issues
    vi.advanceTimersByTime(10000);

    // No assertions needed - just ensuring no errors are thrown
  });

  it("should reset state when loading changes from true to false", async () => {
    const { rerender } = render(
      <LoadingState isLoading={true} timeout={5000} />
    );

    // Fast-forward to build up elapsed time
    vi.advanceTimersByTime(3000);

    // Stop loading
    rerender(<LoadingState isLoading={false} timeout={5000} />);

    // Start loading again
    rerender(<LoadingState isLoading={true} timeout={5000} />);

    // Should not show elapsed time immediately
    expect(screen.queryByText(/elapsed:/i)).not.toBeInTheDocument();
  });
});

describe("FileUploadLoading", () => {
  it("should show file upload specific message", () => {
    render(
      <FileUploadLoading isLoading={true} fileName="test.csv" progress={50} />
    );

    expect(screen.getByText("Uploading test.csv...")).toBeInTheDocument();
    expect(screen.getByText("50% complete")).toBeInTheDocument();
  });

  it("should show generic upload message when no filename", () => {
    render(<FileUploadLoading isLoading={true} />);

    expect(screen.getByText("Uploading file...")).toBeInTheDocument();
  });
});

describe("QueryProcessingLoading", () => {
  it("should show different messages for different stages", () => {
    const { rerender } = render(
      <QueryProcessingLoading isLoading={true} stage="translating" />
    );

    expect(
      screen.getByText("Converting your question to SQL...")
    ).toBeInTheDocument();

    rerender(<QueryProcessingLoading isLoading={true} stage="executing" />);
    expect(screen.getByText("Running your query...")).toBeInTheDocument();

    rerender(<QueryProcessingLoading isLoading={true} stage="processing" />);
    expect(screen.getByText("Processing your request...")).toBeInTheDocument();
  });
});

describe("DashboardLoadingOverlay", () => {
  it("should render as overlay with custom message", () => {
    render(
      <DashboardLoadingOverlay
        isLoading={true}
        message="Loading dashboard data..."
      >
        <div>Dashboard content</div>
      </DashboardLoadingOverlay>
    );

    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Loading dashboard data...")).toBeInTheDocument();
  });

  it("should use default message when none provided", () => {
    render(
      <DashboardLoadingOverlay isLoading={true}>
        <div>Dashboard content</div>
      </DashboardLoadingOverlay>
    );

    expect(screen.getByText("Loading dashboard...")).toBeInTheDocument();
  });
});
