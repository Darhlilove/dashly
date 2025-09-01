# Design Document

## Overview

The automatic query execution feature transforms the dashly user experience by eliminating the manual SQL approval step. Instead of showing users a modal to review and approve generated SQL, the system will automatically execute validated queries and display results immediately. This design maintains all existing security measures while providing a seamless, non-technical user experience.

The feature introduces a streamlined flow: Natural Language → SQL Generation → Automatic Execution → Dashboard Display, with optional advanced mode for power users who want SQL review capabilities.

## Architecture

### Current Flow

```
User Query → API Translation → SQLPreviewModal → Manual Approval → API Execution → Dashboard
```

### New Flow (Default)

```
User Query → API Translation → Automatic Execution → Dashboard + Conversation Update
```

### New Flow (Advanced Mode)

```
User Query → API Translation → SQLPreviewModal → Manual Approval → API Execution → Dashboard
```

### Component Architecture Changes

The design modifies the existing React component architecture to support automatic execution while preserving the manual review option:

1. **App.tsx**: Main orchestration logic updated to support automatic vs manual execution modes
2. **ConversationPane**: Enhanced to show SQL queries and execution status in chat
3. **SQLPreviewModal**: Becomes optional, only shown in advanced mode
4. **New AdvancedModeToggle**: Component to switch between automatic and manual execution
5. **Enhanced Message Types**: Support for SQL display and execution status in conversation

## Components and Interfaces

### Enhanced App State

```typescript
interface AppState {
  // Existing fields...
  uploadStatus: "idle" | "uploading" | "completed" | "error";
  tableInfo: TableInfo | null;
  currentQuery: string;
  currentSQL: string;
  queryResults: ExecuteResponse | null;
  currentChart: ChartConfig | null;
  savedDashboards: Dashboard[];
  showSQLModal: boolean;
  isLoading: boolean;
  error: string | null;

  // New fields for automatic execution
  executionMode: "automatic" | "advanced";
  isExecutingQuery: boolean;
  lastExecutionTime?: number;
}
```

### Enhanced Message Types

```typescript
interface SQLMessage extends Message {
  type: "assistant";
  sqlQuery?: string;
  executionStatus?: "pending" | "executing" | "completed" | "failed";
  executionTime?: number;
  rowCount?: number;
}

interface ExecutionStatusMessage extends Message {
  type: "system";
  status: "executing" | "completed" | "failed";
  details?: {
    executionTime?: number;
    rowCount?: number;
    error?: string;
  };
}
```

### New AdvancedModeToggle Component

```typescript
interface AdvancedModeToggleProps {
  isAdvancedMode: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
}
```

### Enhanced ConversationPane

The conversation pane will be enhanced to display SQL queries and execution status:

```typescript
interface ConversationPaneProps {
  messages: Message[];
  onSendMessage: (query: string) => void;
  isLoading: boolean;
  executionMode: "automatic" | "advanced";
  onExecutionModeChange: (mode: "automatic" | "advanced") => void;
}
```

## Data Models

### Execution Flow State Machine

```typescript
type ExecutionState =
  | { phase: "idle" }
  | { phase: "translating"; query: string }
  | { phase: "translated"; sql: string; query: string }
  | { phase: "executing"; sql: string; query: string }
  | { phase: "completed"; results: ExecuteResponse; sql: string; query: string }
  | { phase: "failed"; error: string; sql?: string; query: string };
```

### Enhanced API Service Methods

The existing API service will be enhanced with automatic execution orchestration:

```typescript
interface AutomaticExecutionResult {
  translationResult: TranslateResponse;
  executionResult: ExecuteResponse;
  executionTime: number;
  fromCache: boolean;
}

class ApiService {
  // New method for automatic execution flow
  async executeQueryAutomatically(
    query: string
  ): Promise<AutomaticExecutionResult>;

  // Enhanced existing methods remain unchanged
  translateQuery(query: string): Promise<TranslateResponse>;
  executeSQL(sql: string, question?: string): Promise<ExecuteResponse>;
}
```

## Error Handling

### Error Recovery Strategy

The automatic execution feature implements comprehensive error handling at multiple levels:

1. **Translation Errors**: Display user-friendly messages in conversation pane with suggestions for rephrasing
2. **Execution Errors**: Show SQL validation errors in plain language with retry options
3. **Network Errors**: Implement retry logic with exponential backoff
4. **Timeout Errors**: Graceful degradation with clear timeout messages

### Error Message Enhancement

