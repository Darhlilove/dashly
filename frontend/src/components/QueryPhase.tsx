import React, { Suspense } from 'react';
import { QueryBox, LoadingSpinner } from './';
import { Dashboard, ChartConfig } from '../types';

// Lazy load heavy components
const ChartRenderer = React.lazy(() => import('./ChartRenderer'));
const DashboardGrid = React.lazy(() => import('./DashboardGrid'));

interface QueryPhaseProps {
  currentQuery: string;
  isLoading: boolean;
  onQuery: (query: string) => void;
  onNewQuery: () => void;
  queryResults: any;
  currentChart: ChartConfig | null;
  onSaveDashboard: (name: string) => void;
  savedDashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
}

const QueryPhase: React.FC<QueryPhaseProps> = ({
  currentQuery,
  isLoading,
  onQuery,
  onNewQuery,
  queryResults,
  currentChart,
  onSaveDashboard,
  savedDashboards,
  onLoadDashboard,
}) => {
  return (
    <div className="space-y-6 sm:space-y-8">
      <section aria-labelledby="query-section">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
          <h2 id="query-section" className="text-xl sm:text-2xl font-semibold">
            Ask a Question
          </h2>
          <button
            onClick={onNewQuery}
            className="px-4 py-2 text-blue-600 hover:text-blue-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md transition-colors self-start sm:self-auto"
            aria-label="Start a new query"
          >
            New Query
          </button>
        </div>

        <QueryBox
          onSubmit={onQuery}
          isLoading={isLoading}
          placeholder="Ask a question about your data (e.g., 'monthly revenue by region last 12 months')"
          value={currentQuery}
        />
      </section>

      {/* Show current results */}
      {queryResults && currentChart && (
        <section aria-labelledby="results-section">
          <h2 id="results-section" className="sr-only">Query Results</h2>
          <Suspense fallback={
            <div className="flex items-center justify-center p-8">
              <LoadingSpinner size="lg" />
              <span className="ml-3 text-gray-600">Loading chart...</span>
            </div>
          }>
            <ChartRenderer
              data={{
                columns: queryResults.columns,
                rows: queryResults.rows
              }}
              config={currentChart}
              onSaveDashboard={onSaveDashboard}
              isLoading={isLoading}
            />
          </Suspense>
        </section>
      )}

      {/* Show saved dashboards */}
      {savedDashboards.length > 0 && (
        <section aria-labelledby="saved-dashboards-query">
          <h2 id="saved-dashboards-query" className="text-xl sm:text-2xl font-semibold mb-4">
            Saved Dashboards
          </h2>
          <Suspense fallback={
            <div className="flex items-center justify-center p-4">
              <LoadingSpinner size="md" />
              <span className="ml-3 text-gray-600">Loading dashboards...</span>
            </div>
          }>
            <DashboardGrid
              dashboards={savedDashboards}
              onLoadDashboard={onLoadDashboard}
              isLoading={isLoading}
            />
          </Suspense>
        </section>
      )}
    </div>
  );
};

export default QueryPhase;