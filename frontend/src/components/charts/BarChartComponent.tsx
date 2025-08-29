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
