import React, { Suspense } from 'react';
import { UploadWidget, LoadingSpinner } from './';
import { Dashboard } from '../types';

// Lazy load DashboardGrid for upload phase
const DashboardGrid = React.lazy(() => import('./DashboardGrid'));

interface UploadPhaseProps {
  onFileUpload: (file: File) => void;
  onDemoData: () => void;
  isLoading: boolean;
  error: string | null;
  savedDashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
}

const UploadPhase: React.FC<UploadPhaseProps> = ({
  onFileUpload,
  onDemoData,
  isLoading,
  error,
  savedDashboards,
  onLoadDashboard,
}) => {
  return (
    <div className="space-y-6 sm:space-y-8">
      <section aria-labelledby="upload-section">
        <div className="text-center mb-6">
          <h2 id="upload-section" className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
            Get Started
          </h2>
          <p className="text-sm sm:text-base text-gray-600">
            Upload your CSV data or use demo data to create dashboards
          </p>
        </div>
        <UploadWidget
          onFileUpload={onFileUpload}
          onDemoData={onDemoData}
          isLoading={isLoading}
          error={error}
        />
      </section>
      
      {/* Show saved dashboards even in upload phase */}
      {savedDashboards.length > 0 && (
        <section aria-labelledby="saved-dashboards-upload">
          <h2 id="saved-dashboards-upload" className="text-xl sm:text-2xl font-semibold mb-4">
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

export default UploadPhase;