from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import os
import tempfile
from pathlib import Path
from typing import Optional
import aiofiles
from datetime import datetime
import uuid
try:
    import emoji as emoji_lib
except Exception:
    emoji_lib = None

from app.config import settings, apply_proxy_settings
from app.database import engine
from app import models
from app.renderer import render_markdown_to_html
from app.pdf.adapter import get_adapter

# Initialize required tables at startup
# アプリ起動時に必要なテーブルを初期化する
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Markdown to PDF Converter",
    description="Convert Markdown content to PDF files",
    version="1.0.0",
)

# Add CORS middleware only when origins are configured
# CORSが設定されている場合のみオリジンを許可するミドルウェアを追加
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Ensure upload directory exists for image assets
# 画像アップロード用ディレクトリを確実に用意する
upload_dir_path = Path(settings.upload_dir)
upload_dir_path.mkdir(exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(upload_dir_path)), name="assets")


@app.get("/")
async def root():
    return {"message": "Markdown to PDF Converter API", "version": "1.0.0"}

@app.post("/convert")
async def convert_markdown_to_pdf(
    markdown_content: str = Form(...),
    filename: Optional[str] = Form(None),
    css_styles: Optional[str] = Form(None),
    emoji_mode: Optional[str] = Form("unicode"),
    newline_to_space: Optional[bool] = Form(None),
    font_size: Optional[int] = Form(None),
    page_size: Optional[str] = Form(None),
    orientation: Optional[str] = Form(None),
    margin: Optional[str] = Form(None),
    # Title page options
    # タイトルページのオプション
    title_page: Optional[bool] = Form(None),
    title_text: Optional[str] = Form(None),
    title_date: Optional[str] = Form(None),
    title_name: Optional[str] = Form(None),
):
    try:
        if not markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown content is required")
        # Handle emoji shortcodes according to settings
        # 絵文字ショートコードを設定に従って処理する
        if emoji_mode and emoji_lib:
            mode = (emoji_mode or "").lower()
            if mode in ("unicode", "on", "enable", "enabled"):
                markdown_content = emoji_lib.emojize(markdown_content, language='alias')
            elif mode in ("off", "disable", "disabled"):
                markdown_content = emoji_lib.replace_emoji(markdown_content, replace='')
        html_content, _ = render_markdown_to_html(
            markdown_content,
            newline_to_space=newline_to_space,
            font_size_px=font_size,
            custom_css=css_styles,
            page_size=page_size,
            orientation=orientation,
            margin=margin,
            title_page=title_page,
            title_text=title_text,
            title_date=title_date,
            title_author=title_name,
        )

        file_id = str(uuid.uuid4())
        output_filename = filename or f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        # Create output directory and prefix filename with UUID
        # 出力ディレクトリを作成しファイル名にUUIDを付与する
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{file_id}_{output_filename}"
        # Generate the file with the configured PDF engine
        # 設定されたPDFエンジンでファイルを生成する
        adapter = get_adapter(settings.pdf_engine)
        adapter.generate(html_content, output_path)
        
        return {
            "success": True,
            "message": "PDF generated successfully",
            "file_id": file_id,
            "filename": output_filename,
            "download_url": f"/download/{file_id}_{output_filename}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@app.post("/preview")
async def preview_markdown(
    markdown_content: str = Form(...),
    css_styles: Optional[str] = Form(None),
    emoji_mode: Optional[str] = Form("unicode"),
    newline_to_space: Optional[bool] = Form(None),
    font_size: Optional[int] = Form(None),
    page_size: Optional[str] = Form(None),
    orientation: Optional[str] = Form(None),
    margin: Optional[str] = Form(None),
    # Title page options
    # タイトルページのオプション
    title_page: Optional[bool] = Form(None),
    title_text: Optional[str] = Form(None),
    title_date: Optional[str] = Form(None),
    title_name: Optional[str] = Form(None),
):
    """Render Markdown to styled HTML for live preview.
    ライブプレビュー用にMarkdownをHTMLへ変換するエンドポイント。
    """
    try:
        if not markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown content is required")

        # Handle emoji shortcodes according to settings
        # 絵文字ショートコードを設定に従って処理する
        if emoji_mode and emoji_lib:
            mode = (emoji_mode or "").lower()
            if mode in ("unicode", "on", "enable", "enabled"):
                markdown_content = emoji_lib.emojize(markdown_content, language='alias')
            elif mode in ("off", "disable", "disabled"):
                markdown_content = emoji_lib.replace_emoji(markdown_content, replace='')
        html_content, _ = render_markdown_to_html(
            markdown_content,
            newline_to_space=newline_to_space,
            font_size_px=font_size,
            custom_css=css_styles,
            page_size=page_size,
            orientation=orientation,
            margin=margin,
            title_page=title_page,
            title_text=title_text,
            title_date=title_date,
            title_author=title_name,
        )

        return Response(content=html_content, media_type="text/html")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering preview: {str(e)}")

@app.post("/upload-convert")
async def upload_and_convert_file(
    file: UploadFile = File(...),
    css_styles: Optional[str] = Form(None)
):
    try:
        if not file.filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="Only .md files are supported")
        
        content = await file.read()
        markdown_content = content.decode('utf-8')
        
        # Ignore client-supplied names so the server assigns unique filenames
        # サーバー側で一意なファイル名を生成するためクライアントの名前は使用しない
        return await convert_markdown_to_pdf(
            markdown_content=markdown_content,
            filename=None,
            css_styles=css_styles
        )
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Allowed image extensions for uploads
# アップロードを許可する画像拡張子の一覧
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Perform basic extension validation (content validation is out of scope)
        # 拡張子ベースで簡易的なバリデーションを行う（内容検証は対象外）
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(status_code=400, detail="Unsupported image format")

        # Use UUID to avoid filename collisions
        # UUIDを使ってファイル名の衝突を避ける
        uid = uuid.uuid4().hex
        safe_name = f"{uid}{ext}"
        dest = upload_dir_path / safe_name
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Image too large")
        async with aiofiles.open(dest, 'wb') as out:
            await out.write(content)

        url = f"/assets/{safe_name}"
        return {"success": True, "url": url, "filename": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

@app.get("/download/{filename}")
async def download_pdf(filename: str):
    output_path = Path(settings.output_dir) / filename
    # Return 404 when the file does not exist
    # ファイルが存在しない場合は404を返す
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(output_path),
        filename=filename,
        media_type="application/pdf"
    )

