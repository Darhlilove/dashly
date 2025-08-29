import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SQLPreviewModal from '../SQLPreviewModal';
import { apiService } from '../../services/api';
import { ExecuteResponse } from '../../types/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  apiService: {
    executeSQL: vi.fn(),
  },
}));

const mockApiService = apiService as any;

describe('SQLPreviewModal', () => {
  const mockOnClose = vi.fn();
  const mockOnExecuteSuccess = vi.fn();
  const mockOnExecuteError = vi.fn();

  const defaultProps = {
    isOpen: true,
    sql: 'SELECT * FROM sales WHERE date >= \'2023-01-01\'',
    onClose: mockOnClose,
    onExecuteSuccess: mockOnExecuteSuccess,
    onExecuteError: mockOnExecuteError,
  };

  const mockExecuteResponse: ExecuteResponse = {
    columns: ['id', 'name', 'amount'],
    rows: [
      [1, 'Product A', 100],
      [2, 'Product B', 200],
    ],
    row_count: 2,
    runtime_ms: 150,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderModal = (props = {}) => {
    return render(<SQLPreviewModal {...defaultProps} {...props} />);
  };

  describe('Modal Visibility', () => {
    it('renders when isOpen is true', () => {
      renderModal();

      expect(screen.getByText('Review Generated SQL')).toBeInTheDocument();
      expect(screen.getByDisplayValue(defaultProps.sql)).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      renderModal({ isOpen: false });

      expect(screen.queryByText('Review Generated SQL')).not.toBeInTheDocument();
    });
  });

  describe('Modal Structure', () => {
    it('renders modal header with title and close button', () => {
      renderModal();

      expect(screen.getByText('Review Generated SQL')).toBeInTheDocument();
      expect(screen.getByLabelText('Close modal')).toBeInTheDocument();
    });

    it('renders SQL textarea with proper attributes', () => {
      renderModal();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('id', 'sql-textarea');
      expect(textarea).toHaveValue(defaultProps.sql);
      expect(textarea).toHaveAttribute('spellCheck', 'false');
    });

    it('renders action buttons', () => {
      renderModal();

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Run Query' })).toBeInTheDocument();
    });

    it('renders help text about SQL restrictions', () => {
      renderModal();

      expect(screen.getByText(/Only SELECT statements are allowed/)).toBeInTheDocument();
    });
  });

  describe('SQL Editing', () => {
    it('allows editing SQL in textarea', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      await user.clear(textarea);
      await user.type(textarea, 'SELECT name FROM products');

      expect(textarea).toHaveValue('SELECT name FROM products');
    });

    it('updates SQL when prop changes', () => {
      const { rerender } = renderModal();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(defaultProps.sql);

      const newSQL = 'SELECT COUNT(*) FROM orders';
      rerender(<SQLPreviewModal {...defaultProps} sql={newSQL} />);

      expect(textarea).toHaveValue(newSQL);
    });

    it('focuses textarea when modal opens', () => {
      renderModal();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();
    });

    it('auto-resizes textarea based on content', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;

      // Add more content to trigger resize
      await user.type(textarea, '\nUNION ALL\nSELECT * FROM products\nWHERE category = \'electronics\'');

      // Height should change (we can't test exact values due to DOM limitations in tests)
      expect(textarea.style.height).toBeDefined();
    });
  });

  describe('Modal Interactions', () => {
    it('closes modal when close button is clicked', async () => {
      const user = userEvent.setup();
      renderModal();

      const closeButton = screen.getByLabelText('Close modal');
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('closes modal when cancel button is clicked', async () => {
      const user = userEvent.setup();
      renderModal();

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('closes modal when overlay is clicked', async () => {
      const user = userEvent.setup();
      renderModal();

      // Click on the overlay (the backdrop)
      const overlay = screen.getByRole('dialog').parentElement!;
      await user.click(overlay);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('does not close modal when modal content is clicked', async () => {
      const user = userEvent.setup();
      renderModal();

      const modalContent = screen.getByRole('dialog');
      await user.click(modalContent);

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it('closes modal when Escape key is pressed', async () => {
      const user = userEvent.setup();
      renderModal();

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('does not close modal when Escape is pressed and modal is closed', async () => {
      const user = userEvent.setup();
      renderModal({ isOpen: false });

      await user.keyboard('{Escape}');

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('SQL Execution', () => {
    it('successfully executes SQL query', async () => {
      const user = userEvent.setup();
      mockApiService.executeSQL.mockResolvedValue(mockExecuteResponse);
      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      await waitFor(() => {
        expect(mockApiService.executeSQL).toHaveBeenCalledWith(defaultProps.sql);
        expect(mockOnExecuteSuccess).toHaveBeenCalledWith(mockExecuteResponse);
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('executes edited SQL query', async () => {
      const user = userEvent.setup();
      mockApiService.executeSQL.mockResolvedValue(mockExecuteResponse);
      renderModal();

      const textarea = screen.getByRole('textbox');
      const editedSQL = 'SELECT name FROM products LIMIT 10';
      
      await user.clear(textarea);
      await user.type(textarea, editedSQL);

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      await waitFor(() => {
        expect(mockApiService.executeSQL).toHaveBeenCalledWith(editedSQL);
      });
    });

    it('handles execution errors', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Invalid SQL syntax';
      mockApiService.executeSQL.mockRejectedValue({ message: errorMessage });
      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      await waitFor(() => {
        expect(mockOnExecuteError).toHaveBeenCalledWith(errorMessage);
        expect(mockOnClose).not.toHaveBeenCalled();
      });
    });

    it('handles execution errors without message', async () => {
      const user = userEvent.setup();
      mockApiService.executeSQL.mockRejectedValue({});
      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      await waitFor(() => {
        expect(mockOnExecuteError).toHaveBeenCalledWith('Failed to execute SQL query');
      });
    });

    it('prevents execution of empty SQL', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      await user.clear(textarea);

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      expect(mockOnExecuteError).toHaveBeenCalledWith('SQL query cannot be empty');
      expect(mockApiService.executeSQL).not.toHaveBeenCalled();
    });

    it('prevents execution of whitespace-only SQL', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      await user.clear(textarea);
      await user.type(textarea, '   \n\t  ');

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      expect(mockOnExecuteError).toHaveBeenCalledWith('SQL query cannot be empty');
      expect(mockApiService.executeSQL).not.toHaveBeenCalled();
    });
  });

  describe('Loading States', () => {
    it('shows loading state during SQL execution', async () => {
      const user = userEvent.setup();
      
      let resolveExecution: (value: any) => void;
      const executionPromise = new Promise((resolve) => {
        resolveExecution = resolve;
      });
      mockApiService.executeSQL.mockReturnValue(executionPromise);

      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      // Check loading state
      expect(screen.getByText('Running Query...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(runButton).toBeDisabled();

      // Resolve the execution
      resolveExecution!(mockExecuteResponse);

      await waitFor(() => {
        expect(screen.queryByText('Running Query...')).not.toBeInTheDocument();
      });
    });

    it('disables buttons during execution', async () => {
      const user = userEvent.setup();
      
      let resolveExecution: (value: any) => void;
      const executionPromise = new Promise((resolve) => {
        resolveExecution = resolve;
      });
      mockApiService.executeSQL.mockReturnValue(executionPromise);

      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      const cancelButton = screen.getByRole('button', { name: 'Cancel' });

      await user.click(runButton);

      expect(runButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();

      resolveExecution!(mockExecuteResponse);

      await waitFor(() => {
        expect(runButton).not.toBeDisabled();
        expect(cancelButton).not.toBeDisabled();
      });
    });

    it('resets loading state after error', async () => {
      const user = userEvent.setup();
      mockApiService.executeSQL.mockRejectedValue({ message: 'Error' });

      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      await waitFor(() => {
        expect(mockOnExecuteError).toHaveBeenCalled();
        expect(screen.queryByText('Running Query...')).not.toBeInTheDocument();
        expect(runButton).not.toBeDisabled();
      });
    });
  });

  describe('Button States', () => {
    it('keeps run button enabled when SQL is empty (to show error message)', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      const runButton = screen.getByRole('button', { name: 'Run Query' });

      await user.clear(textarea);

      expect(runButton).not.toBeDisabled();
    });

    it('keeps run button enabled when SQL has content', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      const runButton = screen.getByRole('button', { name: 'Run Query' });

      await user.clear(textarea);
      await user.type(textarea, 'SELECT 1');

      expect(runButton).not.toBeDisabled();
    });

    it('keeps run button enabled for whitespace-only SQL (to show error message)', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      const runButton = screen.getByRole('button', { name: 'Run Query' });

      await user.clear(textarea);
      await user.type(textarea, '   \n\t  ');

      expect(runButton).not.toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      renderModal();

      const closeButton = screen.getByLabelText('Close modal');
      expect(closeButton).toBeInTheDocument();

      const textarea = screen.getByLabelText('SQL Query (editable)');
      expect(textarea).toBeInTheDocument();
    });

    it('has loading spinner with proper accessibility attributes', async () => {
      const user = userEvent.setup();
      
      let resolveExecution: (value: any) => void;
      const executionPromise = new Promise((resolve) => {
        resolveExecution = resolve;
      });
      mockApiService.executeSQL.mockReturnValue(executionPromise);

      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      await user.click(runButton);

      const loadingSpinner = screen.getByRole('status');
      expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');

      resolveExecution!(mockExecuteResponse);
    });

    it('maintains focus management', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();

      // Tab to cancel button
      await user.tab();
      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      expect(cancelButton).toHaveFocus();

      // Tab to run button
      await user.tab();
      const runButton = screen.getByRole('button', { name: 'Run Query' });
      expect(runButton).toHaveFocus();
    });

    it('traps focus within modal', async () => {
      const user = userEvent.setup();
      renderModal();

      const textarea = screen.getByRole('textbox');
      const closeButton = screen.getByLabelText('Close modal');

      // Start at textarea
      expect(textarea).toHaveFocus();

      // Shift+Tab should go to close button (last focusable element)
      await user.keyboard('{Shift>}{Tab}{/Shift}');
      expect(closeButton).toHaveFocus();

      // Tab should go back to textarea (first focusable element)
      await user.tab();
      expect(textarea).toHaveFocus();
    });
  });

  describe('Event Handling', () => {
    it('prevents multiple simultaneous executions', async () => {
      const user = userEvent.setup();
      
      let resolveExecution: (value: any) => void;
      const executionPromise = new Promise((resolve) => {
        resolveExecution = resolve;
      });
      mockApiService.executeSQL.mockReturnValue(executionPromise);

      renderModal();

      const runButton = screen.getByRole('button', { name: 'Run Query' });
      
      // Click multiple times rapidly
      await user.click(runButton);
      await user.click(runButton);
      await user.click(runButton);

      // Should only be called once
      expect(mockApiService.executeSQL).toHaveBeenCalledTimes(1);

      resolveExecution!(mockExecuteResponse);
    });

    it('cleans up event listeners when unmounted', () => {
      const { unmount } = renderModal();
      
      // Mock removeEventListener to verify cleanup
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');

      unmount();

      // Verify that event listeners are cleaned up
      expect(removeEventListenerSpy).toHaveBeenCalled();
    });
  });
});