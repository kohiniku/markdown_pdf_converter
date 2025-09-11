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
    # Admonition container
    assert "admonition" in text
    # Tasklist checkboxes
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
    # Unicode warning sign should be present
    assert "⚠" in response.text


def test_preview_emoji_off_removes_emoji():
    md = ":warning: 注意"
    response = client.post("/preview", data={"markdown_content": md, "emoji_mode": "off"})
    assert response.status_code == 200
    assert "⚠" not in response.text
