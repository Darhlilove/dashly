import React, { memo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface LineChartComponentProps {
  data: any[];
  config: {
    x?: string;
    y?: string;
    groupBy?: string;
  };
  colors: string[];
  height: number;
}

const LineChartComponent: React.FC<LineChartComponentProps> = memo(
  ({ data, config, colors, height }) => {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
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
          <Line
            type="monotone"
            dataKey={config.y}
            stroke={colors[0]}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          {config.groupBy && (
            <Line
              type="monotone"
              dataKey={config.groupBy}
              stroke={colors[1]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    );
  }
);

LineChartComponent.displayName = "LineChartComponent";

export default LineChartComponent;
