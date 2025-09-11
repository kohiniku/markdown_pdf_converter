from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import os
import tempfile
import markdown
import weasyprint
from pathlib import Path
from typing import Optional
import aiofiles
from datetime import datetime
import uuid
try:
    import emoji as emoji_lib
except Exception:
    emoji_lib = None

from app.config import settings
from app.database import engine
from app import models

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
    emoji_mode: Optional[str] = Form("unicode")
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

        extensions = [
            'extra',               # abbr, attr_list, def_list, fenced_code, footnotes, tables
            'admonition',          # !!! note/warning など
            'pymdownx.details',
            'pymdownx.superfences',
            'pymdownx.tasklist',
            'pymdownx.tilde',      # ~~strike~~
            'pymdownx.mark',       # ==mark==
            'pymdownx.betterem',
            'pymdownx.magiclink',  # URL自動リンク
            'codehilite',
            'toc',
            'tables'
        ]
        extension_configs = {
            'codehilite': {
                'guess_lang': False,
                'linenums': False
            },
            'pymdownx.tasklist': {
                'custom_checkbox': True
            },
            'pymdownx.magiclink': {
                'repo_url_shortener': True,
                'hide_protocol': True
            }
        }

        html = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs=extension_configs
        )
        
        default_css = """
        body {
            /* Prefer Japanese-capable fonts first */
            font-family: 'Noto Sans CJK JP', 'Noto Sans JP', 'Noto Serif CJK JP', 'IPAexGothic', 'IPAGothic', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', Meiryo, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'JetBrains Mono', 'Fira Code', Menlo, Consolas, 'Liberation Mono', monospace;
        }
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
        }
        blockquote {
            border-left: 4px solid #3498db;
            margin: 0;
            padding-left: 20px;
            font-style: italic;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        /* Admonitions (pymdown/admonition) */
        .admonition { border-left: 4px solid #9aa4b2; padding: 12px 16px; background: #f9fafb; border-radius: 8px; margin: 16px 0; }
        .admonition .admonition-title { font-weight: 600; margin-bottom: 8px; }
        .admonition.note { border-color: #2e86de; background: #ecf5ff; }
        .admonition.info { border-color: #17a2b8; background: #e8f7fb; }
        .admonition.tip, .admonition.hint { border-color: #20c997; background: #e8fff6; }
        .admonition.warning { border-color: #e67e22; background: #fff4e5; }
        .admonition.danger, .admonition.caution, .admonition.error { border-color: #e74c3c; background: #ffecec; }
        /* Task list */
        ul.task-list { padding-left: 0; }
        .task-list-item { list-style: none; margin-left: 0; }
        .task-list-item input[type="checkbox"] { margin-right: 8px; transform: translateY(1px); }
        /* CodeHilite */
        .codehilite { background: #f8f8f8; border: 1px solid #ddd; border-radius: 6px; padding: 12px; overflow-x: auto; }
        """
        
        final_css = css_styles if css_styles else default_css
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{final_css}</style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        file_id = str(uuid.uuid4())
        output_filename = filename or f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'
        
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{file_id}_{output_filename}"
        
        pdf_document = weasyprint.HTML(string=html_content)
        pdf_document.write_pdf(str(output_path))
        
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
    emoji_mode: Optional[str] = Form("unicode")
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

        extensions = [
            'extra',
            'admonition',
            'pymdownx.details',
            'pymdownx.superfences',
            'pymdownx.tasklist',
            'pymdownx.tilde',
            'pymdownx.mark',
            'pymdownx.betterem',
            'pymdownx.magiclink',
            'codehilite',
            'toc',
            'tables'
        ]
        extension_configs = {
            'codehilite': {
                'guess_lang': False,
                'linenums': False
            },
            'pymdownx.tasklist': {
                'custom_checkbox': True
            },
            'pymdownx.magiclink': {
                'repo_url_shortener': True,
                'hide_protocol': True
            }
        }

        html = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs=extension_configs
        )

        default_css = """
        body {
            font-family: 'Noto Sans CJK JP', 'Noto Sans JP', 'Noto Serif CJK JP', 'IPAexGothic', 'IPAGothic', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', Meiryo, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
        }
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
        }
        blockquote {
            border-left: 4px solid #3498db;
            margin: 0;
            padding-left: 20px;
            font-style: italic;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .admonition { border-left: 4px solid #9aa4b2; padding: 12px 16px; background: #f9fafb; border-radius: 8px; margin: 16px 0; }
        .admonition .admonition-title { font-weight: 600; margin-bottom: 8px; }
        .admonition.note { border-color: #2e86de; background: #ecf5ff; }
        .admonition.info { border-color: #17a2b8; background: #e8f7fb; }
        .admonition.tip, .admonition.hint { border-color: #20c997; background: #e8fff6; }
        .admonition.warning { border-color: #e67e22; background: #fff4e5; }
        .admonition.danger, .admonition.caution, .admonition.error { border-color: #e74c3c; background: #ffecec; }
        ul.task-list { padding-left: 0; }
        .task-list-item { list-style: none; margin-left: 0; }
        .task-list-item input[type=\"checkbox\"] { margin-right: 8px; transform: translateY(1px); }
        .codehilite { background: #f8f8f8; border: 1px solid #ddd; border-radius: 6px; padding: 12px; overflow-x: auto; }
        """

        final_css = css_styles if css_styles else default_css

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset=\"utf-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
            <style>{final_css}</style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """

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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
