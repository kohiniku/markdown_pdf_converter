import React, { useEffect, useRef, useState } from 'react';
import { FileText, Download, Upload, Moon, Sun, Lightbulb } from 'lucide-react';
import './App.css';

export const MAX_IMAGE_SIZE_MB = 10;
export const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;
const PREVIEW_PAGE_SIZE = 'preview';

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
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [cssStyles, setCssStyles] = useState('');
  // Base PDF font size (px)
  // PDFの基準フォントサイズ（px）
  const [fontSize, setFontSize] = useState<number>(13);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const previewTimer = useRef<number | null>(null);
  // Page size and orientation settings
  // 用紙サイズや向きの設定
  const [pageSize, setPageSize] = useState<string>('A4');
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait');
  const isPreviewMode = pageSize === PREVIEW_PAGE_SIZE;
  // Title page (cover) settings
  // タイトルページ（表紙）の設定
  const [includeTitlePage, setIncludeTitlePage] = useState<boolean>(false);
  const [titleText, setTitleText] = useState<string>("");
  const [titleDate, setTitleDate] = useState<string>("");
  const [titleName, setTitleName] = useState<string>("");

  useEffect(() => {
    if (isPreviewMode) {
      setResult(null);
    }
  }, [isPreviewMode]);

  // Initialize theme from localStorage or system preference
  // localStorageやOSの設定からテーマを初期化する
  useEffect(() => {
    const saved = window.localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') {
      setIsDarkMode(saved === 'dark');
      return;
    }
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDarkMode(prefersDark);
  }, []);

  // Toggle the .dark class on <html> to switch theme variables
  // <html>要素に.darkクラスを付け外ししてテーマ用CSS変数を切り替える
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

    if (isPreviewMode) {
      setError('PDF download is disabled in Preview Use mode');
      return;
    }

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('markdown_content', markdownContent);
      // Let the server generate unique filenames instead of client-supplied ones
      // サーバー側で一意なファイル名を生成するためクライアントの名前は送らない
      if (cssStyles) formData.append('css_styles', cssStyles);
      if (fontSize) formData.append('font_size', String(fontSize));
      if (pageSize) formData.append('page_size', pageSize);
      if (orientation) formData.append('orientation', orientation);
      if (includeTitlePage) {
        formData.append('title_page', 'true');
        if (titleText) formData.append('title_text', titleText);
        if (titleDate) formData.append('title_date', titleDate);
        if (titleName) formData.append('title_name', titleName);
      }

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

  const isImageFile = (file: File) =>
    file.type.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(file.name);

  const selectImageFile = (files: FileList | File[]) =>
    Array.from(files).find((f) => isImageFile(f));

  const deriveAltText = (file: File, fallback = 'pasted-image') => {
    const base = file.name ? file.name.replace(/\.[^.]+$/, '') : '';
    const trimmed = (base || fallback).trim();
    return trimmed || fallback;
  };

  const insertImageMarkdown = (url: string, altText: string) => {
    const snippet = `![${altText}](${url})`;
    const el = textareaRef.current;
    if (el) {
      const currentValue = el.value ?? '';
      const start = el.selectionStart ?? currentValue.length;
      const end = el.selectionEnd ?? start;
      const before = currentValue.slice(0, start);
      const after = currentValue.slice(end);
      const needsBreakBefore = before.length > 0 && !before.endsWith('\n');
      const insertion = `${needsBreakBefore ? '\n' : ''}${snippet}\n`;
      const newText = `${before}${insertion}${after}`;
      setMarkdownContent(newText);
      const newPos = before.length + insertion.length;
      setTimeout(() => {
        const textarea = textareaRef.current;
        if (textarea) {
          textarea.setSelectionRange(newPos, newPos);
          textarea.focus();
        }
      }, 0);
    } else {
      setMarkdownContent((text) => (text ? `${text}\n${snippet}\n` : `${snippet}\n`));
    }
  };

  const uploadAndInsertImage = async (file: File, altHint?: string) => {
    if (file.size === 0) {
      throw new Error('Image file is empty');
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      throw new Error(`Images larger than ${MAX_IMAGE_SIZE_MB} MB are not supported`);
    }
    const formData = new FormData();
    const sanitizedHint = (altHint || 'pasted-image')
      .replace(/[^a-zA-Z0-9_-]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    const fallbackName = file.name && file.name.trim().length > 0
      ? file.name
      : `${sanitizedHint || 'pasted-image'}.png`;
    formData.append('file', file, fallbackName);
    const res = await fetch('/upload-image', { method: 'POST', body: formData });
    if (!res.ok) {
      throw new Error('Image upload failed');
    }
    const data = await res.json();
    const url: string = data.url;
    const altBase = altHint ?? deriveAltText(file);
    insertImageMarkdown(url, altBase || 'pasted-image');
  };

  const extractClipboardImage = (data: DataTransfer | null): File | null => {
    if (!data) return null;
    if (data.files && data.files.length) {
      const viaFiles = selectImageFile(data.files);
      if (viaFiles) return viaFiles;
    }
    if (data.items && data.items.length) {
      for (const item of Array.from(data.items)) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const maybe = item.getAsFile();
          if (maybe) return maybe;
        }
      }
    }
    return null;
  };

  const handleClipboardPaste = async (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const clipboardData = event.clipboardData;
    if (!clipboardData) return;
    const imageFile = extractClipboardImage(clipboardData);
    if (!imageFile) return;

    event.preventDefault();
    try {
      setError('');
      const alt = deriveAltText(imageFile, 'pasted-image');
      await uploadAndInsertImage(imageFile, alt);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Image paste failed';
      setError(message === 'Image upload failed' ? 'Image paste failed' : message);
    }
  };

  const downloadPDF = async () => {
    if (!result || isPreviewMode) return;
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

  // Update the live preview with debounce
  // ライブプレビューをディレイ付きで更新する
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
        if (includeTitlePage) {
          formData.append('title_page', 'true');
          if (titleText) formData.append('title_text', titleText);
          if (titleDate) formData.append('title_date', titleDate);
          if (titleName) formData.append('title_name', titleName);
        }
        const res = await fetch('/preview', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Failed to render preview');
        const html = await res.text();
        setPreviewHtml(html);
      } catch {
        // Silently swallow preview refresh failures
        // プレビュー更新の失敗はユーザーに通知せず静かに無視する
      } finally {
        setIsPreviewLoading(false);
      }
    }, 300);
    return () => {
      if (previewTimer.current) window.clearTimeout(previewTimer.current);
    };
  }, [markdownContent, fontSize, pageSize, orientation]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--background)' }}>
      <div
        className="container mx-auto px-6 py-8"
        style={{ maxWidth: '1400px' }}
      >
        {/*
          Header
          ヘッダー
        */}
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <FileText className="icon-xl" style={{ color: 'var(--primary)' }} aria-hidden="true" />
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

        <div className="grid grid-cols-1 gap-8 md:[grid-template-columns:1fr_1.8fr]">
          {/*
            Input Area
            入力エリア
          */}
          <div className="space-y-6 min-w-0">
            {/*
              PDF Settings Panel
              PDF設定
            */}
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
                    <option value={PREVIEW_PAGE_SIZE}>Preview Use</option>
                    <option value="A3">A3</option>
                    <option value="A4">A4</option>
                    <option value="A5">A5</option>
                    <option value="Letter">Letter</option>
                    <option value="Legal">Legal</option>
                  </select>
                  {isPreviewMode && (
                    <span className="block text-xs mt-2" style={{ color: 'var(--muted)' }}>
                      Continuous preview mode is active; PDF download is disabled.
                    </span>
                  )}
                </label>
                <label className="text-sm" style={{ color: 'var(--muted)' }}>
                  Orientation
                  <select
                    value={orientation}
                    onChange={(e) => setOrientation(e.target.value as 'portrait' | 'landscape')}
                    className="input w-full mt-1"
                    disabled={isPreviewMode}
                  >
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                  </select>
                </label>
                <label className="text-sm col-span-2" style={{ color: 'var(--muted)' }}>
                  Title page (cover slide)
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeTitlePage}
                      onChange={(e) => setIncludeTitlePage(e.target.checked)}
                    />
                    <span className="text-xs" style={{ color: 'var(--text)' }}>
                      Prepend a centered title page to the PDF
                    </span>
                  </div>
                </label>
              </div>
              {includeTitlePage && (
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <label className="text-sm col-span-2" style={{ color: 'var(--muted)' }}>
                    Title
                    <input
                      className="input w-full mt-1"
                      placeholder="My Presentation"
                      value={titleText}
                      onChange={(e) => setTitleText(e.target.value)}
                    />
                  </label>
                  <label className="text-sm" style={{ color: 'var(--muted)' }}>
                    Date
                    <input
                      className="input w-full mt-1"
                      placeholder="2025-09-12"
                      value={titleDate}
                      onChange={(e) => setTitleDate(e.target.value)}
                    />
                  </label>
                  <label className="text-sm" style={{ color: 'var(--muted)' }}>
                    Name
                    <input
                      className="input w-full mt-1"
                      placeholder="Your Name"
                      value={titleName}
                      onChange={(e) => setTitleName(e.target.value)}
                    />
                  </label>
                </div>
              )}
            </div>
            {/* ファイルアップロードエリア */}
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

            {/*
              Markdown Editor
              Markdown入力欄
            */}
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">Markdown Content</h2>
              <textarea
                ref={textareaRef}
                value={markdownContent}
                onChange={(e) => setMarkdownContent(e.target.value)}
                placeholder="Enter your Markdown content here..."
                className="input textarea w-full"
                onPaste={handleClipboardPaste}
                onDragOver={(e) => {
                  // Allow dropping image files directly onto the editor
                  // エディタ上に直接画像ファイルをドロップできるようにする
                  if (e.dataTransfer?.types?.includes('Files')) e.preventDefault();
                }}
                onDrop={async (e) => {
                  const dataTransfer = e.dataTransfer;
                  if (!dataTransfer) return;
                  const imageFile = extractClipboardImage(dataTransfer);
                  if (!imageFile) return;
                  e.preventDefault();
                  try {
                    setError('');
                    const alt = deriveAltText(imageFile, 'pasted-image');
                    await uploadAndInsertImage(imageFile, alt);
                  } catch (err) {
                    const message = err instanceof Error ? err.message : 'Image drop failed';
                    setError(message === 'Image upload failed' ? 'Image drop failed' : message);
                  }
                }}
              />
              <div className="editor-tips" role="note">
                <h3 className="editor-tips__title">
                  <Lightbulb className="editor-tips__icon" aria-hidden="true" />
                  エディタのヒント
                </h3>
                <ul className="editor-tips__list">
                  <li>チェックリストは <code>- [ ]</code> や <code>- [x]</code> を行頭に付与</li>
                  <li>ページ分割したい場所には <code>[[PAGEBREAK]]</code></li>
                  <li>画像を小さくしたいときは <code>{'{width=50%}'}</code> を末尾に付与</li>
                  <li>文字色を変えたいときは<br></br><code>&lt;span style="color:red"&gt; (内容) &lt;/span&gt;</code><br></br></li>
                  <li>注意書きは <br></br> <code>:::note (タイトル) <br></br> (内容) <br></br> :::</code></li>
                    <ul className="editor-tips__list">
                      <li>noteのほかにはtip/warning/caution/infoがある </li>
                    </ul>
                  <li>(エンジニア向け)Bootstrapも利用可能</li>
                </ul>
              </div>
            </div>

            {/*
              Additional settings intentionally removed per requirements
              追加設定は要求により削除済み
            */}
          </div>

          {/*
            Output Area
            出力エリア
          */}
          <div className="flex min-w-0 h-full flex-col gap-6">
            {/*
              Convert Button
              変換ボタン
            */}
            <button
              onClick={handleConvert}
              disabled={isLoading || !markdownContent.trim() || isPreviewMode}
              className="button-primary w-full py-4 text-lg font-semibold shrink-0"
            >
              {isLoading ? 'Converting...' : 'Convert to PDF'}
            </button>
            {isPreviewMode && (
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                Disable Preview Use to generate and download PDF files.
              </p>
            )}

            {/*
              Error Display
              エラー表示
            */}
            {error && (
              <div className="card border-red-500 bg-red-50 dark:bg-red-900/20">
                <p className="text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {/*
              Success Message
              変換成功メッセージ
            */}
            {result && !isPreviewMode && (
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
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                    disabled={isPreviewMode}
                  >
                    <Download className="icon-button" aria-hidden="true" />
                    Download
                  </button>
                </div>
              </div>
            )}

            {/*
              Live Preview
              ライブプレビュー
            */}
            <div className="card flex min-h-[720px] flex-1 flex-col">
              <h2 className="text-lg font-semibold mb-4">Preview</h2>
              {isPreviewLoading && (
                <p className="text-sm" style={{ color: 'var(--muted)' }}>Rendering preview…</p>
              )}
              <div className="flex-1 min-h-0">
                {previewHtml ? (
                  <iframe
                    title="preview"
                    className="preview-frame"
                    srcDoc={previewHtml}
                  />
                ) : (
                  <div className="preview-placeholder">
                    Start typing Markdown to see a live preview here.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
