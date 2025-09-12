import React, { useEffect, useRef, useState } from 'react';
import { FileText, Download, Upload, Moon, Sun } from 'lucide-react';
import './App.css';

interface ConversionResult {
  success: boolean;
  message: string;
  file_id: string;
  filename: string;
  download_url: string;
}

function App() {
  const [markdownContent, setMarkdownContent] = useState('');
  const [filename, setFilename] = useState('');
  const [cssStyles, setCssStyles] = useState('');
  // PDF base font size (px)
  const [fontSize, setFontSize] = useState<number>(13);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const previewTimer = useRef<number | null>(null);
  // Page setup
  const [pageSize, setPageSize] = useState<string>('A4');
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait');
  const [slideMode, setSlideMode] = useState<boolean>(false);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const saved = window.localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') {
      setIsDarkMode(saved === 'dark');
      return;
    }
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDarkMode(prefersDark);
  }, []);

  // Apply/remove .dark on <html> to activate CSS variable overrides
  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) root.classList.add('dark');
    else root.classList.remove('dark');
    window.localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const handleConvert = async () => {
    if (!markdownContent.trim()) {
      setError('Please enter some Markdown content');
      return;
    }

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('markdown_content', markdownContent);
      // Do not send filename; server always generates a new unique name
      if (cssStyles) formData.append('css_styles', cssStyles);
      if (fontSize) formData.append('font_size', String(fontSize));
      if (pageSize) formData.append('page_size', pageSize);
      if (orientation) formData.append('orientation', orientation);
      if (slideMode) formData.append('slide_mode', 'true');

      const response = await fetch('/convert', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Conversion failed');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = (file: File) => {
    if (!file.name.endsWith('.md')) {
      setError('Please select a .md file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setMarkdownContent(content);
      setFilename(file.name.replace('.md', ''));
      setError('');
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const downloadPDF = async () => {
    if (!result) return;
    try {
      const res = await fetch(result.download_url);
      if (!res.ok) throw new Error('Failed to download file');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    }
  };

  // Live preview (debounced)
  useEffect(() => {
    if (previewTimer.current) {
      window.clearTimeout(previewTimer.current);
    }
    if (!markdownContent.trim()) {
      setPreviewHtml('');
      return;
    }
    previewTimer.current = window.setTimeout(async () => {
      try {
        setIsPreviewLoading(true);
        const formData = new FormData();
        formData.append('markdown_content', markdownContent);
        if (fontSize) formData.append('font_size', String(fontSize));
        if (pageSize) formData.append('page_size', pageSize);
        if (orientation) formData.append('orientation', orientation);
        if (slideMode) formData.append('slide_mode', 'true');
        const res = await fetch('/preview', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Failed to render preview');
        const html = await res.text();
        setPreviewHtml(html);
      } catch {
        // keep silent for preview errors
      } finally {
        setIsPreviewLoading(false);
      }
    }, 300);
    return () => {
      if (previewTimer.current) window.clearTimeout(previewTimer.current);
    };
  }, [markdownContent, fontSize, pageSize, orientation, slideMode]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--background)' }}>
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8" style={{ color: 'var(--primary)' }} />
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text)' }}>
              Markdown to PDF Converter
            </h1>
          </div>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-2 rounded-lg hover:bg-opacity-80 transition-colors"
            style={{ backgroundColor: 'var(--surface)', color: 'var(--text)' }}
            aria-label="Toggle theme"
          >
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </header>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 xl:[grid-template-columns:1.1fr_1.4fr] 2xl:[grid-template-columns:1fr_1.6fr]">
          {/* Input Section */}
          <div className="space-y-6 min-w-0">
            {/* PDF Settings */}
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">PDF Settings</h2>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--muted)' }}>Font size</span>
                <span className="text-sm" style={{ color: 'var(--text)' }}>{fontSize}px</span>
              </div>
              <input
                type="range"
                min={8}
                max={18}
                step={1}
                value={fontSize}
                onChange={(e) => setFontSize(parseInt(e.target.value, 10))}
                className="w-full"
                aria-label="Font size"
              />
              <div className="mt-4 grid grid-cols-2 gap-3">
                <label className="text-sm" style={{ color: 'var(--muted)' }}>
                  Page size
                  <select
                    value={pageSize}
                    onChange={(e) => setPageSize(e.target.value)}
                    className="input w-full mt-1"
                  >
                    <option value="A3">A3</option>
                    <option value="A4">A4</option>
                    <option value="A5">A5</option>
                    <option value="Letter">Letter</option>
                    <option value="Legal">Legal</option>
                  </select>
                </label>
                <label className="text-sm" style={{ color: 'var(--muted)' }}>
                  Orientation
                  <select
                    value={orientation}
                    onChange={(e) => setOrientation(e.target.value as 'portrait' | 'landscape')}
                    className="input w-full mt-1"
                  >
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                  </select>
                </label>
                <label className="text-sm" style={{ color: 'var(--muted)' }}>
                  Slide mode (auto page breaks)
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={slideMode}
                      onChange={(e) => setSlideMode(e.target.checked)}
                    />
                    <span className="text-xs" style={{ color: 'var(--text)' }}>
                      Insert page breaks at headings/hr
                    </span>
                  </div>
                </label>
              </div>
            </div>
            {/* File Upload Area */}
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload Markdown File
              </h2>
              <div
                className={`drag-area ${dragOver ? 'drag-over' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <Upload className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p style={{ color: 'var(--muted)' }}>
                  Drag & drop a .md file here, or{' '}
                  <label className="cursor-pointer underline" style={{ color: 'var(--primary)' }}>
                    browse
                    <input
                      type="file"
                      accept=".md"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileUpload(file);
                      }}
                    />
                  </label>
                </p>
              </div>
            </div>

            {/* Markdown Input */}
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">Markdown Content</h2>
              <textarea
                value={markdownContent}
                onChange={(e) => setMarkdownContent(e.target.value)}
                placeholder="Enter your Markdown content here..."
                className="input textarea w-full"
              />
            </div>

            {/* Settings removed as requested */}
          </div>

          {/* Output Section */}
          <div className="space-y-6 min-w-0">
            {/* Convert Button */}
            <button
              onClick={handleConvert}
              disabled={isLoading || !markdownContent.trim()}
              className="button-primary w-full py-4 text-lg font-semibold"
            >
              {isLoading ? 'Converting...' : 'Convert to PDF'}
            </button>

            {/* Error Display */}
            {error && (
              <div className="card border-red-500 bg-red-50 dark:bg-red-900/20">
                <p className="text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {/* Success Result */}
            {result && (
              <div className="card border-green-500 bg-green-50 dark:bg-green-900/20">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-green-800 dark:text-green-200">
                      PDF Generated Successfully!
                    </h3>
                    <p className="text-green-600 dark:text-green-400 text-sm mt-1">
                      {result.filename}
                    </p>
                  </div>
                  <button
                    onClick={downloadPDF}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
              </div>
            )}

            {/* Live Preview */}
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">Preview</h2>
              {isPreviewLoading && (
                <p className="text-sm" style={{ color: 'var(--muted)' }}>Rendering preview…</p>
              )}
              {previewHtml ? (
                <iframe
                  title="preview"
                  className="preview-frame"
                  srcDoc={previewHtml}
                />
              ) : (
                <p className="text-sm" style={{ color: 'var(--muted)' }}>
                  Start typing Markdown to see a live preview here.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
