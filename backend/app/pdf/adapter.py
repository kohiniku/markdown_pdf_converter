from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from app.config import settings


class PDFAdapter(Protocol):
    def generate(self, html: str, output_path: Path) -> None:
        ...


@dataclass
class WeasyPrintAdapter:
    """PDF adapter using WeasyPrint engine.

    This is kept minimal so we can swap engines later if needed.
    """

    def generate(self, html: str, output_path: Path) -> None:  # type: ignore[override]
        # Lazy import so environments without WeasyPrint can still run tests
        try:
            import weasyprint  # type: ignore
        except Exception as e:  # pragma: no cover - covered by DummyAdapter usage
            DummyAdapter().generate(html, output_path)
            return

        # Rewrite app-served asset URLs ("/assets/<file>") to local file URLs so
        # WeasyPrint can load images without knowing the server origin.
        html = rewrite_asset_urls_for_pdf(html, Path(settings.upload_dir).resolve())

        pdf_document = weasyprint.HTML(string=html)
        pdf_document.write_pdf(str(output_path))


def rewrite_asset_urls_for_pdf(html: str, uploads_dir: Path) -> str:
    base = uploads_dir.as_posix().rstrip('/') + '/'
    html = html.replace('src="/assets/', f'src="file://{base}')
    html = html.replace("src='/assets/", f"src='file://{base}")
    html = html.replace('href="/assets/', f'href="file://{base}')
    html = html.replace("href='/assets/", f"href='file://{base}")
    return html


@dataclass
class DummyAdapter:
    """A tiny adapter that writes a minimal PDF for testing without external deps."""

    def generate(self, html: str, output_path: Path) -> None:  # type: ignore[override]
        # Minimal valid PDF (one empty page). Good enough for tests.
        # Reference: PDF 1.4 skeleton
        minimal_pdf = (
            b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj<<>>endobj\n"
            b"2 0 obj<< /Type /Catalog /Pages 3 0 R >>endobj\n"
            b"3 0 obj<< /Type /Pages /Kids [4 0 R] /Count 1 >>endobj\n"
            b"4 0 obj<< /Type /Page /Parent 3 0 R /MediaBox [0 0 595 842] >>endobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000105 00000 n \n0000000169 00000 n \n"
            b"trailer<< /Size 5 /Root 2 0 R >>\nstartxref\n230\n%%EOF\n"
        )
        output_path.write_bytes(minimal_pdf)


def get_adapter(engine: str) -> PDFAdapter:
    engine_norm = (engine or "").strip().lower()
    if engine_norm in ("weasyprint", "weasy", "default", ""):
        try:
            # Probe availability lazily
            import importlib
            importlib.import_module("weasyprint")
            return WeasyPrintAdapter()
        except Exception:
            return DummyAdapter()
    if engine_norm in ("dummy", "test"):
        return DummyAdapter()
    # Unknown engine → safe fallback
    return DummyAdapter()
