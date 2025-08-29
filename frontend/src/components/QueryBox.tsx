import React, { useState } from 'react';
import { LoadingSpinner } from './';

interface QueryBoxProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  placeholder?: string;
  value?: string;
}

const QueryBox: React.FC<QueryBoxProps> = ({ 
  onSubmit,
  isLoading,
  placeholder = "Ask a question about your data...",
  value = ""
}) => {
  const [query, setQuery] = useState(value);

  // Update internal state when value prop changes
  React.useEffect(() => {
    setQuery(value);
  }, [value]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || isLoading) {
      return;
    }

    onSubmit(query.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Allow Ctrl+Enter or Cmd+Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const isSubmitDisabled = !query.trim() || isLoading;

  return (
    <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
      <h2 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4">
        Ask a Question About Your Data
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="query-input" className="sr-only">
            Natural language query
          </label>
          <textarea
            id="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full px-3 sm:px-4 py-2 sm:py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors text-sm sm:text-base"
            rows={3}
            disabled={isLoading}
            aria-describedby="query-help"
            data-testid="query-input"
          />
          <p id="query-help" className="mt-2 text-xs sm:text-sm text-gray-500">
            Describe what you want to see in plain English. Press Ctrl+Enter to generate.
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm sm:text-base"
            data-testid="generate-button"
            aria-describedby={isLoading ? "generating-status" : undefined}
          >
            {isLoading && <LoadingSpinner size="sm" />}
            <span>{isLoading ? 'Generating...' : 'Generate'}</span>
          </button>
          {isLoading && (
            <span id="generating-status" className="sr-only">
              Generating SQL query from your question
            </span>
          )}
        </div>
      </form>

      {query.trim() && !isLoading && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg" role="status" aria-live="polite">
          <p className="text-xs sm:text-sm text-gray-600">
            <strong>Your question:</strong> {query}
          </p>
        </div>
      )}
    </div>
  );
};

export default QueryBox;