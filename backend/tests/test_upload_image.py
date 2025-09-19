from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_image_and_serve_static():
    # Minimal 1x1 PNG byte sequence
    # 最小構成の1x1 PNGバイト列
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x05\x01\x02\xa2\xfd\xd5\xb2\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("tiny.png", png_bytes, "image/png")}
    res = client.post("/upload-image", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data.get("success") is True
    url = data.get("url")
    assert url and url.startswith("/assets/")

    # Ensure the uploaded file is served via StaticFiles mount
    # StaticFilesのマウント経由で取得できることも検証する
    res2 = client.get(url)
    assert res2.status_code == 200
    assert res2.headers.get("content-type", "").startswith("image/")
