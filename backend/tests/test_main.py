import pytest
from fastapi.testclient import TestClient
from textwrap import dedent
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Markdown to PDF Converter API"
    assert data["version"] == "1.0.0"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_convert_empty_content():
    response = client.post("/convert", data={"markdown_content": ""})
    assert response.status_code == 400
    data = response.json()
    assert "Markdown content is required" in data["detail"]

def test_convert_valid_markdown():
    markdown_content = "# Test Header\n\nThis is a test paragraph."
    response = client.post("/convert", data={"markdown_content": markdown_content})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "file_id" in data
    assert "filename" in data
    assert "download_url" in data

def test_convert_with_filename():
    markdown_content = "# Custom Filename Test"
    filename = "custom_test"
    response = client.post("/convert", data={
        "markdown_content": markdown_content,
        "filename": filename
    })
    assert response.status_code == 200
    data = response.json()
    assert filename in data["filename"]

def test_convert_with_css():
    markdown_content = "# Styled Test"
    css_styles = "body { color: red; }"
    response = client.post("/convert", data={
        "markdown_content": markdown_content,
        "css_styles": css_styles
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

def test_download_nonexistent_file():
    response = client.get("/download/nonexistent_file.pdf")
    assert response.status_code == 404


def test_convert_japanese_text():
    markdown_content = "# 見出し\n\nこれは日本語の段落です。"
    response = client.post("/convert", data={"markdown_content": markdown_content})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["download_url"].startswith("/download/")


def test_preview_requires_content():
    response = client.post("/preview", data={"markdown_content": ""})
    assert response.status_code == 400
    data = response.json()
    assert "Markdown content is required" in data["detail"]


def test_preview_valid_markdown_returns_html():
    response = client.post("/preview", data={"markdown_content": "# Hello\n\n**World**"})
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/html")
    assert "<h1" in response.text
    assert "<strong>World</strong>" in response.text
    assert "@font-face" in response.text
    assert ".text-danger" in response.text
    assert "font-family: 'AppSans', 'Noto Sans CJK JP'" in response.text


def test_preview_allows_inline_style_attributes():
    html = client.post(
        "/preview",
        data={"markdown_content": "Before <span style=\"color:red;\">赤字</span> After"},
    ).text
    assert "<span style=\"color:red;\">赤字</span>" in html


def test_preview_allows_bootstrap_classes():
    html = client.post(
        "/preview",
        data={"markdown_content": "<div class=\"text-danger\">Danger</div>"},
    ).text
    assert "class=\"text-danger\"" in html
    assert ".text-danger" in html


def test_title_page_allows_html_break_tokens():
    payload = {
        "markdown_content": "# Body",
        "title_page": "true",
        "title_text": "Line1<br>Line2",
    }
    response = client.post("/preview", data=payload)
    assert response.status_code == 200
    assert "<h1 class=\"gw-title\">Line1<br />Line2</h1>" in response.text


def test_title_page_converts_newlines_to_breaks():
    payload = {
        "markdown_content": "# Body",
        "title_page": "true",
        "title_text": "Line1\nLine2",
    }
    response = client.post("/preview", data=payload)
    assert response.status_code == 200
    assert "<h1 class=\"gw-title\">Line1<br />Line2</h1>" in response.text


def test_preview_admonition_and_tasklist():
    md = dedent(
        """
        !!! note "注意"
            これは注意書きです。

        - [x] 完了
        - [ ] 未完了
        """
    )
    response = client.post("/preview", data={"markdown_content": md})
    assert response.status_code == 200
    text = response.text
    # Assert that the admonition container is present
    # アドモニションのコンテナが含まれているか確認する
    assert "admonition" in text
    # Verify task list checkboxes are rendered in HTML
    # タスクリストのチェックボックスがHTMLに出力されているか確認する
    assert "type=\"checkbox\"" in text


def test_magiclink_autolink():
    md = "Visit https://example.com for details."
    response = client.post("/preview", data={"markdown_content": md})
    assert response.status_code == 200
    assert '<a href="https://example.com"' in response.text


def test_preview_emoji_shortcode_unicode():
    md = ":warning: 注意"
    response = client.post("/preview", data={"markdown_content": md, "emoji_mode": "unicode"})
    assert response.status_code == 200
    # Ensure the Unicode warning icon is present
    # Unicodeの警告アイコンが含まれているか確認する
    assert "⚠" in response.text


def test_preview_emoji_off_removes_emoji():
    md = ":warning: 注意"
    response = client.post("/preview", data={"markdown_content": md, "emoji_mode": "off"})
    assert response.status_code == 200
    html = response.text
    # Ignore icons inside inline <style> and check only visible content
    # インライン<style>内のアイコンは除外し、画面に表示される領域のみを確認する
    cut = html.rfind("</style>")
    visible = html[cut + len("</style>") :] if cut != -1 else html
    assert "⚠" not in visible
