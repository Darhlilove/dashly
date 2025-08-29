import React, { useState } from 'react';


interface SaveDashboardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string) => void;
  isLoading?: boolean;
}

const SaveDashboardModal: React.FC<SaveDashboardModalProps> = ({
  isOpen,
  onClose,
  onSave,
  isLoading = false,
}) => {
  const [dashboardName, setDashboardName] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!dashboardName.trim()) {
      setError('Dashboard name is required');
      return;
    }

    if (dashboardName.trim().length < 3) {
      setError('Dashboard name must be at least 3 characters');
      return;
    }

    setError('');
    onSave(dashboardName.trim());
  };

  const handleClose = () => {
    setDashboardName('');
    setError('');
    onClose();
  };

  // Reset form when modal opens/closes
  React.useEffect(() => {
    if (!isOpen) {
      setDashboardName('');
      setError('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-modal-title"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 id="save-modal-title" className="text-lg font-semibold text-gray-900">
              Save Dashboard
            </h2>
            <button
              onClick={handleClose}
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md transition-colors disabled:opacity-50 p-1"
              aria-label="Close modal"
            >
              <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="dashboardName" className="block text-sm font-medium text-gray-700 mb-2">
                Dashboard Name
              </label>
              <input
                type="text"
                id="dashboardName"
                value={dashboardName}
                onChange={(e) => setDashboardName(e.target.value)}
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-sm sm:text-base"
                placeholder="Enter dashboard name..."
                maxLength={100}
                autoFocus
                aria-describedby={error ? "name-error" : "name-help"}
              />
              <p id="name-help" className="mt-1 text-xs text-gray-500">
                Choose a descriptive name for your dashboard
              </p>
              {error && (
                <p id="name-error" className="mt-1 text-sm text-red-600" role="alert">
                  {error}
                </p>
              )}
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors order-2 sm:order-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !dashboardName.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center order-1 sm:order-2"
                aria-describedby={isLoading ? "saving-status" : undefined}
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Saving...</span>
                  </>
                ) : (
                  'Save Dashboard'
                )}
              </button>
              {isLoading && (
                <span id="saving-status" className="sr-only">
                  Saving dashboard, please wait
                </span>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SaveDashboardModal;