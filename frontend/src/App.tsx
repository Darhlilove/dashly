import React, { useState, useEffect, useCallback } from 'react'
import {
  UploadWidget,
  QueryBox,
  SQLPreviewModal,
  ChartRenderer,
  DashboardGrid,
  ToastContainer,
  LoadingSpinner
} from './components'
import { 
  AppState, 
  ToastNotification, 
  Dashboard,
  UploadResponse,
  ExecuteResponse,
  ApiError
} from './types'
import { apiService } from './services/api'
import { selectChartType } from './utils'
import { generateId } from './utils'

// Initial application state
const initialState: AppState = {
  uploadStatus: 'idle',
  tableInfo: null,
  currentQuery: '',
  currentSQL: '',
  queryResults: null,
  currentChart: null,
  savedDashboards: [],
  showSQLModal: false,
  isLoading: false,
  error: null
}

function App() {
  const [state, setState] = useState<AppState>(initialState)
  const [notifications, setNotifications] = useState<ToastNotification[]>([])

  // Toast notification management
  const addNotification = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    const notification: ToastNotification = {
      id: generateId(),
      type,
      message,
      duration: 5000
    }
    setNotifications(prev => [...prev, notification])
  }, [])

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  // Load saved dashboards on app initialization
  useEffect(() => {
    const loadDashboards = async () => {
      try {
        const dashboards = await apiService.getDashboards()
        setState(prev => ({ ...prev, savedDashboards: dashboards }))
      } catch (error) {
        console.error('Failed to load dashboards:', error)
        // Don't show error toast for initial load failure
      }
    }

    loadDashboards()
  }, [])

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    setState(prev => ({ ...prev, uploadStatus: 'uploading', isLoading: true, error: null }))
    
    try {
      const response = await apiService.uploadFile(file)
      setState(prev => ({ 
        ...prev, 
        uploadStatus: 'completed',
        tableInfo: response,
        isLoading: false
      }))
      addNotification('success', `Successfully uploaded ${file.name}`)
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ 
        ...prev, 
        uploadStatus: 'error',
        error: apiError.message,
        isLoading: false
      }))
      addNotification('error', `Upload failed: ${apiError.message}`)
    }
  }

  // Handle demo data selection
  const handleDemoData = async () => {
    setState(prev => ({ ...prev, uploadStatus: 'uploading', isLoading: true, error: null }))
    
    try {
      const response = await apiService.useDemoData()
      setState(prev => ({ 
        ...prev, 
        uploadStatus: 'completed',
        tableInfo: response,
        isLoading: false
      }))
      addNotification('success', 'Demo data loaded successfully')
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ 
        ...prev, 
        uploadStatus: 'error',
        error: apiError.message,
        isLoading: false
      }))
      addNotification('error', `Failed to load demo data: ${apiError.message}`)
    }
  }

  // Handle natural language query
  const handleQuery = async (query: string) => {
    setState(prev => ({ ...prev, currentQuery: query, isLoading: true, error: null }))
    
    try {
      const response = await apiService.translateQuery(query)
      setState(prev => ({ 
        ...prev, 
        currentSQL: response.sql,
        showSQLModal: true,
        isLoading: false
      }))
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ 
        ...prev, 
        error: apiError.message,
        isLoading: false
      }))
      addNotification('error', `Query translation failed: ${apiError.message}`)
    }
  }

  // Handle SQL execution
  const handleSQLExecution = async (sql: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))
    
    try {
      const response = await apiService.executeSQL(sql)
      const chartConfig = selectChartType({ columns: response.columns, rows: response.rows })
      
      setState(prev => ({ 
        ...prev, 
        queryResults: response,
        currentChart: chartConfig,
        showSQLModal: false,
        isLoading: false
      }))
      addNotification('success', `Query executed successfully (${response.row_count} rows, ${response.runtime_ms}ms)`)
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ 
        ...prev, 
        error: apiError.message,
        isLoading: false
      }))
      addNotification('error', `Query execution failed: ${apiError.message}`)
    }
  }

  // Handle dashboard saving
  const handleSaveDashboard = async (name: string) => {
    if (!state.currentQuery || !state.currentSQL || !state.currentChart) {
      addNotification('error', 'No dashboard to save')
      return
    }

    setState(prev => ({ ...prev, isLoading: true }))
    
    try {
      const dashboard = await apiService.saveDashboard({
        name,
        question: state.currentQuery,
        sql: state.currentSQL,
        chartConfig: state.currentChart
      })
      
      setState(prev => ({ 
        ...prev, 
        savedDashboards: [...prev.savedDashboards, dashboard],
        isLoading: false
      }))
      addNotification('success', `Dashboard "${name}" saved successfully`)
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ ...prev, isLoading: false }))
      addNotification('error', `Failed to save dashboard: ${apiError.message}`)
    }
  }

  // Handle loading saved dashboard
  const handleLoadDashboard = async (dashboard: Dashboard) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))
    
    try {
      const response = await apiService.executeSQL(dashboard.sql)
      
      setState(prev => ({ 
        ...prev, 
        currentQuery: dashboard.question,
        currentSQL: dashboard.sql,
        queryResults: response,
        currentChart: dashboard.chartConfig,
        isLoading: false
      }))
      addNotification('success', `Loaded dashboard "${dashboard.name}"`)
    } catch (error) {
      const apiError = error as ApiError
      setState(prev => ({ 
        ...prev, 
        error: apiError.message,
        isLoading: false
      }))
      addNotification('error', `Failed to load dashboard: ${apiError.message}`)
    }
  }

  // Handle modal close
  const handleModalClose = () => {
    setState(prev => ({ ...prev, showSQLModal: false }))
  }

  // Handle new query (reset current results)
  const handleNewQuery = () => {
    setState(prev => ({ 
      ...prev, 
      currentQuery: '',
      currentSQL: '',
      queryResults: null,
      currentChart: null,
      error: null
    }))
  }

  // Determine current phase based on application state
  const currentPhase = state.uploadStatus === 'completed' ? 'query' : 'upload'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Dashly</h1>
          <p className="text-lg text-gray-600">Dashboard Auto-Designer</p>
          {state.tableInfo && (
            <p className="text-sm text-gray-500 mt-2">
              Table: {state.tableInfo.table} ({state.tableInfo.columns.length} columns)
            </p>
          )}
        </header>

        <div className="max-w-4xl mx-auto">
          {/* Upload Phase */}
          {currentPhase === 'upload' && (
            <div className="space-y-8">
              <UploadWidget
                onFileUpload={handleFileUpload}
                onDemoData={handleDemoData}
                isLoading={state.isLoading}
                error={state.error}
              />
              
              {/* Show saved dashboards even in upload phase */}
              {state.savedDashboards.length > 0 && (
                <div>
                  <h2 className="text-2xl font-semibold mb-4">Saved Dashboards</h2>
                  <DashboardGrid
                    dashboards={state.savedDashboards}
                    onLoadDashboard={handleLoadDashboard}
                    isLoading={state.isLoading}
                  />
                </div>
              )}
            </div>
          )}

          {/* Query Phase */}
          {currentPhase === 'query' && (
            <div className="space-y-8">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-semibold">Ask a Question</h2>
                <button
                  onClick={handleNewQuery}
                  className="px-4 py-2 text-blue-600 hover:text-blue-800 font-medium"
                >
                  New Query
                </button>
              </div>

              <QueryBox
                onSubmit={handleQuery}
                isLoading={state.isLoading}
                placeholder="Ask a question about your data (e.g., 'monthly revenue by region last 12 months')"
                value={state.currentQuery}
              />

              {/* Show current results */}
              {state.queryResults && state.currentChart && (
                <ChartRenderer
                  data={{
                    columns: state.queryResults.columns,
                    rows: state.queryResults.rows
                  }}
                  config={state.currentChart}
                  onSaveDashboard={handleSaveDashboard}
                  isLoading={state.isLoading}
                />
              )}

              {/* Show saved dashboards */}
              {state.savedDashboards.length > 0 && (
                <div>
                  <h2 className="text-2xl font-semibold mb-4">Saved Dashboards</h2>
                  <DashboardGrid
                    dashboards={state.savedDashboards}
                    onLoadDashboard={handleLoadDashboard}
                    isLoading={state.isLoading}
                  />
                </div>
              )}
            </div>
          )}

          {/* Global loading overlay */}
          {state.isLoading && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 flex items-center gap-4">
                <LoadingSpinner size="md" />
                <span className="text-gray-700">Processing...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SQL Preview Modal */}
      {state.showSQLModal && (
        <SQLPreviewModal
          sql={state.currentSQL}
          onExecute={handleSQLExecution}
          onClose={handleModalClose}
          isLoading={state.isLoading}
        />
      )}

      {/* Toast Notifications */}
      <ToastContainer 
        notifications={notifications} 
        onDismiss={removeNotification} 
      />
    </div>
  )
}

export default App