```typescript
interface ExecutionError {
  phase: "translation" | "execution" | "network";
  originalError: ApiError;
  userFriendlyMessage: string;
  suggestions: string[];
  retryable: boolean;
}
```

### Error Display in Conversation

Errors will be displayed as assistant messages in the conversation pane rather than modal dialogs:

```typescript
interface ErrorMessage extends Message {
  type: "assistant";
  isError: true;
  errorPhase: "translation" | "execution";
  suggestions: string[];
  retryable: boolean;
}
```

## Testing Strategy

### Unit Testing

1. **App Component Tests**: Verify automatic execution flow and mode switching
2. **ConversationPane Tests**: Test SQL display and execution status rendering
3. **API Service Tests**: Mock automatic execution scenarios and error conditions
4. **Message Rendering Tests**: Verify proper display of SQL and execution status

### Integration Testing

1. **End-to-End Flow Tests**: Complete user journey from query to dashboard
2. **Error Scenario Tests**: Translation failures, execution failures, network issues
3. **Mode Switching Tests**: Verify seamless transition between automatic and advanced modes
4. **Caching Integration Tests**: Ensure cached results work with automatic execution

### Performance Testing

1. **Execution Time Measurement**: Verify automatic execution doesn't add latency
2. **Memory Usage Tests**: Ensure no memory leaks from automatic execution
3. **Concurrent Execution Tests**: Multiple queries in rapid succession
4. **Cache Performance Tests**: Verify caching improves automatic execution speed

### Accessibility Testing

1. **Screen Reader Tests**: Ensure execution status is announced properly
2. **Keyboard Navigation Tests**: Mode toggle and conversation navigation
3. **Focus Management Tests**: Proper focus handling during automatic execution
4. **ARIA Labels Tests**: Execution status and SQL display accessibility

## Implementation Phases

### Phase 1: Core Automatic Execution

- Modify App.tsx to support automatic execution flow
- Update handleQuery method to automatically execute after translation
- Remove SQLPreviewModal display in automatic mode
- Add basic execution status to conversation pane

### Phase 2: Enhanced Conversation Display

- Implement SQL display in conversation messages
- Add execution status indicators and loading states
- Enhance error display in conversation pane
- Add execution time and row count display

### Phase 3: Advanced Mode Toggle

- Implement AdvancedModeToggle component
- Add mode persistence to user preferences
- Ensure seamless switching between modes
- Maintain backward compatibility with existing modal flow

### Phase 4: Error Handling and Polish

- Implement comprehensive error recovery
- Add user-friendly error messages and suggestions
- Enhance loading states and transitions
- Add performance monitoring for automatic execution

## Security Considerations

### SQL Validation Preservation

All existing SQL validation and security measures remain in place:

- Read-only SELECT statement enforcement
- SQL injection prevention
- Query timeout limits
- Resource usage monitoring

### Automatic Execution Safety

The automatic execution feature maintains security through:

- Same validation pipeline as manual execution
- No bypass of existing security checks
- Audit logging of all automatic executions
- Rate limiting to prevent abuse

### User Control

Users maintain control through:

- Advanced mode toggle for manual review when needed
- Clear visibility of generated SQL in conversation
- Ability to see execution details and errors
- Option to retry with different queries

## Performance Optimizations

### Execution Pipeline Optimization

1. **Parallel Processing**: Where possible, prepare dashboard rendering while query executes
2. **Caching Strategy**: Leverage existing query result caching for repeated queries
3. **Preemptive Loading**: Prepare chart components during SQL generation
4. **Memory Management**: Efficient cleanup of execution state and intermediate results

### User Experience Optimizations

1. **Progressive Loading**: Show intermediate states during automatic execution
2. **Optimistic Updates**: Prepare UI elements while query executes
3. **Smooth Transitions**: Animate between conversation and dashboard states
4. **Responsive Feedback**: Immediate acknowledgment of user queries

## Migration Strategy

### Backward Compatibility

The feature maintains full backward compatibility:

- Existing SQLPreviewModal functionality preserved in advanced mode
- All existing API endpoints remain unchanged
- Saved dashboards continue to work without modification
- User preferences and session data remain compatible

### Gradual Rollout

1. **Default Mode**: Automatic execution becomes the default for new users
2. **Existing Users**: Advanced mode toggle allows opt-in to automatic execution
3. **Feature Discovery**: In-app guidance to introduce automatic execution benefits
4. **Fallback Support**: Advanced mode always available as fallback option
