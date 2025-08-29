import React, { useState, useRef, useCallback } from 'react';

import LoadingSpinner from './LoadingSpinner';

interface UploadWidgetProps {
  onFileUpload: (file: File) => void;
  onDemoData: () => void;
  isLoading: boolean;
  error: string | null;
}

const UploadWidget: React.FC<UploadWidgetProps> = ({
  onFileUpload,
  onDemoData,
  isLoading,
  error,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((file: File) => {
    // Validate file type
    if (!file.type.includes('csv') && !file.name.toLowerCase().endsWith('.csv')) {
      // Error handling is now done by parent component
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      // Error handling is now done by parent component
      return;
    }

    setSelectedFile(file);
  }, []);

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleUploadFile = () => {
    if (!selectedFile) return;
    onFileUpload(selectedFile);
  };

  const handleUseDemoData = () => {
    onDemoData();
  };

  const handleBrowseFiles = () => {
    fileInputRef.current?.click();
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4 sm:p-6" data-testid="upload-widget">

      {/* File Upload Area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-4 sm:p-6 lg:p-8 text-center transition-colors
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${isLoading ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-testid="upload-dropzone"
        role="region"
        aria-label="File upload area"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileInputChange}
          className="hidden"
          tabIndex={-1}
          data-testid="file-input"
        />

        {isLoading ? (
          <div className="flex flex-col items-center">
            <LoadingSpinner size="lg" className="mb-4" />
            <p className="text-sm sm:text-base text-gray-600">
              {selectedFile ? 'Uploading file...' : 'Loading demo data...'}
            </p>
          </div>
        ) : selectedFile ? (
          <div className="flex flex-col items-center">
            <div className="flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 bg-green-100 rounded-full mb-4">
              <svg
                className="w-6 h-6 sm:w-8 sm:h-8 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-base sm:text-lg font-medium text-gray-900 mb-2 text-center">
              {selectedFile.name}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:space-x-3 w-full sm:w-auto">
              <button
                onClick={handleUploadFile}
                className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
                data-testid="upload-button"
                aria-describedby="upload-help"
              >
                Upload File
              </button>
              <button
                onClick={clearSelectedFile}
                className="px-4 sm:px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors font-medium"
                data-testid="clear-file-button"
                aria-label="Clear selected file"
              >
                Clear
              </button>
            </div>
            <p id="upload-help" className="sr-only">
              Click Upload File to process your CSV data
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 bg-gray-100 rounded-full mb-4">
              <svg
                className="w-6 h-6 sm:w-8 sm:h-8 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <p className="text-base sm:text-lg font-medium text-gray-900 mb-2 text-center">
              Drop your CSV file here
            </p>
            <p className="text-sm text-gray-500 mb-4 text-center">
              or click to browse files
            </p>
            <button
              onClick={handleBrowseFiles}
              className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
              data-testid="browse-files-button"
              aria-describedby="file-requirements"
            >
              Browse Files
            </button>
            <p id="file-requirements" className="text-xs text-gray-500 mt-2 text-center">
              CSV files up to 10MB supported
            </p>
          </div>
        )}
      </div>

      {/* Demo Data Section */}
      <div className="mt-6 sm:mt-8 text-center">
        <div className="relative">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">or</span>
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={handleUseDemoData}
            disabled={isLoading}
            className="px-6 sm:px-8 py-2 sm:py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="demo-data-button"
            aria-describedby="demo-data-description"
          >
            Use Demo Data
          </button>
          <p id="demo-data-description" className="text-xs text-gray-500 mt-2">
            Try dashly with sample sales data
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div 
            className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg"
            role="alert"
            aria-live="polite"
          >
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadWidget;