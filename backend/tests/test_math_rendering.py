import base64
import re
import xml.etree.ElementTree as ET

import pytest

from app.renderer import render_markdown_to_html


def math_images(html):
    return re.findall(r'<img[^>]+class="math-svg"[^>]*>', html)


@pytest.mark.parametrize(
    "formula",
    [
        r"\(x_{1,t}-\beta x_{2,t}\)",
        r"\[h=\frac{\log(1/2)}{\log\phi}\]",
        r"$$h=\frac{\log(1/2)}{\log\phi}$$",
    ],
)
def test_latex_is_static_svg(formula):
    html, _ = render_markdown_to_html(
        "前の段落。\n\n" + formula + "\n\n後の段落。", newline_to_space=False
    )
    images = math_images(html)
    assert len(images) == 1
    svg_data = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"', images[0]).group(
        1
    )
    svg = ET.fromstring(base64.b64decode(svg_data))
    assert svg.tag.endswith("svg")
    assert any(el.tag.endswith("path") for el in svg.iter())
    assert "alt=" in images[0]
    assert "<script" not in html


def test_code_and_money_are_not_math():
    html, _ = render_markdown_to_html(
        r"`\(code\)` と $20 または $30。" + "\n\n```latex\n" + r"\[x^2\]" + "\n```"
    )
    assert not math_images(html)
    assert "$20" in html and "$30" in html
    assert r"\(code\)" in html


@pytest.mark.parametrize(
    "text",
    [
        "株価は$150から$180に上昇した。",
        "売上は$1.2B、営業利益は$300Mだった。",
        "costs $5-$10 per unit",
        "誤差項 $e_t$ はドル記号の行内数式として扱わない。",
    ],
)
def test_single_dollar_is_not_math(text):
    html, _ = render_markdown_to_html(text)
    assert not math_images(html)
    assert "math-error" not in html


@pytest.mark.parametrize("collapse", [False, True])
def test_aligned_multiline_and_table(collapse):
    source = r"""\[
\begin{aligned}
x_t &= \alpha x_{t-1}+u_t \\
y_t &= \beta y_{t-1}+v_t
\end{aligned}
\]

| 変数 | 式 |
|---|---|
| 半減期 | \(h=\frac{\log(1/2)}{\log\phi}\) |
"""
    html, _ = render_markdown_to_html(source, newline_to_space=collapse)
    assert len(math_images(html)) == 2
    assert "math-error" not in html
    assert "<table>" in html


def test_bad_formula_stays_visible():
    html, _ = render_markdown_to_html(r"\[\frac{\]")
    assert "math-error" in html
    assert r"\frac{" in html
    assert not math_images(html)


def test_inline_math_stays_on_the_same_pdf_line():
    from weasyprint import HTML
    from weasyprint.formatting_structure.boxes import (
        LineBox,
        InlineReplacedBox,
        TextBox,
    )

    html, _ = render_markdown_to_html(
        r"前の文字 \(x_t\) 後の文字", newline_to_space=False
    )
    document = HTML(string=html).render()
    for page in document.pages:
        for box in page._page_box.descendants():
            if not isinstance(box, LineBox):
                continue
            children = list(box.descendants())
            text = "".join(b.text for b in children if isinstance(b, TextBox))
            if "前の文字" in text and "後の文字" in text:
                assert any(isinstance(b, InlineReplacedBox) for b in children)
                return
    pytest.fail("行内数式が前後の文章と同じPDF行にない")


@pytest.mark.parametrize("collapse", [False, True])
def test_math_newlines_preserve_comments(collapse):
    source = "\\[\nx=1 % comment\n+2\n\\]"
    html, _ = render_markdown_to_html(source, newline_to_space=collapse)
    comparison, _ = render_markdown_to_html(source, newline_to_space=False)
    image = math_images(html)[0]
    reference = math_images(comparison)[0]
    assert re.search('src="([^"]+)"', image).group(1) == re.search(
        'src="([^"]+)"', reference
    ).group(1)
    assert "math-error" not in html


@pytest.mark.parametrize("collapse", [False, True])
@pytest.mark.parametrize(
    "opening,closing",
    [(r"\[", r"\]"), ("$$", "$$"), (r"\begin{align}", r"\end{align}")],
)
def test_display_math_without_surrounding_blank_lines(collapse, opening, closing):
    source = f"前の文。\n{opening}\nx=1\n{closing}\n後の文。"
    html, _ = render_markdown_to_html(source, newline_to_space=collapse)
    assert len(math_images(html)) == 1
    assert "前の文。" in html and "後の文。" in html


@pytest.mark.parametrize("collapse", [False, True])
def test_multiline_code_span_not_rendered(collapse):
    html, _ = render_markdown_to_html(
        "`example\n\\[x=1\\]\nend`", newline_to_space=collapse
    )
    assert not math_images(html)
    assert "<code>example" in html
    assert r"\[x=1\]" in html


def test_multiline_inline_comments_preserved():
    source = "\\(x=1 % comment\n+2\\)"
    actual, _ = render_markdown_to_html(source, newline_to_space=True)
    reference, _ = render_markdown_to_html(source, newline_to_space=False)
    assert len(math_images(actual)) == 1
    assert re.search('src="([^"]+)"', math_images(actual)[0]).group(1) == re.search(
        'src="([^"]+)"', math_images(reference)[0]
    ).group(1)


@pytest.mark.parametrize("collapse", [False, True])
def test_math_inside_callout(collapse):
    source = ":::note\nbefore\n\\[\nx=1\n\\]\nafter\n:::"
    html, _ = render_markdown_to_html(source, newline_to_space=collapse)
    assert len(math_images(html)) == 1
    assert 'class="admonition note"' in html
    assert 'class="codehilite"' not in html
