import React, { useState } from 'react'
import { LoadingSpinner, ToastContainer } from './components'
import { selectChartType } from './utils'
import { ToastNotification, ChartData } from './types'
import { generateId } from './utils'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [notifications, setNotifications] = useState<ToastNotification[]>([])

  const addNotification = (type: 'success' | 'error' | 'info', message: string) => {
    const notification: ToastNotification = {
      id: generateId(),
      type,
      message,
      duration: 5000
    }
    setNotifications(prev => [...prev, notification])
  }

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    // Demo the chart selector with sample data
    const sampleData: ChartData = {
      columns: ['date', 'revenue', 'region'],
      rows: [
        ['2023-01-01', 1000, 'North'],
        ['2023-02-01', 2000, 'South'],
        ['2023-03-01', 1500, 'East']
      ]
    }
    
    const chartConfig = selectChartType(sampleData)
    console.log('Query:', query)
    console.log('Selected chart config:', chartConfig)
    
    // Simulate API delay
    setTimeout(() => {
      setLoading(false)
      addNotification('success', `Generated ${chartConfig.type} chart for your query!`)
    }, 1500)
  }

  const testErrorToast = () => {
    addNotification('error', 'This is a test error message')
  }

  const testInfoToast = () => {
    addNotification('info', 'This is a test info message')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Dashly</h1>
          <p className="text-lg text-gray-600">Dashboard Auto-Designer</p>
        </header>

        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="mb-8">
            <div className="flex gap-4">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about your data (e.g., 'monthly revenue by region last 12 months')"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading && <LoadingSpinner size="sm" />}
                {loading ? 'Processing...' : 'Generate Dashboard'}
              </button>
            </div>
          </form>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Dashboard Preview</h2>
            <div className="text-center text-gray-500 py-12">
              Enter a query above to generate your dashboard
            </div>
          </div>

          {/* Demo buttons for testing components */}
          <div className="mt-8 flex gap-4 justify-center">
            <button
              onClick={testErrorToast}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Test Error Toast
            </button>
            <button
              onClick={testInfoToast}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Test Info Toast
            </button>
          </div>
        </div>
      </div>

      <ToastContainer 
        notifications={notifications} 
        onDismiss={removeNotification} 
      />
    </div>
  )
}

export default App