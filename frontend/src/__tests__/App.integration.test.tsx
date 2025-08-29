import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { apiService } from '../services/api'

// Mock the API service
vi.mock('../services/api', () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
    translateQuery: vi.fn(),
    executeSQL: vi.fn(),
    saveDashboard: vi.fn(),
    getDashboards: vi.fn(),
    getDashboard: vi.fn(),
  }
}))

// Mock chart components to avoid Recharts rendering issues in tests
vi.mock('../components/ChartRenderer', () => ({
  default: ({ data, config, onSaveDashboard }: any) => (
    <div data-testid="chart-renderer">
      <div>Chart Type: {config.type}</div>
      <div>Columns: {data.columns.join(', ')}</div>
      <div>Rows: {data.rows.length}</div>
      <button onClick={() => onSaveDashboard('Test Dashboard')}>
        Save Dashboard
      </button>
    </div>
  )
}))

const mockApiService = apiService as any

describe('App Integration Tests', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks()
    
    // Default mock implementations
    mockApiService.getDashboards.mockResolvedValue([])
    mockApiService.uploadFile.mockResolvedValue({
      table: 'test_table',
      columns: [
        { name: 'date', type: 'DATE' },
        { name: 'revenue', type: 'DECIMAL' },
        { name: 'region', type: 'VARCHAR' }
      ]
    })
    mockApiService.useDemoData.mockResolvedValue({
      table: 'demo_table',
      columns: [
        { name: 'date', type: 'DATE' },
        { name: 'sales', type: 'DECIMAL' },
        { name: 'category', type: 'VARCHAR' }
      ]
    })
    mockApiService.translateQuery.mockResolvedValue({
      sql: 'SELECT date, SUM(revenue) FROM test_table GROUP BY date ORDER BY date'
    })
    mockApiService.executeSQL.mockResolvedValue({
      columns: ['date', 'total_revenue'],
      rows: [
        ['2023-01-01', 1000],
        ['2023-02-01', 2000],
        ['2023-03-01', 1500]
      ],
      row_count: 3,
      runtime_ms: 45
    })
    mockApiService.saveDashboard.mockResolvedValue({
      id: 'dashboard-1',
      name: 'Test Dashboard',
      question: 'monthly revenue',
      sql: 'SELECT date, SUM(revenue) FROM test_table GROUP BY date ORDER BY date',
      chartConfig: { type: 'line', x: 'date', y: 'total_revenue' },
      createdAt: '2023-01-01T00:00:00Z'
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render upload phase initially', async () => {
    render(<App />)
    
    expect(screen.getByText('Dashly')).toBeInTheDocument()
    expect(screen.getByText('Dashboard Auto-Designer')).toBeInTheDocument()
    
    // Should show upload widget
    await waitFor(() => {
      expect(screen.getByTestId('upload-widget')).toBeInTheDocument()
    })
  })

  it('should complete full user journey: upload → query → chart → save', async () => {
    render(<App />)
    
    // Step 1: Upload file
    const fileInput = screen.getByTestId('file-input')
    const testFile = new File(['test,data'], 'test.csv', { type: 'text/csv' })
    
    fireEvent.change(fileInput, { target: { files: [testFile] } })
    
    const uploadButton = screen.getByTestId('upload-button')
    fireEvent.click(uploadButton)
    
    // Wait for upload to complete and transition to query phase
    await waitFor(() => {
      expect(screen.getByText('Ask a Question')).toBeInTheDocument()
    })
    
    expect(mockApiService.uploadFile).toHaveBeenCalledWith(testFile)
    
    // Step 2: Enter natural language query
    const queryInput = screen.getByTestId('query-input')
    fireEvent.change(queryInput, { target: { value: 'monthly revenue' } })
    
    const generateButton = screen.getByTestId('generate-button')
    fireEvent.click(generateButton)
    
    // Wait for SQL modal to appear
    await waitFor(() => {
      expect(screen.getByTestId('sql-modal')).toBeInTheDocument()
    })
    
    expect(mockApiService.translateQuery).toHaveBeenCalledWith('monthly revenue')
    
    // Step 3: Execute SQL
    const runQueryButton = screen.getByTestId('run-query-button')
    fireEvent.click(runQueryButton)
    
    // Wait for chart to render
    await waitFor(() => {
      expect(screen.getByTestId('chart-renderer')).toBeInTheDocument()
    })
    
    expect(mockApiService.executeSQL).toHaveBeenCalledWith(
      'SELECT date, SUM(revenue) FROM test_table GROUP BY date ORDER BY date'
    )
    
    // Step 4: Save dashboard
    const saveDashboardButton = screen.getByText('Save Dashboard')
    fireEvent.click(saveDashboardButton)
    
    await waitFor(() => {
      expect(mockApiService.saveDashboard).toHaveBeenCalledWith({
        name: 'Test Dashboard',
        question: 'monthly revenue',
        sql: 'SELECT date, SUM(revenue) FROM test_table GROUP BY date ORDER BY date',
        chartConfig: { type: 'line', x: 'date', y: 'total_revenue' }
      })
    })
    
    // Should show success notification
    await waitFor(() => {
      expect(screen.getByText(/Dashboard "Test Dashboard" saved successfully/)).toBeInTheDocument()
    })
  })

  it('should handle demo data workflow', async () => {
    render(<App />)
    
    // Click demo data button
    const demoButton = screen.getByTestId('demo-data-button')
    fireEvent.click(demoButton)
    
    // Wait for transition to query phase
    await waitFor(() => {
      expect(screen.getByText('Ask a Question')).toBeInTheDocument()
    })
    
    expect(mockApiService.useDemoData).toHaveBeenCalled()
    
    // Should show table info
    expect(screen.getByText('Table: demo_table (3 columns)')).toBeInTheDocument()
  })

  it('should handle API errors gracefully', async () => {
    // Mock API error
    mockApiService.uploadFile.mockRejectedValue({
      message: 'Invalid file format',
      code: 'INVALID_FILE'
    })
    
    render(<App />)
    
    const fileInput = screen.getByTestId('file-input')
    const testFile = new File(['invalid'], 'test.csv', { type: 'text/csv' })
    
    fireEvent.change(fileInput, { target: { files: [testFile] } })
    
    // Wait for upload button to appear after file selection
    await waitFor(() => {
      expect(screen.getByTestId('upload-button')).toBeInTheDocument()
    })
    
    const uploadButton = screen.getByTestId('upload-button')
    fireEvent.click(uploadButton)
    
    // Should show error notification
    await waitFor(() => {
      expect(screen.getByText(/Upload failed: Invalid file format/)).toBeInTheDocument()
    })
    
    // Should remain in upload phase
    expect(screen.getByTestId('upload-widget')).toBeInTheDocument()
  })

  it('should load saved dashboards on initialization', async () => {
    const mockDashboards = [
      {
        id: 'dashboard-1',
        name: 'Revenue Dashboard',
        question: 'monthly revenue',
        sql: 'SELECT * FROM revenue',
        chartConfig: { type: 'line' as const },
        createdAt: '2023-01-01T00:00:00Z'
      }
    ]
    
    mockApiService.getDashboards.mockResolvedValue(mockDashboards)
    
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByText('Saved Dashboards')).toBeInTheDocument()
      expect(screen.getByText('Revenue Dashboard')).toBeInTheDocument()
    })
    
    expect(mockApiService.getDashboards).toHaveBeenCalled()
  })

  it('should handle dashboard loading', async () => {
    const mockDashboard = {
      id: 'dashboard-1',
      name: 'Revenue Dashboard',
      question: 'monthly revenue',
      sql: 'SELECT date, revenue FROM sales',
      chartConfig: { type: 'line' as const, x: 'date', y: 'revenue' },
      createdAt: '2023-01-01T00:00:00Z'
    }
    
    mockApiService.getDashboards.mockResolvedValue([mockDashboard])
    
    render(<App />)
    
    // Wait for dashboard to appear
    await waitFor(() => {
      expect(screen.getByText('Revenue Dashboard')).toBeInTheDocument()
    })
    
    // Click on dashboard card
    const dashboardCard = screen.getByTestId('dashboard-card-dashboard-1')
    fireEvent.click(dashboardCard)
    
    await waitFor(() => {
      expect(mockApiService.executeSQL).toHaveBeenCalledWith('SELECT date, revenue FROM sales')
    })
    
    // Should show success notification
    await waitFor(() => {
      expect(screen.getByText(/Loaded dashboard "Revenue Dashboard"/)).toBeInTheDocument()
    })
  })

  it('should handle new query reset', async () => {
    // First complete a query workflow
    mockApiService.useDemoData.mockResolvedValue({
      table: 'demo_table',
      columns: [{ name: 'date', type: 'DATE' }]
    })
    
    render(<App />)
    
    // Load demo data
    const demoButton = screen.getByTestId('demo-data-button')
    fireEvent.click(demoButton)
    
    await waitFor(() => {
      expect(screen.getByText('Ask a Question')).toBeInTheDocument()
    })
    
    // Simulate having results
    const queryInput = screen.getByTestId('query-input')
    fireEvent.change(queryInput, { target: { value: 'test query' } })
    
    const generateButton = screen.getByTestId('generate-button')
    fireEvent.click(generateButton)
    
    await waitFor(() => {
      expect(screen.getByTestId('sql-modal')).toBeInTheDocument()
    })
    
    const runQueryButton = screen.getByTestId('run-query-button')
    fireEvent.click(runQueryButton)
    
    await waitFor(() => {
      expect(screen.getByTestId('chart-renderer')).toBeInTheDocument()
    })
    
    // Click new query button
    const newQueryButton = screen.getByText('New Query')
    fireEvent.click(newQueryButton)
    
    // Should reset the query input
    expect(screen.getByTestId('query-input')).toHaveValue('')
    
    // Should not show chart renderer anymore
    expect(screen.queryByTestId('chart-renderer')).not.toBeInTheDocument()
  })

  it('should show loading states during operations', async () => {
    // Mock slow API response
    mockApiService.uploadFile.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        table: 'test_table',
        columns: []
      }), 100))
    )
    
    render(<App />)
    
    const fileInput = screen.getByTestId('file-input')
    const testFile = new File(['test'], 'test.csv', { type: 'text/csv' })
    
    fireEvent.change(fileInput, { target: { files: [testFile] } })
    
    const uploadButton = screen.getByTestId('upload-button')
    fireEvent.click(uploadButton)
    
    // Should show loading overlay
    expect(screen.getByText('Processing...')).toBeInTheDocument()
    
    await waitFor(() => {
      expect(screen.queryByText('Processing...')).not.toBeInTheDocument()
    })
  })

  it('should handle toast notification dismissal', async () => {
    render(<App />)
    
    // Trigger an error to show toast
    mockApiService.useDemoData.mockRejectedValue({
      message: 'Test error',
      code: 'TEST_ERROR'
    })
    
    const demoButton = screen.getByTestId('demo-data-button')
    fireEvent.click(demoButton)
    
    // Wait for error toast
    await waitFor(() => {
      expect(screen.getByText(/Failed to load demo data: Test error/)).toBeInTheDocument()
    })
    
    // Find and click dismiss button
    const dismissButton = screen.getByTestId('toast-dismiss')
    fireEvent.click(dismissButton)
    
    // Toast should be removed
    await waitFor(() => {
      expect(screen.queryByText(/Failed to load demo data: Test error/)).not.toBeInTheDocument()
    })
  })
})