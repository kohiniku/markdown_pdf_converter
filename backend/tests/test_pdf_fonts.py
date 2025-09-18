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
        color_space = None
        color_coords = None
        color_alpha = None
        try:
            color_obj = style["color"]
            color_space = getattr(color_obj, "space", None)
            color_coords = tuple(color_obj.coordinates)
            color_alpha = getattr(color_obj, "alpha", None)
        except Exception:
            pass
        runs.append(
            {
                "text": text,
                "weight": weight,
                "family": family,
                "color_space": color_space,
                "color_coords": color_coords,
                "color_alpha": color_alpha,
            }
        )
    return runs


def test_bold_text_uses_heavier_font_weight():
    runs = _collect_runs("Regular **Bold** text")
    bold_runs = [run for run in runs if run["text"].strip() == "Bold"]
    assert bold_runs, "Bold text run not found in rendered output"
    assert all(run["weight"] >= 700 for run in bold_runs)
    assert any("AppSans" in run["family"] for run in bold_runs)


def test_regular_text_stays_normal_weight():
    runs = _collect_runs("Regular **Bold** text")
    normal_runs = [run for run in runs if run["text"].strip() == "Regular"]
    assert normal_runs, "Regular text run not found in rendered output"
    assert all(run["weight"] in (400, 500) for run in normal_runs)


def test_inline_style_color_applied():
    runs = _collect_runs("Inline <span style='color:#ff0000'>Red</span> text")
    red_runs = [run for run in runs if run["text"].strip() == "Red"]
    assert red_runs, "Styled span text not found in rendered output"
    for run in red_runs:
        assert run["color_space"] == "srgb"
        r, g, b = run["color_coords"]
        assert pytest.approx(r, rel=1e-3) == 1.0
        assert pytest.approx(g, rel=1e-3) == 0.0
        assert pytest.approx(b, rel=1e-3) == 0.0
        assert pytest.approx(run["color_alpha"], rel=1e-3) == 1.0


def test_bootstrap_text_danger_color():
    runs = _collect_runs("<span class='text-danger'>Danger</span>")
    danger_runs = [run for run in runs if run["text"].strip() == "Danger"]
    assert danger_runs, "Bootstrap-styled text not found in rendered output"
    for run in danger_runs:
        assert run["color_space"] == "srgb"
        r, g, b = run["color_coords"]
        assert pytest.approx(r, rel=1e-3) == 0.8627
        assert pytest.approx(g, rel=1e-3) == 0.2078
        assert pytest.approx(b, rel=1e-3) == 0.2706
        assert pytest.approx(run["color_alpha"], rel=1e-3) == 1.0
