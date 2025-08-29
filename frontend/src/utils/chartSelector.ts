import { ChartConfig, ChartData } from "../types";

// Column type analysis
interface ColumnAnalysis {
  name: string;
  type: "numeric" | "categorical" | "datetime" | "text";
  uniqueValues: number;
  sampleValues: any[];
}

/**
 * Analyzes column types based on data content
 */
export function analyzeColumnTypes(
  columns: string[],
  rows: any[][]
): ColumnAnalysis[] {
  return columns.map((columnName, index) => {
    const columnValues = rows
      .map((row) => row[index])
      .filter((val) => val != null);
    const uniqueValues = new Set(columnValues);
    const sampleValues = Array.from(uniqueValues).slice(0, 10);

    // Determine column type
    let type: ColumnAnalysis["type"] = "text";

    if (columnValues.length === 0) {
      type = "text";
    } else if (isDateTimeColumn(columnValues)) {
      type = "datetime";
    } else if (isNumericColumn(columnValues)) {
      type = "numeric";
    } else if (
      uniqueValues.size < columnValues.length &&
      uniqueValues.size <= 50
    ) {
      // If unique values are less than total values (repeated values) and max 50, treat as categorical
      type = "categorical";
    } else {
      type = "text";
    }

    return {
      name: columnName,
      type,
      uniqueValues: uniqueValues.size,
      sampleValues,
    };
  });
}

/**
 * Checks if column contains datetime values
 */
function isDateTimeColumn(values: any[]): boolean {
  if (values.length === 0) return false;

  const sampleSize = Math.min(values.length, 10);
  const dateCount = values.slice(0, sampleSize).reduce((count, value) => {
    if (typeof value === "string") {
      // Check for common date patterns
      const datePatterns = [
        /^\d{4}-\d{2}-\d{2}/, // YYYY-MM-DD
        /^\d{2}\/\d{2}\/\d{4}/, // MM/DD/YYYY
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/, // ISO datetime
        /^\d{4}-\d{2}/, // YYYY-MM
      ];

      if (datePatterns.some((pattern) => pattern.test(value))) {
        return count + 1;
      }

      // Try parsing as date
      const parsed = new Date(value);
      if (!isNaN(parsed.getTime()) && value.length > 4) {
        return count + 1;
      }
    }
    return count;
  }, 0);

  return dateCount / sampleSize >= 0.8; // 80% of samples should be dates
}

/**
 * Checks if column contains numeric values
 */
function isNumericColumn(values: any[]): boolean {
  if (values.length === 0) return false;

  const sampleSize = Math.min(values.length, 10);
  const numericCount = values.slice(0, sampleSize).reduce((count, value) => {
    if (typeof value === "number" && !isNaN(value)) {
      return count + 1;
    }
    if (typeof value === "string") {
      const parsed = parseFloat(value);
      if (!isNaN(parsed) && isFinite(parsed)) {
        return count + 1;
      }
    }
    return count;
  }, 0);

  return numericCount / sampleSize >= 0.8; // 80% of samples should be numeric
}

/**
 * Selects appropriate chart type based on data analysis
 */
export function selectChartType(data: ChartData): ChartConfig {
  const { columns, rows } = data;

  if (rows.length === 0 || columns.length === 0) {
    return { type: "table" };
  }

  const columnAnalysis = analyzeColumnTypes(columns, rows);

  const datetimeColumns = columnAnalysis.filter(
    (col) => col.type === "datetime"
  );
  const numericColumns = columnAnalysis.filter((col) => col.type === "numeric");
  const categoricalColumns = columnAnalysis.filter(
    (col) => col.type === "categorical"
  );

  // Rule 1: Line Chart - One datetime column + numeric columns
  if (datetimeColumns.length === 1 && numericColumns.length >= 1) {
    return {
      type: "line",
      x: datetimeColumns[0].name,
      y: numericColumns[0].name,
      groupBy: numericColumns.length > 1 ? numericColumns[1].name : undefined,
    };
  }

  // Rule 2: Pie Chart - One categorical column with ≤8 unique values + one numeric column
  if (categoricalColumns.length >= 1 && numericColumns.length >= 1) {
    const smallCategorical = categoricalColumns.find(
      (col) => col.uniqueValues <= 8
    );
    if (smallCategorical) {
      return {
        type: "pie",
        x: smallCategorical.name,
        y: numericColumns[0].name,
        limit: 8,
      };
    }
  }

  // Rule 3: Bar Chart - One categorical column + one numeric column
  if (categoricalColumns.length >= 1 && numericColumns.length >= 1) {
    return {
      type: "bar",
      x: categoricalColumns[0].name,
      y: numericColumns[0].name,
      limit: categoricalColumns[0].uniqueValues > 20 ? 20 : undefined,
    };
  }

  // Rule 4: Line Chart fallback - If we have any numeric data and first column could be x-axis
  if (numericColumns.length >= 2) {
    // Check if first column could be treated as x-axis (even if not datetime)
    return {
      type: "line",
      x: numericColumns[0].name,
      y: numericColumns[1].name,
    };
  }

  // Default: Table view
  return { type: "table" };
}

/**
 * Gets unique values for a specific column
 */
export function getUniqueValues(rows: any[][], columnIndex: number): any[] {
  const values = rows
    .map((row) => row[columnIndex])
    .filter((val) => val != null);
  return Array.from(new Set(values));
}

/**
 * Validates if chart configuration is appropriate for the data
 */
export function validateChartConfig(
  data: ChartData,
  config: ChartConfig
): boolean {
  const { columns, rows } = data;

  if (config.type === "table") {
    return true; // Table can always display any data
  }

  // Check if specified columns exist
  if (config.x && !columns.includes(config.x)) {
    return false;
  }

  if (config.y && !columns.includes(config.y)) {
    return false;
  }

  if (config.groupBy && !columns.includes(config.groupBy)) {
    return false;
  }

  // Validate data has enough rows for meaningful charts
  if (rows.length === 0) {
    return false;
  }

  return true;
}

/**
 * Creates a fallback chart configuration when automatic selection fails
 */
export function createFallbackConfig(data: ChartData): ChartConfig {
  const { columns, rows } = data;

  if (columns.length === 0 || rows.length === 0) {
    return { type: "table" };
  }

  // Simple fallback: use first two columns if available
  if (columns.length >= 2) {
    return {
      type: "bar",
      x: columns[0],
      y: columns[1],
    };
  }

  return { type: "table" };
}
