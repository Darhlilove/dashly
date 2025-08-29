# Implementation Plan

- [x] 1. Set up project foundation and type definitions

  - Create TypeScript interfaces for API responses, chart configurations, and application state
  - Set up the API service layer with Axios configuration and error handling
  - Configure Tailwind CSS theme with custom colors and design system
  - _Requirements: 7.1, 8.1, 8.2_

- [x] 2. Implement core UI components and utilities

  - Create LoadingSpinner component with Tailwind styling
  - Create Toast notification component with success/error states and auto-dismiss functionality
  - Implement chart selection utility functions that analyze data shape and return appropriate ChartConfig
  - _Requirements: 9.3, 9.1, 9.2, 4.1, 4.2, 4.3, 4.4_

- [x] 3. Build UploadWidget component with file handling

  - Create UploadWidget component with file input, drag-and-drop support, and "Use Demo Data" button
  - Implement file upload logic that calls `/api/upload` endpoint with proper error handling
  - Add demo data functionality that calls the upload API with demo flag
  - Write unit tests for file upload scenarios and demo data selection
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 4. Implement QueryBox component for natural language input

  - Create QueryBox component with textarea input and "Generate" button
  - Add loading states and disable button during API calls
  - Implement integration with `/api/translate` endpoint to convert natural language to SQL
  - Write unit tests for query input handling and API integration
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Build SQLPreviewModal for SQL review and execution

  - Create modal component with overlay, generated SQL display, and action buttons
  - Implement editable SQL textarea with basic formatting
  - Add "Run Query" functionality that calls `/api/execute` endpoint
  - Include modal close/cancel functionality and proper state management
  - Write unit tests for modal interactions and SQL execution
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 6. Create ChartRenderer component with automatic chart selection

  - Implement data analysis functions that determine appropriate chart type based on column types and data shape
  - Create Recharts integration for line charts with time series data
  - Create Recharts integration for bar charts with categorical data
  - Create Recharts integration for pie charts with small cardinality categorical data
  - Implement fallback table view for data that doesn't match chart patterns
  - Write unit tests for chart type selection logic and rendering
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 7. Implement dashboard saving functionality

  - Add "Save Dashboard" button to ChartRenderer component
  - Create dashboard name input modal or inline input
  - Implement API call to `/api/dashboards` endpoint with dashboard configuration
  - Add success/error toast notifications for save operations
  - Write unit tests for dashboard saving workflow
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Build DashboardCard component for saved dashboards

  - Create DashboardCard component with title display and mini-chart preview
  - Implement click-to-load functionality that restores saved dashboard state
  - Add responsive grid layout for multiple dashboard cards
  - Create empty state component for when no dashboards exist
  - Write unit tests for dashboard card interactions and loading
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9. Integrate main App component with state management

  - Create main App component that manages global application state
  - Implement routing logic between upload phase and query phase based on table existence
  - Add toast notification context and error boundary for global error handling
  - Integrate all components into cohesive user workflow
  - Write integration tests for complete user journey from upload to dashboard creation
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 10. Add responsive design and accessibility features

  - Implement responsive breakpoints for mobile and tablet devices
  - Add proper ARIA labels and keyboard navigation support
  - Ensure color contrast meets accessibility standards
  - Add focus management for modal components
  - Test and fix any responsive design issues across different screen sizes
  - _Requirements: 8.5, 8.3, 8.4_

- [ ] 11. Implement error handling and loading states

  - Add comprehensive error handling for all API calls with specific error messages
  - Implement loading spinners and skeleton screens for better user experience
  - Add retry mechanisms for failed network requests
  - Create error boundary components to catch and handle React component errors
  - Write unit tests for error scenarios and recovery mechanisms
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 12. Optimize performance and add final polish
  - Implement React.memo for expensive chart rendering components
  - Add code splitting for chart components to reduce initial bundle size
  - Implement debouncing for query input to prevent excessive API calls
  - Add session storage caching for recent query results
  - Perform final testing of complete workflow and fix any remaining issues
  - _Requirements: 7.4, 8.1, 8.2_
