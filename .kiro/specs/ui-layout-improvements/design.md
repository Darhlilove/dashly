# UI Layout Improvements Design

## Overview

This design document outlines the implementation approach for enhancing dashly's user interface with resizable panes, auto-hiding sidebar, and flexible data visualization options. The design focuses on creating a modern, responsive interface that maximizes screen real estate while maintaining intuitive navigation.

## Architecture

### Component Hierarchy

```
App
├── AutoHideSidebar (new)
│   ├── SidebarContent (existing MainLayout sidebar)
│   └── SidebarTrigger (new)
├── ResizableLayout (new)
│   ├── ChatPane (existing MainLayout conversation)
│   ├── ResizeDivider (new)
│   └── DashboardPane (modified)
│       ├── ViewToggle (new)
│       ├── DashboardView (existing DashboardWorkspace)
│       └── DataTableView (new)
└── ResponsiveContainer (new)
```

### State Management

The layout state will be managed at the App level with the following additions:

```typescript
interface LayoutState {
  sidebarVisible: boolean;
  chatPaneWidth: number; // percentage (default: 16.67% = 1/6)
  dashboardPaneWidth: number; // percentage (default: 83.33% = 5/6)
  currentView: "dashboard" | "data";
  isMobile: boolean;
  isResizing: boolean;
}
```

## Components and Interfaces

### 1. AutoHideSidebar Component

**Purpose:** Manages the auto-hiding sidebar functionality with hover detection.

**Props:**

```typescript
interface AutoHideSidebarProps {
  children: React.ReactNode; // Main content
  sidebarContent: React.ReactNode; // Sidebar content
  isVisible: boolean;
  onVisibilityChange: (visible: boolean) => void;
  triggerWidth?: number; // Default: 20px
  hideDelay?: number; // Default: 1000ms
}
```

**Key Features:**

- Mouse position tracking for left edge detection
- Smooth CSS transitions with transform3d for performance
- Overlay positioning that doesn't affect layout
- Touch/swipe support for mobile devices

### 2. ResizableLayout Component

**Purpose:** Handles the resizable split between chat and dashboard panes.

**Props:**

```typescript
interface ResizableLayoutProps {
  chatContent: React.ReactNode;
  dashboardContent: React.ReactNode;
  initialChatWidth: number; // percentage
  onResize: (chatWidth: number, dashboardWidth: number) => void;
  minChatWidth?: number; // Default: 10%
  maxChatWidth?: number; // Default: 50%
}
```

**Key Features:**

- Drag handle with visual feedback
- Constraint-based resizing with min/max limits
- Smooth resize with requestAnimationFrame
- Keyboard accessibility for resize control

### 3. DataTableView Component

**Purpose:** Displays uploaded data in a structured table format.

**Props:**

```typescript
interface DataTableViewProps {
  tableInfo: UploadResponse;
  data?: any[][]; // Raw table data
  maxRows?: number; // Default: 100
  virtualScrolling?: boolean;
}
```

**Key Features:**

- Virtual scrolling for large datasets
- Column type indicators
- Sortable columns
- Search/filter functionality
- Export capabilities

### 4. ViewToggle Component

**Purpose:** Provides switching between dashboard and data views.

**Props:**

```typescript
interface ViewToggleProps {
  currentView: "dashboard" | "data";
  onViewChange: (view: "dashboard" | "data") => void;
  hasCharts: boolean;
  disabled?: boolean;
}
```

**Key Features:**

- Tab-style or toggle button interface
- Smooth transition animations
- Accessibility support with ARIA labels
- Visual indicators for active view

## Data Models

### Layout Configuration

```typescript
interface LayoutConfig {
  breakpoints: {
    mobile: number; // 768px
    tablet: number; // 1024px
    desktop: number; // 1200px
  };
  defaultSizes: {
    desktop: { chat: 16.67; dashboard: 83.33 };
    tablet: { chat: 20; dashboard: 80 };
    mobile: { chat: 100; dashboard: 100 }; // Stacked
  };
  animations: {
    sidebarDuration: number; // 200ms
    resizeDuration: number; // 0ms (immediate)
    viewSwitchDuration: number; // 150ms
  };
}
```

### Table Data Structure

```typescript
interface TableData {
  columns: Array<{
    name: string;
    type: string;
    sortable: boolean;
  }>;
  rows: any[][];
  totalRows: number;
  currentPage: number;
  pageSize: number;
}
```

## Error Handling

### Resize Constraints

- Prevent panes from becoming too small to be functional
- Handle edge cases where content doesn't fit
- Graceful fallback for unsupported browsers

### Mobile Compatibility

- Feature detection for touch events
- Fallback navigation for devices without hover
- Orientation change handling

### Performance Considerations

- Throttle resize events to prevent excessive re-renders
- Use CSS transforms instead of layout changes where possible
- Implement virtual scrolling for large datasets
- Lazy load non-visible content

## Testing Strategy

### Unit Tests

- Component rendering with various props
- State management and event handling
- Resize calculation logic
- Mobile/desktop behavior switching

### Integration Tests

- Sidebar show/hide functionality
- Pane resizing with mouse/touch
- View switching with data persistence
- Responsive breakpoint behavior

### Visual Regression Tests

- Layout appearance across screen sizes
- Animation smoothness and timing
- Accessibility compliance (color contrast, focus indicators)

### Performance Tests

- Large dataset rendering performance
- Memory usage during extended use
- Animation frame rate during interactions

## Implementation Phases

### Phase 1: Core Layout Structure

1. Create ResizableLayout component with basic split functionality
2. Implement AutoHideSidebar with hover detection
3. Add responsive breakpoint detection
4. Basic CSS animations and transitions

### Phase 2: Data Visualization

1. Create DataTableView component with virtual scrolling
2. Implement ViewToggle component
3. Add smooth transitions between views
4. Integrate with existing dashboard components

### Phase 3: Polish and Optimization

1. Add advanced resize constraints and snapping
2. Implement keyboard navigation support
3. Add touch/swipe gestures for mobile
4. Performance optimization and testing

### Phase 4: Accessibility and Testing

1. ARIA labels and keyboard navigation
2. Reduced motion preference support
3. Comprehensive testing across devices
4. Documentation and user guides

## CSS Architecture

### Layout System

- CSS Grid for main layout structure
- Flexbox for component internal layouts
- CSS Custom Properties for dynamic sizing
- Transform3d for smooth animations

### Responsive Design

- Mobile-first approach with progressive enhancement
- Container queries where supported
- Fluid typography and spacing
- Touch-friendly interactive elements

### Animation Strategy

- CSS transitions for simple state changes
- CSS animations for complex sequences
- JavaScript for gesture-based interactions
- Respect for prefers-reduced-motion

## Browser Compatibility

### Minimum Requirements

- Modern browsers with CSS Grid support
- Touch event support for mobile devices
- ResizeObserver API (with polyfill fallback)
- CSS Custom Properties support

### Progressive Enhancement

- Basic functionality without JavaScript
- Graceful degradation for older browsers
- Feature detection for advanced capabilities
- Polyfills for critical missing features
