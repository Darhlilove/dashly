# Requirements Document

## Introduction

This feature implements a React TypeScript frontend application using Vite and Tailwind CSS that provides an intuitive interface for the dashly dashboard auto-designer. The frontend enables users to upload CSV data or use demo data, input natural language queries, preview and execute generated SQL, and view results as automatically selected charts or tables. The interface follows a minimalistic, boxy design aesthetic similar to Notion.

## Requirements

### Requirement 1

**User Story:** As a dashly user, I want a clean upload interface on the home page, so that I can either upload my CSV data or use demo data to get started quickly.

#### Acceptance Criteria

1. WHEN the user visits the root path `/` THEN the system SHALL display an UploadWidget component with file upload functionality
2. WHEN the user selects a CSV file THEN the system SHALL show the file name and provide an upload button
3. WHEN the user clicks upload THEN the system SHALL send a POST request to `/api/upload` with the CSV file
4. WHEN the user wants to use demo data THEN the system SHALL provide a "Use Demo Data" button that calls `/api/upload` with demo flag
5. WHEN upload succeeds THEN the system SHALL hide the upload widget and show the QueryBox component
6. WHEN upload fails THEN the system SHALL display an error toast with the failure reason

### Requirement 2

**User Story:** As a dashly user, I want to input natural language queries in a simple text box, so that I can describe what data visualization I want to create.

#### Acceptance Criteria

1. WHEN a table exists in the database THEN the system SHALL display a QueryBox component with a text input field
2. WHEN the user types a natural language query THEN the system SHALL provide a "Generate" button to process the query
3. WHEN the user clicks Generate THEN the system SHALL send a POST request to `/api/translate` with the natural language query
4. WHEN translation succeeds THEN the system SHALL open a SQLPreviewModal showing the generated SQL
5. WHEN translation fails THEN the system SHALL display an error toast with the failure reason

### Requirement 3

**User Story:** As a dashly user, I want to preview and optionally edit the generated SQL before execution, so that I can verify the query matches my intent.

#### Acceptance Criteria

1. WHEN SQL is generated from natural language THEN the system SHALL display a SQLPreviewModal component
2. WHEN the modal opens THEN it SHALL show the generated SQL in an editable text area
3. WHEN the user wants to execute the query THEN the system SHALL provide a "Run Query" button
4. WHEN the user clicks Run Query THEN the system SHALL send a POST request to `/api/execute` with the SQL
5. WHEN the user wants to cancel THEN the system SHALL provide a close button that dismisses the modal
6. WHEN SQL execution succeeds THEN the system SHALL close the modal and display the ChartRenderer component

### Requirement 4

**User Story:** As a dashly user, I want automatic chart type selection based on my query results, so that I get the most appropriate visualization without manual configuration.

#### Acceptance Criteria

1. WHEN query results contain 1 time column and numeric data THEN the system SHALL automatically select a line chart
2. WHEN query results contain 1 categorical column and numeric data THEN the system SHALL automatically select a bar chart
3. WHEN query results contain 1 categorical column with small cardinality (≤8 categories) THEN the system SHALL automatically select a pie chart
4. WHEN query results don't match chart patterns THEN the system SHALL default to table view
5. WHEN chart type is determined THEN the system SHALL create appropriate ChartConfig with x, y, and groupBy fields
6. WHEN charts are rendered THEN the system SHALL use Recharts library for visualization

### Requirement 5

**User Story:** As a dashly user, I want to save successful dashboard configurations, so that I can reuse and share my visualizations.

#### Acceptance Criteria

1. WHEN a chart is successfully rendered THEN the system SHALL provide a "Save Dashboard" button
2. WHEN the user clicks Save Dashboard THEN the system SHALL prompt for a dashboard name
3. WHEN the user provides a name THEN the system SHALL send a POST request to `/api/dashboards` with `{name, question, sql, chartConfig}`
4. WHEN dashboard save succeeds THEN the system SHALL display a success toast
5. WHEN dashboard save fails THEN the system SHALL display an error toast with the failure reason

### Requirement 6

**User Story:** As a dashly user, I want to view my saved dashboards as cards, so that I can quickly access and reuse previous visualizations.

#### Acceptance Criteria

1. WHEN saved dashboards exist THEN the system SHALL display DashboardCard components for each saved dashboard
2. WHEN a dashboard card is displayed THEN it SHALL show the dashboard title and a chart snapshot
3. WHEN the user clicks a dashboard card THEN the system SHALL load and display that dashboard's visualization
4. WHEN dashboard cards are rendered THEN they SHALL use a grid layout that's responsive to screen size
5. WHEN no dashboards exist THEN the system SHALL show an appropriate empty state message

### Requirement 7

**User Story:** As a developer, I want strongly typed TypeScript interfaces, so that the frontend has type safety and better development experience.

#### Acceptance Criteria

1. WHEN ChartConfig is defined THEN it SHALL include type as 'line'|'bar'|'pie'|'table' and optional x, y, groupBy, limit fields
2. WHEN API responses are typed THEN they SHALL match the backend response formats exactly
3. WHEN components are implemented THEN they SHALL use proper TypeScript interfaces for props
4. WHEN data flows through the application THEN it SHALL maintain type safety from API calls to chart rendering
5. WHEN the application is built THEN it SHALL have no TypeScript compilation errors

### Requirement 8

**User Story:** As a dashly user, I want a minimalistic and clean interface design, so that I can focus on creating dashboards without visual distractions.

#### Acceptance Criteria

1. WHEN the application loads THEN it SHALL use a boxy, minimalistic design similar to Notion
2. WHEN components are styled THEN they SHALL use Tailwind CSS with a consistent color theme
3. WHEN interactive elements are displayed THEN they SHALL have clear hover and focus states
4. WHEN loading states occur THEN the system SHALL show a simple loading spinner component
5. WHEN the interface is responsive THEN it SHALL work well on both desktop and mobile devices

### Requirement 9

**User Story:** As a dashly user, I want clear feedback about system operations, so that I understand what's happening and can respond to errors appropriately.

#### Acceptance Criteria

1. WHEN any operation succeeds THEN the system SHALL display a success toast notification
2. WHEN any operation fails THEN the system SHALL display an error toast with a clear error message
3. WHEN operations are in progress THEN the system SHALL show loading indicators
4. WHEN errors occur THEN the system SHALL provide actionable feedback when possible
5. WHEN toast notifications appear THEN they SHALL auto-dismiss after 5 seconds or allow manual dismissal

### Requirement 10

**User Story:** As a developer, I want the frontend to integrate seamlessly with the existing backend APIs, so that the full dashly workflow functions correctly.

#### Acceptance Criteria

1. WHEN the frontend calls `/api/upload` THEN it SHALL handle both file upload and demo data scenarios correctly
2. WHEN the frontend calls `/api/translate` THEN it SHALL send natural language queries and receive SQL responses
3. WHEN the frontend calls `/api/execute` THEN it SHALL send SQL queries and receive structured data results
4. WHEN the frontend calls `/api/dashboards` THEN it SHALL save dashboard configurations correctly
5. WHEN API calls are made THEN the system SHALL handle network errors and timeouts gracefully
