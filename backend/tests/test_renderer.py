import re

from app import renderer


def test_title_page_print_min_height_matches_available_area():
    html, _ = renderer.render_markdown_to_html(
        "",
        title_page=True,
        title_text="Sample",
    )

    match = re.search(
        r"@media print\{\.gw-title-page\{min-height:([0-9]+)px;height:\1px;", html
    )
    assert match, (
        "Expected numeric min-height and height declarations for print title page"
    )

    expected_height = _expected_available_height_px()
    assert int(match.group(1)) == expected_height


def test_image_width_attribute_is_reflected_in_style():
    html, _ = renderer.render_markdown_to_html(
        "![img](/assets/picture.png){width=200}\n",
        title_page=False,
    )
    assert 'width="200"' in html
    assert re.search(r"style=\"[^\"]*width:200px;", html)


def test_image_width_with_percentage_is_preserved():
    html, _ = renderer.render_markdown_to_html(
        "![img](/assets/picture.png){width=50%}\n",
        title_page=False,
    )
    assert re.search(r"style=\"[^\"]*width:50%;", html)


def test_double_space_line_break_preserved_when_collapsed():
    html, _ = renderer.render_markdown_to_html(
        "First line  \nSecond line",
        newline_to_space=True,
    )
    assert "First line<br />" in html
    assert "Second line" in html


def test_preview_page_size_uses_continuous_layout():
    html, css = renderer.render_markdown_to_html(
        "# Preview Flow",
        page_size="preview",
        for_preview=True,
    )
    assert "gw-preview-flow" in html
    assert "gw-preview-scroll" in html
    assert 'class="gw-page-wrapper"' not in html
    assert "function paginate" not in html
    assert ".gw-preview-flow" in css
    assert "repeating-linear-gradient" in css


def test_force_preview_layout_for_regular_page_size():
    html, css = renderer.render_markdown_to_html(
        "# Simplified Preview",
        page_size="A4",
        preview_flow_override=True,
        for_preview=True,
    )
    assert "gw-preview-flow" in html
    assert '<div class="gw-page-wrapper">' not in html
    assert ".gw-preview-flow" in css
    assert "repeating-linear-gradient" in css


def test_paginated_preview_builds_static_template():
    html, _ = renderer.render_markdown_to_html(
        "# Body",
        page_size="A4",
        for_preview=True,
    )
    assert '<template id="gw-preview-template">' in html
    assert 'data-preview-mode="static"' in html
    assert ".gw-page-slice" in html


def test_paginated_preview_applies_per_page_margins():
    _, css = renderer.render_markdown_to_html(
        "# Body",
        page_size="A4",
        for_preview=True,
    )
    assert '.gw-page-wrapper[data-preview-mode="static"] .gw-page-outer>.gw-page' in css
    assert "box-sizing:border-box;padding:var(--page-margin-top" in css


def _expected_available_height_px() -> int:
    page_size = renderer.settings.pdf_page_size_default
    orientation = renderer.settings.pdf_page_orientation_default
    margin = renderer.settings.pdf_page_margin_default

    width_mm, height_mm = renderer._page_dimensions_mm(page_size)
    if (orientation or "portrait").strip().lower() == "landscape":
        width_mm, height_mm = height_mm, width_mm

    page_height_px = renderer._mm_to_px(height_mm)
    top, _, bottom, _ = renderer._expand_margin_shorthand(margin)

    top_px = renderer._css_length_to_px(top) or 0
    bottom_px = renderer._css_length_to_px(bottom) or 0

    return max(page_height_px - int(round(top_px + bottom_px)), 0)
