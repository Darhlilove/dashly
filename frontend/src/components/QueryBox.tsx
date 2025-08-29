import React, { useState } from 'react';
import { LoadingSpinner } from './';
import { apiService } from '../services/api';
import { ApiError } from '../types/api';

interface QueryBoxProps {
  onSQLGenerated: (sql: string, query: string) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

const QueryBox: React.FC<QueryBoxProps> = ({ 
  onSQLGenerated, 
  onError, 
  disabled = false 
}) => {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || isLoading || disabled) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiService.translateQuery(query.trim());
      onSQLGenerated(response.sql, query.trim());
      // Don't clear the query so user can see what they asked
    } catch (error) {
      const apiError = error as ApiError;
      onError(apiError.message || 'Failed to translate query to SQL');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Allow Ctrl+Enter or Cmd+Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const isSubmitDisabled = !query.trim() || isLoading || disabled;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
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
            placeholder="e.g., 'Show monthly revenue by region for the last 12 months' or 'What are the top 5 products by sales?'"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors"
            rows={3}
            disabled={isLoading || disabled}
            aria-describedby="query-help"
          />
          <p id="query-help" className="mt-2 text-sm text-gray-500">
            Describe what you want to see in plain English. Press Ctrl+Enter to generate.
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {isLoading && <LoadingSpinner size="sm" />}
            {isLoading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </form>

      {query.trim() && !isLoading && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <strong>Your question:</strong> {query}
          </p>
        </div>
      )}
    </div>
  );
};

export default QueryBox;