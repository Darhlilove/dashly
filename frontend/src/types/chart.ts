// Chart Configuration Types for automatic chart selection

export interface ChartConfig {
  type: "line" | "bar" | "pie" | "table";
  x?: string;
  y?: string;
  groupBy?: string;
  limit?: number;
}

export interface ChartData {
  columns: string[];
  rows: any[][];
}

export interface ChartProps {
  data: ChartData;
  config: ChartConfig;
  width?: number;
  height?: number;
}
