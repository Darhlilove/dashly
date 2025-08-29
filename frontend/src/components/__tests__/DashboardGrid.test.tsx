import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import DashboardGrid, { EmptyDashboardState, DashboardGridSkeleton } from "../DashboardGrid";
import { Dashboard } from "../../types/dashboard";

// Mock DashboardCard component
vi.mock("../DashboardCard", () => ({
  default: ({ dashboard, onLoad }: { dashboard: Dashboard; onLoad: (d: Dashboard) => void }) => (
    <div
      data-testid={`dashboard-card-${dashboard.id}`}
      onClick={() => onLoad(dashboard)}
    >
      {dashboard.name}
    </div>
  ),
}));

describe("DashboardGrid", () => {
  const mockOnLoadDashboard = vi.fn();

  const mockDashboards: Dashboard[] = [
    {
      id: "dashboard-1",
      name: "Sales Dashboard",
      question: "Monthly sales trends",
      sql: "SELECT * FROM sales",
      chartConfig: { type: "line", x: "month", y: "sales" },
      createdAt: "2024-01-15T10:30:00Z",
    },
    {
      id: "dashboard-2",
      name: "Revenue Dashboard",
      question: "Revenue by region",
      sql: "SELECT * FROM revenue",
      chartConfig: { type: "bar", x: "region", y: "revenue" },
      createdAt: "2024-01-16T10:30:00Z",
    },
    {
      id: "dashboard-3",
      name: "User Analytics",
      question: "User engagement metrics",
      sql: "SELECT * FROM users",
      chartConfig: { type: "pie", x: "category", y: "count" },
      createdAt: "2024-01-17T10:30:00Z",
    },
  ];

  beforeEach(() => {
    mockOnLoadDashboard.mockClear();
  });

  describe("DashboardGrid", () => {
    it("renders dashboard cards in a grid", () => {
      render(
        <DashboardGrid
          dashboards={mockDashboards}
          onLoadDashboard={mockOnLoadDashboard}
        />
      );

      expect(screen.getByTestId("dashboard-card-dashboard-1")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-card-dashboard-2")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-card-dashboard-3")).toBeInTheDocument();

      expect(screen.getByText("Sales Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Revenue Dashboard")).toBeInTheDocument();
      expect(screen.getByText("User Analytics")).toBeInTheDocument();
    });

    it("calls onLoadDashboard when a card is clicked", () => {
      render(
        <DashboardGrid
          dashboards={mockDashboards}
          onLoadDashboard={mockOnLoadDashboard}
        />
      );

      const firstCard = screen.getByTestId("dashboard-card-dashboard-1");
      fireEvent.click(firstCard);

      expect(mockOnLoadDashboard).toHaveBeenCalledWith(mockDashboards[0]);
      expect(mockOnLoadDashboard).toHaveBeenCalledTimes(1);
    });

    it("renders empty state when no dashboards exist", () => {
      render(
        <DashboardGrid
          dashboards={[]}
          onLoadDashboard={mockOnLoadDashboard}
        />
      );

      expect(screen.getByText("No dashboards yet")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Create your first dashboard by uploading data and asking a question. Your saved dashboards will appear here."
        )
      ).toBeInTheDocument();
    });

    it("renders skeleton when loading", () => {
      render(
        <DashboardGrid
          dashboards={mockDashboards}
          onLoadDashboard={mockOnLoadDashboard}
          isLoading={true}
        />
      );

      // Should not render actual dashboard cards when loading
      expect(screen.queryByTestId("dashboard-card-dashboard-1")).not.toBeInTheDocument();
      
      // Should render skeleton elements
      const skeletonElements = screen.getAllByRole("generic");
      expect(skeletonElements.length).toBeGreaterThan(0);
    });

    it("applies custom className", () => {
      const { container } = render(
        <DashboardGrid
          dashboards={mockDashboards}
          onLoadDashboard={mockOnLoadDashboard}
          className="custom-grid-class"
        />
      );

      const gridContainer = container.firstChild as HTMLElement;
      expect(gridContainer).toHaveClass("custom-grid-class");
    });

    it("renders responsive grid classes", () => {
      const { container } = render(
        <DashboardGrid
          dashboards={mockDashboards}
          onLoadDashboard={mockOnLoadDashboard}
        />
      );

      const gridElement = container.querySelector(".grid");
      expect(gridElement).toHaveClass("grid-cols-1");
      expect(gridElement).toHaveClass("sm:grid-cols-2");
      expect(gridElement).toHaveClass("lg:grid-cols-3");
      expect(gridElement).toHaveClass("xl:grid-cols-4");
    });
  });

  describe("EmptyDashboardState", () => {
    it("renders empty state message", () => {
      render(<EmptyDashboardState />);

      expect(screen.getByText("No dashboards yet")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Create your first dashboard by uploading data and asking a question. Your saved dashboards will appear here."
        )
      ).toBeInTheDocument();
    });

    it("renders workflow hint", () => {
      render(<EmptyDashboardState />);

      expect(
        screen.getByText("Upload CSV → Ask question → Save dashboard")
      ).toBeInTheDocument();
    });

    it("renders dashboard icon", () => {
      const { container } = render(<EmptyDashboardState />);

      // Look for the main dashboard icon SVG specifically
      const dashboardIcon = container.querySelector('svg[viewBox="0 0 24 24"]');
      expect(dashboardIcon).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <EmptyDashboardState className="custom-empty-class" />
      );

      const emptyStateContainer = container.firstChild as HTMLElement;
      expect(emptyStateContainer).toHaveClass("custom-empty-class");
    });
  });

  describe("DashboardGridSkeleton", () => {
    it("renders skeleton cards", () => {
      render(<DashboardGridSkeleton />);

      const skeletonCards = screen.getAllByRole("generic");
      // Should render multiple skeleton cards (6 by default)
      expect(skeletonCards.length).toBeGreaterThan(5);
    });

    it("renders skeleton elements with animation", () => {
      const { container } = render(<DashboardGridSkeleton />);

      const animatedElements = container.querySelectorAll(".animate-pulse");
      expect(animatedElements.length).toBeGreaterThan(0);
    });

    it("applies custom className", () => {
      const { container } = render(
        <DashboardGridSkeleton className="custom-skeleton-class" />
      );

      const skeletonContainer = container.firstChild as HTMLElement;
      expect(skeletonContainer).toHaveClass("custom-skeleton-class");
    });

    it("renders responsive grid classes", () => {
      const { container } = render(<DashboardGridSkeleton />);

      const gridElement = container.querySelector(".grid");
      expect(gridElement).toHaveClass("grid-cols-1");
      expect(gridElement).toHaveClass("sm:grid-cols-2");
      expect(gridElement).toHaveClass("lg:grid-cols-3");
      expect(gridElement).toHaveClass("xl:grid-cols-4");
    });
  });
});