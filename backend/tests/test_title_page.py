from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_preview_includes_title_page_when_enabled():
    res = client.post(
        "/preview",
        data={
            "markdown_content": "# Hello\n\nBody",
            "title_page": "true",
            "title_text": "My Talk",
            "title_date": "2025-09-12",
            "title_name": "Taro Yamada",
        },
    )
    assert res.status_code == 200
    html = res.text
    assert 'class="gw-title-page"' in html
    assert 'My Talk' in html
    assert '2025-09-12' in html
    assert 'Taro Yamada' in html


def test_preview_omits_title_page_when_not_requested():
    res = client.post(
        "/preview",
        data={
            "markdown_content": "# No Title\n\nText",
        },
    )
    assert res.status_code == 200
    assert 'class="gw-title-page"' not in res.text


def test_convert_accepts_title_page_params():
    res = client.post(
        "/convert",
        data={
            "markdown_content": "# Doc",
            "title_page": "true",
            "title_text": "Deck",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("success") is True
