import React from "react";
import { render, screen } from "@testing-library/react";
import SkeletonLoader, {
  ChartSkeleton,
  TableSkeleton,
  DashboardCardSkeleton,
  QueryBoxSkeleton,
  UploadWidgetSkeleton,
} from "../SkeletonLoader";

describe("SkeletonLoader", () => {
  it("should render with default props", () => {
    const { container } = render(<SkeletonLoader />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass(
      "animate-pulse",
      "bg-gray-200",
      "rounded",
      "h-4"
    );
  });

  it("should render with custom className", () => {
    const { container } = render(<SkeletonLoader className="custom-class" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("custom-class");
  });

  it("should render text variant correctly", () => {
    const { container } = render(<SkeletonLoader variant="text" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("h-4");
  });

  it("should render rectangular variant correctly", () => {
    const { container } = render(<SkeletonLoader variant="rectangular" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("h-32");
  });

  it("should render circular variant correctly", () => {
    const { container } = render(<SkeletonLoader variant="circular" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("rounded-full");
  });

  it("should render chart variant correctly", () => {
    const { container } = render(<SkeletonLoader variant="chart" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("h-64");
  });

  it("should render table variant correctly", () => {
    const { container } = render(<SkeletonLoader variant="table" />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveClass("h-8");
  });

  it("should apply custom width and height", () => {
    const { container } = render(
      <SkeletonLoader width="200px" height="100px" />
    );
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveStyle({
      width: "200px",
      height: "100px",
    });
  });

  it("should apply numeric width and height", () => {
    const { container } = render(<SkeletonLoader width={200} height={100} />);
    const skeleton = container.firstChild as HTMLElement;

    expect(skeleton).toHaveStyle({
      width: "200px",
      height: "100px",
    });
  });

  it("should render multiple lines for text variant", () => {
    const { container } = render(<SkeletonLoader variant="text" lines={3} />);
    const skeletons = container.querySelectorAll(".animate-pulse");

    expect(skeletons).toHaveLength(3);

    // Last line should be shorter (3/4 width)
    const lastSkeleton = skeletons[2] as HTMLElement;
    expect(lastSkeleton).toHaveClass("w-3/4");
  });

  it("should add margin between multiple lines", () => {
    const { container } = render(<SkeletonLoader variant="text" lines={3} />);
    const skeletons = container.querySelectorAll(".animate-pulse");

    // First two lines should have margin bottom
    expect(skeletons[0]).toHaveClass("mb-2");
    expect(skeletons[1]).toHaveClass("mb-2");
    expect(skeletons[2]).not.toHaveClass("mb-2");
  });
});

describe("ChartSkeleton", () => {
  it("should render chart skeleton with header and chart area", () => {
    const { container } = render(<ChartSkeleton />);

    expect(
      container.querySelector(".bg-white.rounded-lg.border")
    ).toBeInTheDocument();

    // Should have header area with title and button
    const headerSkeletons = container.querySelectorAll(".animate-pulse");
    expect(headerSkeletons.length).toBeGreaterThan(1);
  });

  it("should apply custom className", () => {
    const { container } = render(<ChartSkeleton className="custom-chart" />);
    const chartContainer = container.firstChild as HTMLElement;

    expect(chartContainer).toHaveClass("custom-chart");
  });
});

describe("TableSkeleton", () => {
  it("should render table skeleton with default rows and columns", () => {
    render(<TableSkeleton />);

    expect(screen.getByRole("table")).toBeInTheDocument();

    // Should have header row
    const headerCells = screen.getAllByRole("columnheader");
    expect(headerCells).toHaveLength(4); // Default 4 columns

    // Should have body rows
    const bodyCells = screen.getAllByRole("cell");
    expect(bodyCells).toHaveLength(20); // 5 rows × 4 columns
  });

  it("should render table skeleton with custom rows and columns", () => {
    render(<TableSkeleton rows={3} columns={2} />);

    const headerCells = screen.getAllByRole("columnheader");
    expect(headerCells).toHaveLength(2);

    const bodyCells = screen.getAllByRole("cell");
    expect(bodyCells).toHaveLength(6); // 3 rows × 2 columns
  });

  it("should apply custom className", () => {
    const { container } = render(<TableSkeleton className="custom-table" />);
    const tableContainer = container.firstChild as HTMLElement;

    expect(tableContainer).toHaveClass("custom-table");
  });
});

describe("DashboardCardSkeleton", () => {
  it("should render dashboard card skeleton structure", () => {
    const { container } = render(<DashboardCardSkeleton />);

    expect(
      container.querySelector(".bg-white.rounded-lg.border")
    ).toBeInTheDocument();

    // Should have multiple skeleton elements for title, description, and chart
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(2);
  });

  it("should apply custom className", () => {
    const { container } = render(
      <DashboardCardSkeleton className="custom-card" />
    );
    const cardContainer = container.firstChild as HTMLElement;

    expect(cardContainer).toHaveClass("custom-card");
  });
});

describe("QueryBoxSkeleton", () => {
  it("should render query box skeleton structure", () => {
    const { container } = render(<QueryBoxSkeleton />);

    expect(
      container.querySelector(".bg-white.rounded-lg.shadow-md")
    ).toBeInTheDocument();

    // Should have skeleton elements for title, input area, and button
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(1);
  });

  it("should apply custom className", () => {
    const { container } = render(<QueryBoxSkeleton className="custom-query" />);
    const queryContainer = container.firstChild as HTMLElement;

    expect(queryContainer).toHaveClass("custom-query");
  });
});

describe("UploadWidgetSkeleton", () => {
  it("should render upload widget skeleton structure", () => {
    const { container } = render(<UploadWidgetSkeleton />);

    expect(
      container.querySelector(".border-2.border-dashed")
    ).toBeInTheDocument();

    // Should have skeleton elements for icon, text, and buttons
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(3);
  });

  it('should render "or" divider', () => {
    render(<UploadWidgetSkeleton />);

    expect(screen.getByText("or")).toBeInTheDocument();
  });

  it("should apply custom className", () => {
    const { container } = render(
      <UploadWidgetSkeleton className="custom-upload" />
    );
    const uploadContainer = container.firstChild as HTMLElement;

    expect(uploadContainer).toHaveClass("custom-upload");
  });
});
