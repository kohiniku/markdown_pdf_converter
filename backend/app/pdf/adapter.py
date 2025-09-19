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
    """Adapter that generates PDFs via WeasyPrint.

    Kept minimal to allow swapping engines later.
    将来的に他エンジンへ差し替えやすいよう最小限の実装に留めている。
    """

    def generate(self, html: str, output_path: Path) -> None:  # type: ignore[override]
        # Lazy import so tests run even without WeasyPrint installed
        # WeasyPrintが入っていない環境でもテストを回せるよう遅延インポートする
        try:
            import weasyprint  # type: ignore
        except Exception as e:  # pragma: no cover - DummyAdapterで吸収するケース
            DummyAdapter().generate(html, output_path)
            return

        # Rewrite app-served asset URLs to local file URLs so WeasyPrint can load images
        # アプリ内のアセットURL("/assets/<file>")をローカルファイルURLへ書き換え、WeasyPrintがサーバーのオリジンを知らなくても画像を読み込めるようにする
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
    """Tiny adapter that writes a minimal PDF without external deps.

    外部依存なくテスト用の最小PDFを書き出すアダプタ。
    """

    def generate(self, html: str, output_path: Path) -> None:  # type: ignore[override]
        # Minimal single-page PDF sufficient for tests (PDF 1.4 skeleton)
        # 空の1ページだけを含む最小構成のPDF。テスト用途には十分。（参考: PDF 1.4のスケルトン構造）
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
            # Probe availability lazily and fall back if unavailable
            # 利用可否を遅延確認し、存在しなければフォールバックする
            import importlib
            importlib.import_module("weasyprint")
            return WeasyPrintAdapter()
        except Exception:
            return DummyAdapter()
    if engine_norm in ("dummy", "test"):
        return DummyAdapter()
    # Unknown engines fall back to the dummy adapter
    # 未知のエンジン指定は安全側に倒してダミーを返す
    return DummyAdapter()
