import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UploadWidget from '../UploadWidget';
import { apiService } from '../../services/api';
import { UploadResponse } from '../../types/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  apiService: {
    uploadFile: vi.fn(),
    useDemoData: vi.fn(),
  },
}));

const mockApiService = apiService as any;

describe('UploadWidget', () => {
  const mockOnUploadSuccess = vi.fn();
  const mockOnUploadError = vi.fn();

  const mockUploadResponse: UploadResponse = {
    table: 'test_table',
    columns: [
      { name: 'id', type: 'INTEGER' },
      { name: 'name', type: 'VARCHAR' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderUploadWidget = () => {
    return render(
      <UploadWidget
        onUploadSuccess={mockOnUploadSuccess}
        onUploadError={mockOnUploadError}
      />
    );
  };

  describe('Initial Render', () => {
    it('renders the upload widget with correct title and description', () => {
      renderUploadWidget();

      expect(screen.getByText('Welcome to dashly')).toBeInTheDocument();
      expect(
        screen.getByText('Upload your CSV data or use demo data to get started')
      ).toBeInTheDocument();
    });

    it('renders the drag and drop area', () => {
      renderUploadWidget();

      expect(screen.getByTestId('upload-dropzone')).toBeInTheDocument();
      expect(screen.getByText('Drop your CSV file here')).toBeInTheDocument();
      expect(screen.getByText('or click to browse files')).toBeInTheDocument();
    });

    it('renders the browse files button', () => {
      renderUploadWidget();

      expect(screen.getByTestId('browse-files-button')).toBeInTheDocument();
    });

    it('renders the demo data button', () => {
      renderUploadWidget();

      expect(screen.getByTestId('demo-data-button')).toBeInTheDocument();
      expect(screen.getByText('Use Demo Data')).toBeInTheDocument();
    });
  });

  describe('File Selection', () => {
    it('handles file selection via file input', async () => {
      const user = userEvent.setup();
      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      expect(screen.getByText('test.csv')).toBeInTheDocument();
      expect(screen.getByTestId('upload-button')).toBeInTheDocument();
      expect(screen.getByTestId('clear-file-button')).toBeInTheDocument();
    });

    it('handles file selection via browse button click', async () => {
      const user = userEvent.setup();
      renderUploadWidget();

      const browseButton = screen.getByTestId('browse-files-button');
      const fileInput = screen.getByTestId('file-input');

      // Mock the click event on file input
      const clickSpy = vi.spyOn(fileInput, 'click');
      await user.click(browseButton);

      expect(clickSpy).toHaveBeenCalled();
    });

    it('validates file type and shows error for non-CSV files', async () => {
      renderUploadWidget();

      const file = new File(['test data'], 'test.txt', {
        type: 'text/plain',
      });

      const fileInput = screen.getByTestId('file-input');
      
      // Trigger the file input change event directly
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      
      fireEvent.change(fileInput);

      expect(mockOnUploadError).toHaveBeenCalledWith('Please select a CSV file');
    });

    it('validates file size and shows error for large files', async () => {
      const user = userEvent.setup();
      renderUploadWidget();

      // Create a file larger than 10MB
      const largeContent = 'x'.repeat(11 * 1024 * 1024);
      const file = new File([largeContent], 'large.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      expect(mockOnUploadError).toHaveBeenCalledWith(
        'File size must be less than 10MB'
      );
    });

    it('clears selected file when clear button is clicked', async () => {
      const user = userEvent.setup();
      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      expect(screen.getByText('test.csv')).toBeInTheDocument();

      const clearButton = screen.getByTestId('clear-file-button');
      await user.click(clearButton);

      expect(screen.queryByText('test.csv')).not.toBeInTheDocument();
      expect(screen.getByText('Drop your CSV file here')).toBeInTheDocument();
    });
  });

  describe('Drag and Drop', () => {
    it('handles drag over events', () => {
      renderUploadWidget();

      const dropzone = screen.getByTestId('upload-dropzone');
      
      fireEvent.dragOver(dropzone);
      
      expect(dropzone).toHaveClass('border-blue-400', 'bg-blue-50');
    });

    it('handles drag leave events', () => {
      renderUploadWidget();

      const dropzone = screen.getByTestId('upload-dropzone');
      
      fireEvent.dragOver(dropzone);
      fireEvent.dragLeave(dropzone);
      
      expect(dropzone).not.toHaveClass('border-blue-400', 'bg-blue-50');
    });

    it('handles file drop', () => {
      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const dropzone = screen.getByTestId('upload-dropzone');
      
      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [file],
        },
      });

      expect(screen.getByText('test.csv')).toBeInTheDocument();
    });
  });

  describe('File Upload', () => {
    it('successfully uploads a file', async () => {
      const user = userEvent.setup();
      
      // Create a promise that we can control
      let resolveUpload: (value: any) => void;
      const uploadPromise = new Promise((resolve) => {
        resolveUpload = resolve;
      });
      mockApiService.uploadFile.mockReturnValue(uploadPromise);

      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      const uploadButton = screen.getByTestId('upload-button');
      await user.click(uploadButton);

      // Check loading state appears
      expect(screen.getByText('Uploading file...')).toBeInTheDocument();

      // Resolve the upload
      resolveUpload!(mockUploadResponse);

      await waitFor(() => {
        expect(mockApiService.uploadFile).toHaveBeenCalledWith(file);
        expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockUploadResponse);
      });
    });

    it('handles upload error', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Upload failed';
      mockApiService.uploadFile.mockRejectedValue({ message: errorMessage });

      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      const uploadButton = screen.getByTestId('upload-button');
      await user.click(uploadButton);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith(errorMessage);
      });
    });

    it('shows loading state during upload', async () => {
      const user = userEvent.setup();
      let resolveUpload: (value: any) => void;
      const uploadPromise = new Promise((resolve) => {
        resolveUpload = resolve;
      });
      mockApiService.uploadFile.mockReturnValue(uploadPromise);

      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      const uploadButton = screen.getByTestId('upload-button');
      await user.click(uploadButton);

      expect(screen.getByText('Uploading file...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument();

      // Resolve the upload
      resolveUpload!(mockUploadResponse);

      await waitFor(() => {
        expect(screen.queryByText('Uploading file...')).not.toBeInTheDocument();
      });
    });
  });

  describe('Demo Data', () => {
    it('successfully loads demo data', async () => {
      const user = userEvent.setup();
      
      // Create a promise that we can control
      let resolveDemoData: (value: any) => void;
      const demoDataPromise = new Promise((resolve) => {
        resolveDemoData = resolve;
      });
      mockApiService.useDemoData.mockReturnValue(demoDataPromise);

      renderUploadWidget();

      const demoButton = screen.getByTestId('demo-data-button');
      await user.click(demoButton);

      // Check loading state appears
      expect(screen.getByText('Loading demo data...')).toBeInTheDocument();

      // Resolve the demo data loading
      resolveDemoData!(mockUploadResponse);

      await waitFor(() => {
        expect(mockApiService.useDemoData).toHaveBeenCalled();
        expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockUploadResponse);
      });
    });

    it('handles demo data loading error', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Failed to load demo data';
      mockApiService.useDemoData.mockRejectedValue({ message: errorMessage });

      renderUploadWidget();

      const demoButton = screen.getByTestId('demo-data-button');
      await user.click(demoButton);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith(errorMessage);
      });
    });

    it('shows loading state during demo data loading', async () => {
      const user = userEvent.setup();
      let resolveDemoData: (value: any) => void;
      const demoDataPromise = new Promise((resolve) => {
        resolveDemoData = resolve;
      });
      mockApiService.useDemoData.mockReturnValue(demoDataPromise);

      renderUploadWidget();

      const demoButton = screen.getByTestId('demo-data-button');
      await user.click(demoButton);

      expect(screen.getByText('Loading demo data...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(demoButton).toBeDisabled();

      // Resolve the demo data loading
      resolveDemoData!(mockUploadResponse);

      await waitFor(() => {
        expect(screen.queryByText('Loading demo data...')).not.toBeInTheDocument();
        expect(demoButton).not.toBeDisabled();
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API errors without message property', async () => {
      const user = userEvent.setup();
      mockApiService.uploadFile.mockRejectedValue({});

      renderUploadWidget();

      const file = new File(['test,data\n1,hello'], 'test.csv', {
        type: 'text/csv',
      });

      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, file);

      const uploadButton = screen.getByTestId('upload-button');
      await user.click(uploadButton);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith('Failed to upload file');
      });
    });

    it('handles demo data API errors without message property', async () => {
      const user = userEvent.setup();
      mockApiService.useDemoData.mockRejectedValue({});

      renderUploadWidget();

      const demoButton = screen.getByTestId('demo-data-button');
      await user.click(demoButton);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith('Failed to load demo data');
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      renderUploadWidget();

      const fileInput = screen.getByTestId('file-input');
      expect(fileInput).toHaveAttribute('accept', '.csv');

      const loadingSpinner = screen.queryByRole('status');
      if (loadingSpinner) {
        expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');
      }
    });

    it('maintains focus management', async () => {
      const user = userEvent.setup();
      renderUploadWidget();

      const browseButton = screen.getByTestId('browse-files-button');
      const demoButton = screen.getByTestId('demo-data-button');
      
      // Tab to the first focusable element (browse button)
      await user.tab();
      expect(browseButton).toHaveFocus();
      
      // Tab to the next focusable element (demo button)
      await user.tab();
      expect(demoButton).toHaveFocus();
    });
  });
});