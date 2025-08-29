import { describe, it, expect } from "vitest";
import {
  analyzeColumnTypes,
  selectChartType,
  validateChartConfig,
  getUniqueValues,
  createFallbackConfig,
} from "../chartSelector";
import { ChartData, ChartConfig } from "../../types";

describe("chartSelector", () => {
  describe("analyzeColumnTypes", () => {
    it("should identify numeric columns", () => {
      const columns = ["id", "value"];
      const rows = [
        [1, 100],
        [2, 200],
        [3, 300],
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("numeric");
      expect(analysis[1].type).toBe("numeric");
    });

    it("should identify categorical columns", () => {
      const columns = ["category", "region"];
      const rows = [
        ["A", "North"],
        ["B", "South"],
        ["A", "North"],
        ["C", "East"],
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("categorical");
      expect(analysis[1].type).toBe("categorical");
      expect(analysis[0].uniqueValues).toBe(3); // A, B, C
      expect(analysis[1].uniqueValues).toBe(3); // North, South, East
    });

    it("should identify datetime columns", () => {
      const columns = ["date", "timestamp"];
      const rows = [
        ["2023-01-01", "2023-01-01T10:00:00"],
        ["2023-02-01", "2023-02-01T11:00:00"],
        ["2023-03-01", "2023-03-01T12:00:00"],
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("datetime");
      expect(analysis[1].type).toBe("datetime");
    });

    it("should identify text columns", () => {
      const columns = ["description", "notes"];
      const rows = [
        ["This is a long description", "Some notes here"],
        ["Another description", "More notes"],
        ["Yet another description", "Even more notes"],
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("text");
      expect(analysis[1].type).toBe("text");
    });

    it("should handle mixed data types", () => {
      const columns = ["id", "name", "value", "date"];
      const rows = [
        [1, "Item A", 100, "2023-01-01"],
        [2, "Item B", 200, "2023-02-01"],
        [3, "Item C", 300, "2023-03-01"],
        [4, "Item A", 150, "2023-04-01"], // Repeat Item A to make it categorical
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("numeric"); // id
      expect(analysis[1].type).toBe("categorical"); // name (low cardinality with repeats)
      expect(analysis[2].type).toBe("numeric"); // value
      expect(analysis[3].type).toBe("datetime"); // date
    });

    it("should handle empty data", () => {
      const columns = ["col1", "col2"];
      const rows: any[][] = [];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("text");
      expect(analysis[1].type).toBe("text");
    });

    it("should handle numeric strings", () => {
      const columns = ["price", "quantity"];
      const rows = [
        ["10.99", "5"],
        ["20.50", "3"],
        ["15.75", "8"],
      ];

      const analysis = analyzeColumnTypes(columns, rows);

      expect(analysis[0].type).toBe("numeric");
      expect(analysis[1].type).toBe("numeric");
    });
  });

  describe("selectChartType", () => {
    it("should select line chart for time series data", () => {
      const data: ChartData = {
        columns: ["date", "revenue"],
        rows: [
          ["2023-01-01", 1000],
          ["2023-02-01", 1200],
          ["2023-03-01", 1100],
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("line");
      expect(config.x).toBe("date");
      expect(config.y).toBe("revenue");
    });

    it("should select pie chart for small categorical data", () => {
      const data: ChartData = {
        columns: ["category", "value"],
        rows: [
          ["A", 100],
          ["B", 200],
          ["C", 150],
          ["A", 50], // Duplicate to keep cardinality low
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("pie");
      expect(config.x).toBe("category");
      expect(config.y).toBe("value");
      expect(config.limit).toBe(8);
    });

    it("should select bar chart for large categorical data", () => {
      const data: ChartData = {
        columns: ["category", "value"],
        rows: [
          ["Category A", 100],
          ["Category B", 200],
          ["Category C", 150],
          ["Category D", 300],
          ["Category E", 250],
          ["Category F", 180],
          ["Category G", 220],
          ["Category H", 190],
          ["Category I", 280],
          ["Category A", 120], // Repeat to make it categorical
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("bar");
      expect(config.x).toBe("category");
      expect(config.y).toBe("value");
    });

    it("should select table for complex data", () => {
      const data: ChartData = {
        columns: ["id", "description", "notes"],
        rows: [
          [1, "Long description text", "Some notes"],
          [2, "Another description", "More notes"],
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("table");
    });

    it("should select table for empty data", () => {
      const data: ChartData = {
        columns: [],
        rows: [],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("table");
    });

    it("should handle multiple numeric columns in line chart", () => {
      const data: ChartData = {
        columns: ["date", "revenue", "profit"],
        rows: [
          ["2023-01-01", 1000, 200],
          ["2023-02-01", 1200, 300],
          ["2023-03-01", 1100, 250],
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("line");
      expect(config.x).toBe("date");
      expect(config.y).toBe("revenue");
      expect(config.groupBy).toBe("profit");
    });

    it("should fallback to line chart for numeric data without datetime", () => {
      const data: ChartData = {
        columns: ["x", "y"],
        rows: [
          [1, 10],
          [2, 20],
          [3, 15],
        ],
      };

      const config = selectChartType(data);

      expect(config.type).toBe("line");
      expect(config.x).toBe("x");
      expect(config.y).toBe("y");
    });
  });

  describe("validateChartConfig", () => {
    const sampleData: ChartData = {
      columns: ["category", "value"],
      rows: [
        ["A", 100],
        ["B", 200],
      ],
    };

    it("should validate correct configuration", () => {
      const config: ChartConfig = {
        type: "bar",
        x: "category",
        y: "value",
      };

      expect(validateChartConfig(sampleData, config)).toBe(true);
    });

    it("should reject configuration with non-existent columns", () => {
      const config: ChartConfig = {
        type: "bar",
        x: "nonexistent",
        y: "value",
      };

      expect(validateChartConfig(sampleData, config)).toBe(false);
    });

    it("should always validate table configuration", () => {
      const config: ChartConfig = {
        type: "table",
      };

      expect(validateChartConfig(sampleData, config)).toBe(true);
    });

    it("should reject configuration for empty data", () => {
      const emptyData: ChartData = {
        columns: ["col1"],
        rows: [],
      };

      const config: ChartConfig = {
        type: "bar",
        x: "col1",
        y: "col1",
      };

      expect(validateChartConfig(emptyData, config)).toBe(false);
    });

    it("should validate configuration with groupBy", () => {
      const config: ChartConfig = {
        type: "line",
        x: "category",
        y: "value",
        groupBy: "category",
      };

      expect(validateChartConfig(sampleData, config)).toBe(true);
    });

    it("should reject configuration with invalid groupBy", () => {
      const config: ChartConfig = {
        type: "line",
        x: "category",
        y: "value",
        groupBy: "nonexistent",
      };

      expect(validateChartConfig(sampleData, config)).toBe(false);
    });
  });

  describe("getUniqueValues", () => {
    it("should return unique values from column", () => {
      const rows = [
        ["A", 100],
        ["B", 200],
        ["A", 150],
        ["C", 300],
      ];

      const uniqueValues = getUniqueValues(rows, 0);

      expect(uniqueValues).toEqual(["A", "B", "C"]);
    });

    it("should handle null values", () => {
      const rows = [
        ["A", 100],
        [null, 200],
        ["B", 150],
        [undefined, 300],
      ];

      const uniqueValues = getUniqueValues(rows, 0);

      expect(uniqueValues).toEqual(["A", "B"]);
    });

    it("should return empty array for empty data", () => {
      const rows: any[][] = [];

      const uniqueValues = getUniqueValues(rows, 0);

      expect(uniqueValues).toEqual([]);
    });
  });

  describe("createFallbackConfig", () => {
    it("should create bar chart for two-column data", () => {
      const data: ChartData = {
        columns: ["col1", "col2"],
        rows: [
          ["A", 100],
          ["B", 200],
        ],
      };

      const config = createFallbackConfig(data);

      expect(config.type).toBe("bar");
      expect(config.x).toBe("col1");
      expect(config.y).toBe("col2");
    });

    it("should create table for single column data", () => {
      const data: ChartData = {
        columns: ["col1"],
        rows: [["A"], ["B"]],
      };

      const config = createFallbackConfig(data);

      expect(config.type).toBe("table");
    });

    it("should create table for empty data", () => {
      const data: ChartData = {
        columns: [],
        rows: [],
      };

      const config = createFallbackConfig(data);

      expect(config.type).toBe("table");
    });
  });
});
