# Data Display and Chat Response Improvements

## Introduction

This specification addresses critical user experience issues in the dashly application where uploaded CSV data is not properly displayed in the table view, chat responses override the data table instead of updating the dashboard, and chat responses are too technical rather than user-friendly. The goal is to create a clear separation between data viewing and dashboard visualization while providing conversational, insightful responses.

## Requirements

### Requirement 1: Proper CSV Data Display in Table View

**User Story:** As a user, I want to see my uploaded CSV data immediately displayed in a clear table format, so that I can verify the data was uploaded correctly and understand its structure.

#### Acceptance Criteria

1. WHEN a user successfully uploads a CSV file THEN the system SHALL immediately display the data in a table format in the main content area
2. WHEN the table is displayed THEN it SHALL show all column headers with proper formatting
3. WHEN the table contains many rows THEN the system SHALL implement pagination or virtual scrolling to display the first 50-100 rows with navigation controls
4. WHEN the table is shown THEN it SHALL include data type indicators for each column (text, number, date, etc.)
5. WHEN no data is uploaded THEN the system SHALL show a clear message prompting the user to upload a CSV file
6. WHEN the CSV has formatting issues THEN the system SHALL display the data that could be parsed and show clear error messages for problematic rows

### Requirement 2: Separate Dashboard and Data Views

**User Story:** As a user, I want to clearly distinguish between viewing my raw data and viewing dashboard visualizations, so that I can switch between them without losing either view.

#### Acceptance Criteria

1. WHEN data is uploaded THEN the system SHALL provide two distinct view modes: "Data" and "Dashboard"
2. WHEN in "Data" mode THEN the system SHALL display the raw CSV data in table format
3. WHEN in "Dashboard" mode THEN the system SHALL display charts and visualizations created from chat queries
4. WHEN switching between modes THEN the system SHALL preserve the state of both views
5. WHEN a chat query creates a visualization THEN it SHALL only update the Dashboard view, not replace the Data view
6. WHEN no visualizations exist THEN the Dashboard view SHALL show a message indicating no charts have been created yet
7. WHEN the user is in Data mode and asks a question THEN the system SHALL automatically switch to Dashboard mode to show the results

### Requirement 3: Conversational and Insightful Chat Responses

**User Story:** As a user, I want chat responses that provide meaningful insights in plain English rather than technical execution details, so that I can understand what the data reveals without needing technical knowledge.

#### Acceptance Criteria

1. WHEN the system processes a data query THEN it SHALL respond with conversational insights rather than technical execution details
2. WHEN presenting results THEN the system SHALL explain what the data shows in business terms (e.g., "Your sales peaked in December with $50K revenue" instead of "Query executed successfully. Found 5 rows.")
3. WHEN creating visualizations THEN the system SHALL explain what the chart reveals (e.g., "I've created a bar chart showing that Widget A is your top seller, generating nearly twice the revenue of your next best product")
4. WHEN data patterns are detected THEN the system SHALL highlight interesting trends or outliers conversationally
5. WHEN suggesting follow-up questions THEN the system SHALL phrase them as natural conversation starters
6. WHEN errors occur THEN the system SHALL explain what went wrong in user-friendly terms without exposing technical details
7. WHEN no interesting patterns exist THEN the system SHALL acknowledge this and suggest alternative ways to explore the data

### Requirement 4: Intelligent Response Formatting

**User Story:** As a user, I want chat responses to be well-structured and easy to scan, so that I can quickly understand the key insights and decide on next steps.

#### Acceptance Criteria

1. WHEN providing insights THEN the system SHALL structure responses with clear key findings at the top
2. WHEN multiple insights are found THEN the system SHALL present them as bullet points or numbered lists
3. WHEN including numbers or statistics THEN the system SHALL format them in a readable way (e.g., "$49,319" instead of "49319.84999999")
4. WHEN suggesting actions THEN the system SHALL clearly separate suggestions from findings
5. WHEN the response is long THEN the system SHALL use appropriate formatting to improve readability
6. WHEN referencing data columns THEN the system SHALL use business-friendly names when possible

### Requirement 5: Context-Aware Dashboard Updates

**User Story:** As a user, I want the dashboard to intelligently update with new visualizations while preserving previous charts that are still relevant, so that I can build up a comprehensive view of my data over time.

#### Acceptance Criteria

1. WHEN a new query creates a visualization THEN the system SHALL add it to the dashboard without removing existing charts unless they conflict
2. WHEN a query updates existing data THEN the system SHALL refresh the relevant charts while preserving others
3. WHEN multiple charts show similar data THEN the system SHALL ask the user if they want to replace or keep both
4. WHEN the dashboard becomes cluttered THEN the system SHALL suggest organizing or removing older charts
5. WHEN charts are added THEN the system SHALL arrange them in a logical layout automatically
6. WHEN a chart is no longer relevant THEN the system SHALL provide easy ways to remove it

### Requirement 6: Error Handling and User Guidance

**User Story:** As a user, I want clear guidance when something goes wrong or when I ask questions that can't be answered, so that I can understand how to proceed.

#### Acceptance Criteria

1. WHEN a query cannot be processed THEN the system SHALL explain why in simple terms and suggest alternatives
2. WHEN data is missing for a requested analysis THEN the system SHALL explain what data would be needed
3. WHEN a question is too vague THEN the system SHALL ask clarifying questions conversationally
4. WHEN technical errors occur THEN the system SHALL translate them into user-friendly explanations
5. WHEN the system is unsure about user intent THEN it SHALL offer multiple interpretation options
6. WHEN suggesting corrections THEN the system SHALL provide specific examples of better questions to ask
