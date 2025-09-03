/**
 * Dashboard Automation Service
 *
 * Handles automatic dashboard updates when chart configurations are received
 * from chat interactions, providing seamless integration between conversational
 * responses and dashboard visualization updates.
 */

import { apiService } from "./api";
import { ChartConfig, ExecuteResponse } from "../types";
import { selectChartType } from "../utils/chartSelector";

export interface DashboardUpdateResult {
  success: boolean;
  chartConfig: ChartConfig;
  queryResults?: ExecuteResponse;
  error?: string;
}

export interface AutomaticDashboardOptions {
  onUpdate?: (result: DashboardUpdateResult) => void;
  onError?: (error: string) => void;
  executeQuery?: boolean; // Whether to execute a query to get data for the chart
}

class DashboardAutomationService {
  /**
   * Process a chart configuration from chat and automatically update the dashboard
   */
  async processChartRecommendation(
    chartConfig: ChartConfig,
    userQuestion: string,
    options: AutomaticDashboardOptions = {}
  ): Promise<DashboardUpdateResult> {
    try {
      console.log(
        "🔄 Processing chart recommendation for automatic dashboard update"
      );
      console.log("📊 Chart config:", chartConfig);
      console.log("❓ User question:", userQuestion);

      // If we need to execute a query to get data for the chart
      if (options.executeQuery) {
        try {
          // Execute the user's question to get data
          const automaticResult = await apiService.executeQueryAutomatically(
            userQuestion
          );
          const queryResults = automaticResult.executionResult;

          // Validate that the recommended chart config is suitable for the data
          const validatedChartConfig = this.validateAndAdjustChartConfig(
            chartConfig,
            queryResults
          );

          const result: DashboardUpdateResult = {
            success: true,
            chartConfig: validatedChartConfig,
            queryResults: queryResults,
          };

          console.log(
            "✅ Automatic dashboard update successful with query execution"
          );
          options.onUpdate?.(result);
          return result;
        } catch (queryError) {
          console.error(
            "❌ Failed to execute query for dashboard update:",
            queryError
          );

          // Fall back to just using the chart config without data
          const result: DashboardUpdateResult = {
            success: false,
            chartConfig: chartConfig,
            error: `Failed to execute query: ${queryError}`,
          };

          options.onError?.(result.error);
          return result;
        }
      } else {
        // Just use the chart config without executing a query
        const result: DashboardUpdateResult = {
          success: true,
          chartConfig: chartConfig,
        };

        console.log(
          "✅ Chart recommendation processed without query execution"
        );
        options.onUpdate?.(result);
        return result;
      }
    } catch (error) {
      const errorMessage = `Failed to process chart recommendation: ${error}`;
      console.error("❌", errorMessage);

      const result: DashboardUpdateResult = {
        success: false,
        chartConfig: chartConfig,
        error: errorMessage,
      };

      options.onError?.(errorMessage);
      return result;
    }
  }

  /**
   * Validate and adjust chart configuration based on actual query results
   */
  private validateAndAdjustChartConfig(
    recommendedConfig: ChartConfig,
    queryResults: ExecuteResponse
  ): ChartConfig {
    console.log("🔍 Validating chart config against query results");

    // If no data, fall back to table view
    if (!queryResults.rows || queryResults.rows.length === 0) {
      console.log("⚠️ No data available, falling back to table view");
      return { type: "table" };
    }

    // Check if recommended axes exist in the data
    const availableColumns = queryResults.columns;

    let adjustedConfig = { ...recommendedConfig };
    let needsAdjustment = false;

    // Validate x-axis column
    if (
      adjustedConfig.x_axis &&
      !availableColumns.includes(adjustedConfig.x_axis)
    ) {
      console.log(
        `⚠️ X-axis column '${adjustedConfig.x_axis}' not found in results`
      );
      adjustedConfig.x_axis = availableColumns[0] || undefined;
      needsAdjustment = true;
    }

    // Validate y-axis column
    if (
      adjustedConfig.y_axis &&
      !availableColumns.includes(adjustedConfig.y_axis)
    ) {
      console.log(
        `⚠️ Y-axis column '${adjustedConfig.y_axis}' not found in results`
      );
      adjustedConfig.y_axis =
        availableColumns[1] || availableColumns[0] || undefined;
      needsAdjustment = true;
    }

    // If significant adjustments were needed, fall back to automatic chart selection
    if (needsAdjustment) {
      console.log(
        "🔄 Significant adjustments needed, using automatic chart selection"
      );
      const autoSelectedConfig = selectChartType({
        columns: queryResults.columns,
        rows: queryResults.rows,
      });

      // Preserve the title from the original recommendation if available
      if (recommendedConfig.title && !autoSelectedConfig.title) {
        autoSelectedConfig.title = recommendedConfig.title;
      }

      return autoSelectedConfig;
    }

    console.log("✅ Chart config validation successful");
    return adjustedConfig;
  }

  /**
   * Determine if a chart configuration should trigger an automatic dashboard update
   */
  shouldAutoUpdateDashboard(
    chartConfig: ChartConfig,
    userQuestion: string
  ): boolean {
    // Don't auto-update for table views unless explicitly requested
    if (chartConfig.type === "table") {
      const questionLower = userQuestion.toLowerCase();
      return (
        questionLower.includes("table") || questionLower.includes("show all")
      );
    }

    // Auto-update for all other chart types
    return true;
  }

  /**
   * Generate a dashboard name based on the user question and chart type
   */
  generateDashboardName(
    userQuestion: string,
    chartConfig: ChartConfig
  ): string {
    // Clean up the question to make it dashboard-name-like
    let name = userQuestion.trim();

    // Remove question words
    const questionStarters = [
      "show me",
      "what is",
      "what are",
      "how much",
      "how many",
      "can you show",
    ];
    const nameLower = name.toLowerCase();

    for (const starter of questionStarters) {
      if (nameLower.startsWith(starter)) {
        name = name.substring(starter.length).trim();
        break;
      }
    }

    // Remove trailing question mark
    if (name.endsWith("?")) {
      name = name.slice(0, -1);
    }

    // Capitalize first letter
    if (name.length > 0) {
      name = name.charAt(0).toUpperCase() + name.slice(1);
    }

    // Add chart type context if the name is generic
    if (
      name.length < 10 ||
      ["data", "information", "results"].includes(name.toLowerCase())
    ) {
      const chartTypeNames = {
        bar: "Bar Chart",
        line: "Line Chart",
        pie: "Pie Chart",
        table: "Data Table",
      };
      const chartTypeName =
        chartTypeNames[chartConfig.type as keyof typeof chartTypeNames] ||
        "Chart";
      name = `${name} ${chartTypeName}`.trim();
    }

    // Limit length
    if (name.length > 50) {
      name = name.substring(0, 47) + "...";
    }

    return name || "Dashboard";
  }
}

// Export singleton instance
export const dashboardAutomationService = new DashboardAutomationService();
export default dashboardAutomationService;
