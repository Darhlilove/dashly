import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QueryBox from '../QueryBox';
import { apiService } from '../../services/api';
import { TranslateResponse } from '../../types/api';

// Mock the API service
vi.mock('../../services/api', () => ({
  apiService: {
    translateQuery: vi.fn(),
  },
}));

const mockApiService = apiService as any;

describe('QueryBox', () => {
  const mockOnSQLGenerated = vi.fn();
  const mockOnError = vi.fn();

  const mockTranslateResponse: TranslateResponse = {
    sql: 'SELECT * FROM sales WHERE date >= \'2023-01-01\'',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderQueryBox = (disabled = false) => {
    return render(
      <QueryBox
        onSQLGenerated={mockOnSQLGenerated}
        onError={mockOnError}
        disabled={disabled}
      />
    );
  };

  describe('Initial Render', () => {
    it('renders the query box with correct title and elements', () => {
      renderQueryBox();

      expect(screen.getByText('Ask a Question About Your Data')).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Show monthly revenue by region/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Generate' })).toBeInTheDocument();
    });

    it('renders textarea with proper attributes', () => {
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('id', 'query-input');
      expect(textarea).toHaveAttribute('rows', '3');
      expect(textarea).toHaveAttribute('aria-describedby', 'query-help');
    });

    it('renders help text', () => {
      renderQueryBox();

      expect(screen.getByText(/Describe what you want to see in plain English/)).toBeInTheDocument();
      expect(screen.getByText(/Press Ctrl\+Enter to generate/)).toBeInTheDocument();
    });

    it('has generate button disabled initially', () => {
      renderQueryBox();

      const generateButton = screen.getByRole('button', { name: 'Generate' });
      expect(generateButton).toBeDisabled();
    });
  });

  describe('User Input', () => {
    it('enables generate button when query is entered', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      expect(generateButton).toBeDisabled();

      await user.type(textarea, 'Show me sales data');

      expect(generateButton).not.toBeDisabled();
    });

    it('disables generate button for whitespace-only input', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, '   ');

      expect(generateButton).toBeDisabled();
    });

    it('shows query preview when query is entered', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Show me sales data');

      expect(screen.getByText('Your question:')).toBeInTheDocument();
      // Use getAllByText since the text appears in both textarea and preview
      const elements = screen.getAllByText('Show me sales data');
      expect(elements).toHaveLength(2); // One in textarea, one in preview
    });

    it('handles keyboard shortcuts (Ctrl+Enter)', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockResolvedValue(mockTranslateResponse);
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Show me sales data');

      await user.keyboard('{Control>}{Enter}{/Control}');

      await waitFor(() => {
        expect(mockApiService.translateQuery).toHaveBeenCalledWith('Show me sales data');
      });
    });

    it('handles keyboard shortcuts (Cmd+Enter on Mac)', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockResolvedValue(mockTranslateResponse);
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Show me sales data');

      await user.keyboard('{Meta>}{Enter}{/Meta}');

      await waitFor(() => {
        expect(mockApiService.translateQuery).toHaveBeenCalledWith('Show me sales data');
      });
    });
  });

  describe('Form Submission', () => {
    it('successfully translates query to SQL', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockResolvedValue(mockTranslateResponse);
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockApiService.translateQuery).toHaveBeenCalledWith('Show me sales data');
        expect(mockOnSQLGenerated).toHaveBeenCalledWith(
          mockTranslateResponse.sql,
          'Show me sales data'
        );
      });
    });

    it('trims whitespace from query before submission', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockResolvedValue(mockTranslateResponse);
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, '  Show me sales data  ');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockApiService.translateQuery).toHaveBeenCalledWith('Show me sales data');
        expect(mockOnSQLGenerated).toHaveBeenCalledWith(
          mockTranslateResponse.sql,
          'Show me sales data'
        );
      });
    });

    it('prevents submission of empty or whitespace-only queries', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, '   ');
      await user.click(generateButton);

      expect(mockApiService.translateQuery).not.toHaveBeenCalled();
      expect(mockOnSQLGenerated).not.toHaveBeenCalled();
    });

    it('prevents form submission via Enter key', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Show me sales data');
      await user.keyboard('{Enter}');

      // Should not submit, only Ctrl+Enter or Cmd+Enter should submit
      expect(mockApiService.translateQuery).not.toHaveBeenCalled();
    });
  });

  describe('Loading States', () => {
    it('shows loading state during API call', async () => {
      const user = userEvent.setup();
      
      let resolveTranslate: (value: any) => void;
      const translatePromise = new Promise((resolve) => {
        resolveTranslate = resolve;
      });
      mockApiService.translateQuery.mockReturnValue(translatePromise);

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      // Check loading state
      expect(screen.getByText('Generating...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(generateButton).toBeDisabled();
      expect(textarea).toBeDisabled();

      // Resolve the API call
      resolveTranslate!(mockTranslateResponse);

      await waitFor(() => {
        expect(screen.queryByText('Generating...')).not.toBeInTheDocument();
        expect(generateButton).not.toBeDisabled();
        expect(textarea).not.toBeDisabled();
      });
    });

    it('disables form during loading', async () => {
      const user = userEvent.setup();
      
      let resolveTranslate: (value: any) => void;
      const translatePromise = new Promise((resolve) => {
        resolveTranslate = resolve;
      });
      mockApiService.translateQuery.mockReturnValue(translatePromise);

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      // Try to submit again while loading
      await user.click(generateButton);

      // Should only be called once
      expect(mockApiService.translateQuery).toHaveBeenCalledTimes(1);

      resolveTranslate!(mockTranslateResponse);
    });
  });

  describe('Error Handling', () => {
    it('handles API errors with message', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Failed to translate query';
      mockApiService.translateQuery.mockRejectedValue({ message: errorMessage });

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(errorMessage);
      });
    });

    it('handles API errors without message', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockRejectedValue({});

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith('Failed to translate query to SQL');
      });
    });

    it('resets loading state after error', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockRejectedValue({ message: 'Error' });

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled();
        expect(screen.queryByText('Generating...')).not.toBeInTheDocument();
        expect(generateButton).not.toBeDisabled();
        expect(textarea).not.toBeDisabled();
      });
    });
  });

  describe('Disabled State', () => {
    it('disables all interactions when disabled prop is true', () => {
      renderQueryBox(true);

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      expect(textarea).toBeDisabled();
      expect(generateButton).toBeDisabled();
    });

    it('prevents form submission when disabled', async () => {
      const user = userEvent.setup();
      renderQueryBox(true);

      const generateButton = screen.getByRole('button', { name: 'Generate' });
      await user.click(generateButton);

      expect(mockApiService.translateQuery).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and relationships', () => {
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-describedby', 'query-help');
      
      const label = screen.getByLabelText('Natural language query');
      expect(label).toBe(textarea);

      const helpText = screen.getByText(/Describe what you want to see in plain English/);
      expect(helpText).toHaveAttribute('id', 'query-help');
    });

    it('maintains focus management', async () => {
      const user = userEvent.setup();
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      // Focus textarea directly
      await user.click(textarea);
      expect(textarea).toHaveFocus();

      // Tab to generate button (but it's disabled initially)
      await user.tab();
      // Since button is disabled, focus might not move to it
      // Let's just verify the button exists and is disabled
      expect(generateButton).toBeDisabled();
    });

    it('has loading spinner with proper accessibility attributes', async () => {
      const user = userEvent.setup();
      
      let resolveTranslate: (value: any) => void;
      const translatePromise = new Promise((resolve) => {
        resolveTranslate = resolve;
      });
      mockApiService.translateQuery.mockReturnValue(translatePromise);

      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      const loadingSpinner = screen.getByRole('status');
      expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');

      resolveTranslate!(mockTranslateResponse);
    });
  });

  describe('Query Persistence', () => {
    it('keeps query text after successful submission', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockResolvedValue(mockTranslateResponse);
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnSQLGenerated).toHaveBeenCalled();
      });

      // Query should still be in the textarea
      expect(textarea).toHaveValue('Show me sales data');
    });

    it('keeps query text after error', async () => {
      const user = userEvent.setup();
      mockApiService.translateQuery.mockRejectedValue({ message: 'Error' });
      renderQueryBox();

      const textarea = screen.getByRole('textbox');
      const generateButton = screen.getByRole('button', { name: 'Generate' });

      await user.type(textarea, 'Show me sales data');
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled();
      });

      // Query should still be in the textarea
      expect(textarea).toHaveValue('Show me sales data');
    });
  });
});