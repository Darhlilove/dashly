import React, { memo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface PieChartComponentProps {
  data: any[];
  config: {
    x?: string;
    y?: string;
  };
  colors: string[];
  height: number;
}

const PieChartComponent: React.FC<PieChartComponentProps> = memo(
  ({ data, config, colors, height }) => {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) =>
              `${name} ${(percent * 100).toFixed(0)}%`
            }
            outerRadius={Math.min(height * 0.3, 100)}
            fill="#8884d8"
            dataKey={config.y || "value"}
            nameKey={config.x || "name"}
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={colors[index % colors.length]}
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }
);

PieChartComponent.displayName = "PieChartComponent";

export default PieChartComponent;