def _collapse_soft_newlines(md: str) -> str:
    """Collapse single newlines within paragraphs into spaces.
    段落内の単独の改行をスペースへ置き換える。

    - Preserve blank-line paragraph breaks.
    - 空行による段落区切りは維持する。
    - Leave code fences, lists, headings, blockquotes, tables untouched.
    - コードブロックやリスト、見出し、引用、表などはそのまま残す。
    """
    lines = md.splitlines()
    out_lines = []
    para_buf: list[str] = []
    in_fence = False
    fence_delim = ""

    import re
    re_blank = re.compile(r"^\s*$")
    re_fence = re.compile(r"^\s*(```|~~~)")
    re_indented_code = re.compile(r"^\s{4,}")
    re_heading = re.compile(r"^\s*#{1,6}\s+")
    re_list = re.compile(r"^\s*(?:[*+-]|\d+[\.)])\s+")
    re_blockquote = re.compile(r"^\s*>\s*")
    re_table = re.compile(r"^\s*\|")
    re_hr = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
    re_admon = re.compile(r"^\s*!!!\b")
    re_html = re.compile(r"^\s*<[/!?]?")

    def flush_para():
        nonlocal para_buf
        if para_buf:
            out_lines.append(" ".join(s.strip() for s in para_buf))
            para_buf = []

    for raw in lines:
        line = raw.rstrip("\n")
        if in_fence:
            out_lines.append(line)
            if re_fence.match(line):
                in_fence = False
            continue

        if re_fence.match(line):
            flush_para()
            in_fence = True
            out_lines.append(line)
            continue

        if (re_blank.match(line) or re_indented_code.match(line) or re_heading.match(line)
            or re_blockquote.match(line) or re_table.match(line)
            or re_hr.match(line) or re_admon.match(line) or re_html.match(line)):
            flush_para()
            out_lines.append(line)
            continue

        # Insert a blank line when a list follows a paragraph to aid parsing
        # 段落の直後にリストが続く場合は空行を足してMarkdownパーサーにリストと認識させる
        if re_list.match(line):
            flush_para()
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            out_lines.append(line)
            continue

        # Buffer regular paragraph lines before collapsing
        # 通常の段落行は一旦バッファに追加する
        para_buf.append(line)

    flush_para()
    return "\n".join(out_lines)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Apply proxy configuration immediately after app creation when required
# プロキシ設定が必要な場合はアプリ初期化直後に適用する
if settings.apply_proxy_on_startup:
    apply_proxy_settings()
