import React, { memo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface BarChartComponentProps {
  data: any[];
  config: {
    x?: string;
    y?: string;
  };
  colors: string[];
  height: number;
}

const BarChartComponent: React.FC<BarChartComponentProps> = memo(
  ({ data, config, colors, height }) => {
    // Debug logging to help diagnose chart rendering issues
    console.log("BarChartComponent - Data:", data);
    console.log("BarChartComponent - Config:", config);
    console.log("BarChartComponent - Data length:", data?.length);

    // Check if we have valid data
    if (!data || data.length === 0) {
      return (
        <div
          style={{
            height,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <p>No data available for chart</p>
        </div>
      );
    }

    // Check if Y values exist and are numeric
    const yKey = config.y || "value";
    const hasValidYValues = data.some((item) => {
      const yValue = item[yKey];
      return yValue !== undefined && yValue !== null && !isNaN(Number(yValue));
    });

    console.log("BarChartComponent - Y key:", yKey);
    console.log("BarChartComponent - Has valid Y values:", hasValidYValues);
    console.log(
      "BarChartComponent - Sample Y values:",
      data.slice(0, 3).map((item) => ({ [yKey]: item[yKey] }))
    );

    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 5, right: 15, left: 10, bottom: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={config.x}
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey={config.y || "value"} fill={colors[0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
);

BarChartComponent.displayName = "BarChartComponent";

export default BarChartComponent;
