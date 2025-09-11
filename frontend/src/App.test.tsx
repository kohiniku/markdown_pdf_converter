import { render, screen, fireEvent, waitFor } from '@testing-library/react';
/// <reference types="vitest" />
import App from './App';

// Mock fetch globally
const g: any = globalThis as any;
g.fetch = vi.fn();

// Mock FileReader
const mockFileReader: any = {
  readAsText: vi.fn(),
  result: '',
  onload: null,
  onerror: null,
  readyState: 0,
};
g.FileReader = vi.fn().mockImplementation(() => mockFileReader);

describe('App Component', () => {
  beforeEach(() => {
    (g.fetch as any).mockClear();
    // Default: preview endpoint returns simple HTML
    g.fetch.mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('<html><body><h1>Preview</h1></body></html>'),
    });
  });

  test('renders main heading', () => {
    render(<App />);
    expect(screen.getByText(/Markdown to PDF Converter/i)).toBeInTheDocument();
  });

  test('renders upload area', () => {
    render(<App />);
    expect(screen.getByText(/Drag & drop a .md file here/i)).toBeInTheDocument();
  });

  test('renders markdown textarea', () => {
    render(<App />);
    expect(screen.getByPlaceholderText(/Enter your Markdown content here/i)).toBeInTheDocument();
  });

  test('convert button is disabled when no content', () => {
    render(<App />);
    const convertButton = screen.getByText(/Convert to PDF/i);
    expect(convertButton).toBeDisabled();
  });

  test('convert button enables after typing', () => {
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Enter your Markdown content here/i);
    const convertButton = screen.getByText(/Convert to PDF/i);
    fireEvent.change(textarea, { target: { value: '# Test Content' } });
    expect(convertButton).toBeEnabled();
  });

  test('shows error when conversion fails', async () => {
    // Preview returns HTML; convert fails with network error
    (g.fetch as any).mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/convert')) {
        return Promise.reject(new Error('Network error'));
      }
      return Promise.resolve({ ok: true, text: () => Promise.resolve('<html></html>') });
    });

    render(<App />);
    fireEvent.change(screen.getByPlaceholderText(/Enter your Markdown content here/i), {
      target: { value: '# Test Content' },
    });
    fireEvent.click(screen.getByText(/Convert to PDF/i));

    await waitFor(() => expect(screen.getByText(/Network error/i)).toBeInTheDocument());
  });

  test('shows success message on successful conversion', async () => {
    const mockResponse = {
      success: true,
      message: 'PDF generated successfully',
      file_id: 'test-id',
      filename: 'test.pdf',
      download_url: '/download/test.pdf',
    };

    (g.fetch as any).mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/convert')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockResponse) });
      }
      return Promise.resolve({ ok: true, text: () => Promise.resolve('<html></html>') });
    });

    render(<App />);
    fireEvent.change(screen.getByPlaceholderText(/Enter your Markdown content here/i), {
      target: { value: '# Test Content' },
    });
    fireEvent.click(screen.getByText(/Convert to PDF/i));

    await waitFor(() => expect(screen.getByText(/PDF Generated Successfully!/i)).toBeInTheDocument());
  });
});
