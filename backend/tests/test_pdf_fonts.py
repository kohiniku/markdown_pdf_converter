import pytest

from app.renderer import render_markdown_to_html

pytest.importorskip("weasyprint")

from weasyprint import HTML  # type: ignore  # noqa: E402


def _collect_runs(markdown: str):
    html, _ = render_markdown_to_html(markdown, title_page=False)
    document = HTML(string=html).render()
    runs = []
    page = document.pages[0]
    for node in page._page_box.descendants():  # type: ignore[attr-defined]
        text = getattr(node, "text", "")
        if not text:
            continue
        style = getattr(node, "style", None)
        if not style:
            continue
        try:
            weight = style["font_weight"]
            family = style["font_family"]
        except KeyError:
            continue
        runs.append((text, weight, family))
    return runs


def test_bold_text_uses_heavier_font_weight():
    runs = _collect_runs("Regular **Bold** text")
    bold_runs = [(text, weight, family) for text, weight, family in runs if text.strip() == "Bold"]
    assert bold_runs, "Bold text run not found in rendered output"
    assert all(weight >= 700 for _, weight, _ in bold_runs)
    assert any(any(fam == "AppSans" for fam in family) for _, _, family in bold_runs)


def test_regular_text_stays_normal_weight():
    runs = _collect_runs("Regular **Bold** text")
    normal_runs = [(text, weight) for text, weight, _ in runs if text.strip() == "Regular"]
    assert normal_runs, "Regular text run not found in rendered output"
    assert all(weight in (400, 500) for _, weight in normal_runs)
