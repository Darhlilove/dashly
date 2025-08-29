import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Vendor chunks
          if (id.includes("node_modules")) {
            if (id.includes("react") || id.includes("react-dom")) {
              return "react-vendor";
            }
            if (id.includes("recharts")) {
              return "charts";
            }
            if (id.includes("axios")) {
              return "http";
            }
            return "vendor";
          }

          // Feature-based chunks
          if (
            id.includes("ChartRenderer") ||
            id.includes("SaveDashboardModal")
          ) {
            return "charts-ui";
          }
          if (id.includes("DashboardGrid") || id.includes("DashboardCard")) {
            return "dashboard";
          }
          if (id.includes("UploadWidget") || id.includes("UploadPhase")) {
            return "upload";
          }
          if (
            id.includes("QueryBox") ||
            id.includes("QueryPhase") ||
            id.includes("SQLPreviewModal")
          ) {
            return "query";
          }
          if (
            id.includes("Toast") ||
            id.includes("LoadingSpinner") ||
            id.includes("ErrorBoundary")
          ) {
            return "ui";
          }
        },
      },
    },
    // Increase chunk size warning limit to 600KB since we're optimizing
    chunkSizeWarningLimit: 600,
  },
});
