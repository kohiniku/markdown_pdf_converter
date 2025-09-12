from textwrap import dedent

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings, apply_proxy_settings


client = TestClient(app)


def test_preview_has_growi_container_and_heading_anchor():
    md = "# Title\n\nParagraph"
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    html = res.text
    assert "class=\"gw-container\"" in html
    # permalink anchor span/link
    assert "gw-heading-anchor" in html


def test_preview_footnotes_and_tables_render():
    md = dedent(
        """
        A sentence with a footnote.[^1]

        [^1]: footnote body

        | h1 | h2 |
        |----|----|
        | c1 | c2 |
        """
    )
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    h = res.text
    assert "footnotes" in h
    assert "<table" in h and "<td" in h


def test_proxy_env_application(monkeypatch):
    # ensure we start from a clean env
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"]:
        monkeypatch.delenv(k, raising=False)

    # override live settings via monkeypatching attributes
    monkeypatch.setattr(settings, "http_proxy", "http://proxy.local:8080")
    monkeypatch.setattr(settings, "https_proxy", "https://secure-proxy.local:8443")
    monkeypatch.setattr(settings, "no_proxy", "localhost,127.0.0.1")

    apply_proxy_settings()

    import os

    assert os.environ.get("HTTP_PROXY") == "http://proxy.local:8080"
    assert os.environ.get("HTTPS_PROXY") == "https://secure-proxy.local:8443"
    assert os.environ.get("NO_PROXY") == "localhost,127.0.0.1"


def test_declared_growi_target_version_present():
    assert settings.growi_target_version.startswith("7.")


def test_preview_page_setup_a4_landscape_margin():
    md = "# Title\n\nParagraph"
    res = client.post(
        "/preview",
        data={
            "markdown_content": md,
            "page_size": "A4",
            "orientation": "landscape",
            "margin": "15mm",
        },
    )
    assert res.status_code == 200
    html = res.text
    compact = html.replace(" ", "")
    assert "@page" in html and ("size:A4landscape" in compact or "size:A4 landscape" in html)


def test_github_callout_note_blockquote():
    md = (
        "> [!NOTE]\n"
        "> Useful Information that user should know\n"
    )
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    html = res.text
    # rendered as admonition note
    assert 'class="admonition note"' in html
    assert 'Useful Information' in html


def test_triple_colon_admonition_note():
    md = (
        ":::note\n"
        "Useful Information that user should know\n"
        ":::\n"
    )
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    html = res.text
    assert 'class="admonition note"' in html

def test_triple_colon_warning_title_with_emoji_dedup():
    md = (
        ":::warning ⚠ Warning\n"
        "Be careful\n"
        ":::\n"
    )
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    html = res.text
    # Consider only visible content (cut after </style>)
    cut = html.rfind("</style>")
    visible = html[cut + len("</style>") :] if cut != -1 else html
    # Title text is present once (CSS provides the emoji icon)
    assert visible.count(">Warning<") == 1
    # CSS contains mapping for title ::before, not container ::before
    assert ".admonition.warning .admonition-title::before" in html
    assert ".admonition.warning::before" not in html


def test_slide_mode_injects_css_rules():
    md = "# A\n\nText\n\n## B\n\nMore"
    res = client.post(
        "/preview",
        data={"markdown_content": md, "slide_mode": "true"},
    )
    assert res.status_code == 200
    html = res.text
    assert "page-break-before: always" in html or "break-before: page" in html


def test_slide_mode_off_has_no_rules():
    md = "# A\n\nText"
    res = client.post(
        "/preview",
        data={"markdown_content": md},
    )
    assert res.status_code == 200
    html = res.text
    assert "page-break-before: always" not in html


def test_newline_as_space_inside_admonition():
    md = (
        ":::note\n"
        "Line one\n"
        "continues here\n"
        "\n"
        "New para\n"
        ":::\n"
    )
    res = client.post(
        "/preview",
        data={"markdown_content": md, "newline_to_space": "true"},
    )
    assert res.status_code == 200
    html = res.text
    # After </style>, look for collapsed line content in a single paragraph
    cut = html.rfind("</style>")
    visible = html[cut + len("</style>") :] if cut != -1 else html
    assert "Line one continues here" in visible
    # paragraph break preserved
    assert "New para" in visible
