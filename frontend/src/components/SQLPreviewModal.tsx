// SQLPreviewModal component for SQL review and execution

import React, { useState, useEffect, useRef } from "react";
import LoadingSpinner from "./LoadingSpinner";

interface SQLPreviewModalProps {
  sql: string;
  onExecute: (sql: string) => void;
  onClose: () => void;
  isLoading: boolean;
}

const SQLPreviewModal: React.FC<SQLPreviewModalProps> = ({
  sql,
  onExecute,
  onClose,
  isLoading,
}) => {
  const [editedSQL, setEditedSQL] = useState(sql);
  const modalRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Update edited SQL when prop changes
  useEffect(() => {
    setEditedSQL(sql);
  }, [sql]);

  // Focus textarea when modal opens
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  // Handle click outside modal to close
  const handleOverlayClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  // Execute SQL query
  const handleRunQuery = () => {
    const trimmedSQL = editedSQL.trim();
    if (!trimmedSQL) {
      return;
    }

    onExecute(trimmedSQL);
  };

  // Handle SQL textarea change
  const handleSQLChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedSQL(event.target.value);
  };

  // Auto-resize textarea based on content
  const handleTextareaResize = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  useEffect(() => {
    handleTextareaResize();
  }, [editedSQL]);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleOverlayClick}
      data-testid="sql-modal"
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="bg-white border border-gray-300 max-w-4xl w-full max-h-[90vh] flex flex-col mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200">
          <h2
            id="modal-title"
            className="text-lg sm:text-xl font-semibold text-gray-900"
          >
            Review Generated SQL
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors p-1"
            aria-label="Close modal"
          >
            <svg
              className="w-5 h-5 sm:w-6 sm:h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-4 sm:p-6 overflow-hidden">
          <div className="mb-4">
            <label
              htmlFor="sql-textarea"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              SQL Query (editable)
            </label>
            <textarea
              ref={textareaRef}
              id="sql-textarea"
              value={editedSQL}
              onChange={handleSQLChange}
              onInput={handleTextareaResize}
              className="w-full min-h-[150px] sm:min-h-[200px] max-h-[300px] sm:max-h-[400px] p-3 sm:p-4 border border-gray-300 font-mono text-xs sm:text-sm resize-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="Enter your SQL query here..."
              spellCheck={false}
              aria-describedby="sql-help"
            />
          </div>

          <div id="sql-help" className="text-xs text-gray-500 mb-4">
            <p>
              <strong>Note:</strong> Only SELECT statements are allowed. The
              query will be validated before execution.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3 p-4 sm:p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors order-2 sm:order-1"
          >
            Cancel
          </button>
          <button
            onClick={handleRunQuery}
            disabled={isLoading || !editedSQL.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 order-1 sm:order-2"
            data-testid="run-query-button"
            aria-describedby={isLoading ? "query-running-status" : undefined}
          >
            {isLoading && <LoadingSpinner size="sm" />}
            <span>{isLoading ? "Running Query..." : "Run Query"}</span>
          </button>
          {isLoading && (
            <span id="query-running-status" className="sr-only">
              Executing SQL query, please wait
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default SQLPreviewModal;
