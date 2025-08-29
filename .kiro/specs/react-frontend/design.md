# Design Document

## Overview

The React frontend for dashly is a single-page application built with Vite, React 18, TypeScript, and Tailwind CSS. It provides an intuitive interface for the dashboard auto-designer workflow, featuring automatic chart generation from natural language queries. The design emphasizes simplicity, type safety, and seamless integration with the existing FastAPI backend.

## Architecture

### Technology Stack

- **Build Tool**: Vite for fast development and optimized builds
- **Framework**: React 18 with functional components and hooks
- **Language**: TypeScript for type safety and better developer experience
- **Styling**: Tailwind CSS for utility-first styling with custom theme
- **Charts**: Recharts library for data visualization
- **HTTP Client**: Axios for API communication
- **State Management**: React hooks (useState, useEffect) for local state

### Application Structure

```
frontend/src/
├── components/           # Reusable UI components
│   ├── UploadWidget.tsx
│   ├── QueryBox.tsx
│   ├── SQLPreviewModal.tsx
│   ├── ChartRenderer.tsx
│   ├── DashboardCard.tsx
│   ├── LoadingSpinner.tsx
│   └── Toast.tsx
├── types/               # TypeScript type definitions
│   ├── api.ts          # API response types
│   ├── chart.ts        # Chart configuration types
│   └── dashboard.ts    # Dashboard types
├── services/           # API service layer
│   └── api.ts         # Axios-based API client
├── utils/             # Utility functions
│   ├── chartSelector.ts # Chart type selection logic
│   └── dataMapper.ts   # Data transformation utilities
├── App.tsx            # Main application component
├── main.tsx          # Application entry point
└── index.css         # Global styles and Tailwind imports
```

## Components and Interfaces

### Core TypeScript Interfaces

```typescript
// Chart Configuration
interface ChartConfig {
  type: "line" | "bar" | "pie" | "table";
  x?: string;
  y?: string;
  groupBy?: string;
  limit?: number;
}

// API Response Types
interface UploadResponse {
  table: string;
  columns: Array<{ name: string; type: string }>;
}

interface TranslateResponse {
  sql: string;
}

interface ExecuteResponse {
  columns: string[];
  rows: any[][];
  row_count: number;
  runtime_ms: number;
}

interface Dashboard {
  id: string;
  name: string;
  question: string;
  sql: string;
  chartConfig: ChartConfig;
  createdAt: string;
}
```

### Component Architecture

#### App.tsx (Main Container)

- Manages global application state (upload status, current dashboard)
- Handles routing logic between upload and query phases
- Provides toast notification context
- Renders appropriate components based on application state

#### UploadWidget.tsx

- File upload interface with drag-and-drop support
- "Use Demo Data" button for quick testing
- Progress indicators during upload
- Error handling for invalid files

#### QueryBox.tsx

- Natural language query input with textarea
- "Generate" button with loading state
- Query history dropdown (stretch feature)
- Integration with translation API

#### SQLPreviewModal.tsx

- Modal overlay with generated SQL display
- Editable SQL textarea with syntax highlighting (basic)
- "Run Query" and "Cancel" action buttons
- SQL validation feedback

#### ChartRenderer.tsx

- Automatic chart type selection based on data shape
- Recharts integration for line, bar, and pie charts
- Fallback table view for complex data
- Responsive chart sizing

#### DashboardCard.tsx

- Compact dashboard preview with title and mini-chart
- Click-to-load functionality
- Grid layout support
- Hover effects and animations

### Chart Selection Logic

The chart type selection follows these rules:

1. **Line Chart**: Data has exactly one datetime/date column + numeric columns
2. **Bar Chart**: Data has one categorical column + one numeric column
3. **Pie Chart**: Data has one categorical column with ≤8 unique values + one numeric column
4. **Table**: Default fallback for all other data shapes

```typescript
function selectChartType(columns: string[], rows: any[][]): ChartConfig {
  const columnTypes = analyzeColumnTypes(columns, rows);

  if (hasTimeColumn(columnTypes) && hasNumericColumns(columnTypes)) {
    return {
      type: "line",
      x: getTimeColumn(columnTypes),
      y: getNumericColumn(columnTypes),
    };
  }

  if (hasCategoricalColumn(columnTypes) && hasNumericColumns(columnTypes)) {
    const categoricalCol = getCategoricalColumn(columnTypes);
    const uniqueValues = getUniqueValues(rows, categoricalCol);

    if (uniqueValues.length <= 8) {
      return {
        type: "pie",
        x: categoricalCol,
        y: getNumericColumn(columnTypes),
      };
    } else {
      return {
        type: "bar",
        x: categoricalCol,
        y: getNumericColumn(columnTypes),
      };
    }
  }

  return { type: "table" };
}
```

