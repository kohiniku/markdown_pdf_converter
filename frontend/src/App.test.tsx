import { render, screen, fireEvent, waitFor } from '@testing-library/react';
/// <reference types="vitest" />
import App, { MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_SIZE_MB } from './App';

// Mock global fetch for tests
// グローバルなfetchをモック化する
const g: any = globalThis as any;
g.fetch = vi.fn();

// Mock FileReader for browser APIs in tests
// FileReaderもテスト用にモック化する
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
    // By default, preview endpoint returns simple HTML
    // デフォルトではプレビューAPIがシンプルなHTMLを返す想定
    g.fetch.mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/upload-image')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ url: '/assets/uploaded.png' }),
        });
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve('<html><body><h1>Preview</h1></body></html>'),
      });
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

  test('preview mode disables PDF conversion controls', () => {
    render(<App />);
    const pageSizeSelect = screen.getByLabelText(/Page size/i) as HTMLSelectElement;
    fireEvent.change(pageSizeSelect, { target: { value: 'preview' } });

    const convertButton = screen.getByText(/Convert to PDF/i);
    const orientationSelect = screen.getByLabelText(/Orientation/i) as HTMLSelectElement;
    const textarea = screen.getByPlaceholderText(/Enter your Markdown content here/i);

    fireEvent.change(textarea, { target: { value: '# Heading' } });

    expect(convertButton).toBeDisabled();
    expect(orientationSelect).toBeDisabled();
    expect(screen.getByText(/Continuous preview mode is active/i)).toBeInTheDocument();
    expect(screen.getByText(/Disable Preview Use to generate/i)).toBeInTheDocument();
  });

  test('shows error when conversion fails', async () => {
    // Keep preview successful but force a network error on convert
    // プレビューは成功させつつ、変換APIでネットワークエラーを起こさせる
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

  test('drops image into editor inserts markdown snippet', async () => {
    (g.fetch as any).mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/upload-image')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ url: '/assets/test.png' }),
        });
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve('<html></html>'),
      });
    });

    render(<App />);
    const textarea = screen.getByPlaceholderText(/Enter your Markdown content here/i) as HTMLTextAreaElement;
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'sample.png', { type: 'image/png' });

    fireEvent.drop(textarea, {
      dataTransfer: {
        files: [file],
        types: ['Files'],
      },
    });

    await waitFor(() => expect(textarea.value).toContain('![sample](/assets/test.png)'));
    expect(g.fetch).toHaveBeenCalledWith(
      '/upload-image',
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('pasting clipboard image inserts markdown snippet', async () => {
    (g.fetch as any).mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/upload-image')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ url: '/assets/pasted.png' }),
        });
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve('<html></html>'),
      });
    });

    render(<App />);
    const textarea = screen.getByPlaceholderText(/Enter your Markdown content here/i) as HTMLTextAreaElement;
    const clipboardFile = new File([new Uint8Array([137, 80, 78, 71])], 'clipboard.png', {
      type: 'image/png',
    });

    fireEvent.paste(textarea, {
      clipboardData: {
        files: [clipboardFile],
        items: [
          {
            kind: 'file',
            type: 'image/png',
            getAsFile: () => clipboardFile,
          },
        ],
        types: ['Files'],
      },
    });

    await waitFor(() => expect(textarea.value).toContain('![clipboard](/assets/pasted.png)'));
    expect(g.fetch).toHaveBeenCalledWith(
      '/upload-image',
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('editor tips are visible near markdown textarea', () => {
    render(<App />);
    expect(screen.getByText(/チェックリストは/)).toBeInTheDocument();
    expect(screen.getAllByText(/\[\[PAGEBREAK\]\]/i).length).toBeGreaterThan(0);
  });

  test('shows error when dropped image exceeds size limit', async () => {
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Enter your Markdown content here/i);
    const bigFile = new File([new Uint8Array([0])], 'huge.png', { type: 'image/png' });
    Object.defineProperty(bigFile, 'size', { value: MAX_IMAGE_SIZE_BYTES + 1 });

    fireEvent.drop(textarea, {
      dataTransfer: {
        files: [bigFile],
        types: ['Files'],
      },
    });

    await waitFor(() =>
      expect(screen.getByText(new RegExp(`Images larger than ${MAX_IMAGE_SIZE_MB} MB`))).toBeInTheDocument()
    );
    expect(g.fetch).not.toHaveBeenCalledWith(
      '/upload-image',
      expect.anything()
    );
  });
});
