from pathlib import Path
from app.pdf.adapter import rewrite_asset_urls_for_pdf


def test_rewrite_asset_urls_for_pdf():
    html = '<img src="/assets/abc.png"><link href="/assets/style.css">'
    out = rewrite_asset_urls_for_pdf(html, Path('uploads'))
    assert 'file://' in out
    assert '/assets/' not in out

