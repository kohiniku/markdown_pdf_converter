from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Markdown to PDF Converter",
    description="Convert Markdown content to PDF files",
    version="1.0.0",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
):
    try:
        if not markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown content is required")
        # Emoji shortcode handling
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
        )

        file_id = str(uuid.uuid4())
        output_filename = filename or f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{file_id}_{output_filename}"
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
):
    """Render Markdown to styled HTML for live preview."""
    try:
        if not markdown_content.strip():
            raise HTTPException(status_code=400, detail="Markdown content is required")

        # Emoji shortcode handling
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
        
        filename = file.filename.replace('.md', '.pdf')
        
        return await convert_markdown_to_pdf(
            markdown_content=markdown_content,
            filename=filename,
            css_styles=css_styles
        )
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/download/{filename}")
async def download_pdf(filename: str):
    output_path = Path(settings.output_dir) / filename
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(output_path),
        filename=filename,
        media_type="application/pdf"
    )

def _collapse_soft_newlines(md: str) -> str:
    """Join single newlines inside normal paragraphs into spaces.
    - Preserves blank-line paragraph breaks
    - Leaves code fences/indented code, lists, headings, blockquotes, tables as-is
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

        # If a list starts directly after a paragraph (no blank line),
        # insert a blank line to ensure Markdown parser recognizes a list.
        if re_list.match(line):
            flush_para()
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            out_lines.append(line)
            continue

        # normal paragraph line → buffer
        para_buf.append(line)

    flush_para()
    return "\n".join(out_lines)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Apply proxy settings as early as possible after app is created
if settings.apply_proxy_on_startup:
    apply_proxy_settings()
