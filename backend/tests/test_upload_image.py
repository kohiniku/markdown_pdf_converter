from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
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


def test_upload_image_rejects_large_files():
    upload_dir = Path(settings.upload_dir)
    existing_files = set(upload_dir.iterdir()) if upload_dir.exists() else set()

    too_large_bytes = settings.max_file_size + 1
    payload = b"\x00" * too_large_bytes
    files = {"file": ("huge.png", payload, "image/png")}

    res = client.post("/upload-image", files=files)
    assert res.status_code == 413
    assert res.json().get("detail") == "Image too large"

    remaining_files = set(upload_dir.iterdir()) if upload_dir.exists() else set()
    assert remaining_files == existing_files