## Data Models

### Application State Structure

```typescript
interface AppState {
  uploadStatus: "idle" | "uploading" | "completed" | "error";
  tableInfo: UploadResponse | null;
  currentQuery: string;
  currentSQL: string;
  queryResults: ExecuteResponse | null;
  currentChart: ChartConfig | null;
  savedDashboards: Dashboard[];
  showSQLModal: boolean;
  isLoading: boolean;
  error: string | null;
}
```

### API Service Layer

```typescript
class ApiService {
  private baseURL = "/api";

  async uploadFile(file: File): Promise<UploadResponse>;
  async useDemoData(): Promise<UploadResponse>;
  async translateQuery(query: string): Promise<TranslateResponse>;
  async executeSQL(sql: string): Promise<ExecuteResponse>;
  async saveDashboard(
    dashboard: Omit<Dashboard, "id" | "createdAt">
  ): Promise<Dashboard>;
  async getDashboards(): Promise<Dashboard[]>;
}
```

## Error Handling

### Error Categories

1. **Network Errors**: Connection failures, timeouts
2. **Validation Errors**: Invalid file formats, malformed SQL
3. **Server Errors**: Backend processing failures
4. **Client Errors**: Invalid user input, missing data

### Error Handling Strategy

- Toast notifications for user-facing errors
- Console logging for debugging information
- Graceful degradation for non-critical failures
- Retry mechanisms for transient network issues

```typescript
interface ErrorHandler {
  handleUploadError(error: Error): void;
  handleQueryError(error: Error): void;
  handleNetworkError(error: Error): void;
  showErrorToast(message: string): void;
}
```

## Testing Strategy

### Unit Testing

- Component rendering and prop handling
- Chart selection logic validation
- Data transformation utilities
- API service methods

### Integration Testing

- Complete user workflow from upload to chart rendering
- API integration with mock backend responses
- Error handling scenarios
- Responsive design validation

### Testing Tools

- **Jest**: Unit test framework
- **React Testing Library**: Component testing utilities
- **MSW (Mock Service Worker)**: API mocking for integration tests

## Performance Considerations

### Optimization Strategies

1. **Code Splitting**: Lazy load chart components
2. **Memoization**: React.memo for expensive chart renders
3. **Debouncing**: Query input to prevent excessive API calls
4. **Caching**: Store recent query results in sessionStorage
5. **Bundle Size**: Tree-shaking unused Recharts components

### Loading States

- Skeleton screens for chart loading
- Progress indicators for file uploads
- Spinner components for API calls
- Optimistic UI updates where appropriate

## Styling and Theme

### Design System

- **Primary Color**: Blue (#3B82F6)
- **Secondary Color**: Gray (#6B7280)
- **Success Color**: Green (#10B981)
- **Error Color**: Red (#EF4444)
- **Background**: White/Light Gray (#F9FAFB)

### Tailwind Configuration

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: "#3B82F6",
        secondary: "#6B7280",
        success: "#10B981",
        error: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        notion: "0 1px 3px rgba(0, 0, 0, 0.1)",
      },
    },
  },
};
```

### Component Styling Patterns

- Consistent spacing using Tailwind's spacing scale
- Rounded corners (rounded-lg) for modern appearance
- Subtle shadows for depth
- Hover and focus states for all interactive elements
- Responsive design with mobile-first approach

## Integration Points

### Backend API Integration

- **Upload Endpoint**: POST `/api/upload` for file upload and demo data
- **Translation Endpoint**: POST `/api/translate` for NL to SQL conversion
- **Execution Endpoint**: POST `/api/execute` for SQL query execution
- **Dashboard Endpoint**: POST `/api/dashboards` for saving dashboard configurations

### Data Flow

1. User uploads file → Backend processes → Frontend receives table schema
2. User enters query → Frontend sends to translation API → Receives SQL
3. User approves SQL → Frontend sends to execution API → Receives data
4. Frontend analyzes data → Selects chart type → Renders visualization
5. User saves dashboard → Frontend sends configuration to backend

### Error Boundaries

React error boundaries to catch and handle component-level errors gracefully, preventing full application crashes and providing user-friendly error messages.

## Security Considerations

### Client-Side Security

- Input sanitization for user queries
- XSS prevention in dynamic content rendering
- Secure handling of file uploads (client-side validation)
- HTTPS enforcement for production deployment

### API Communication

- Proper error message handling (no sensitive data exposure)
- Request timeout configuration
- CORS handling for development environment
- Authentication headers (if implemented in future)
