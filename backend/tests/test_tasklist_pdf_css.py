from textwrap import dedent

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_preview_contains_print_tasklist_css():
    md = dedent(
        """
        - [x] 完了
        - [ ] 未完了
        """
    )
    res = client.post("/preview", data={"markdown_content": md})
    assert res.status_code == 200
    html = res.text
    # Our print-safe checkbox rules for pymdownx custom markup or GitHub-like fallback
    assert (
        'input[type="checkbox"] + .task-list-indicator::before' in html
        or 'input.task-list-item-checkbox + label::before' in html
    )

