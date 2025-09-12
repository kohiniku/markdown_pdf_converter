from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import markdown as md

from app.config import settings


@lru_cache(maxsize=1)
def get_theme_css() -> str:
    theme_path = Path(__file__).with_suffix("").parent / "themes" / "growi_v7.css"
    try:
        return theme_path.read_text(encoding="utf-8")
    except Exception:
        # very small safe fallback
        return (
            "body{font-family:'Noto Sans JP',sans-serif;line-height:1.7;color:#222;max-width:880px;margin:0 auto;padding:24px;}"
            "h1,h2,h3{color:#222;margin:1.2em 0 .6em}code{background:#f6f8fa;padding:.2em .4em;border-radius:4px}"
        )


def collapse_soft_newlines(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    out, buf = [], []

    import re

    re_blank = re.compile(r"^\s*$")
    re_fence = re.compile(r"^\s*(```|~~~)")
    re_indented_code = re.compile(r"^\s{4,}")
    re_heading = re.compile(r"^\s*#{1,6}\s+")
    re_list = re.compile(r"^\s*(?:[*+-]|\d+[\.)])\s+")
    re_blockquote = re.compile(r"^\s*>\s*")
    re_table = re.compile(r"^\s*\|")
    re_hr = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
    re_admon = re.compile(r"^\s*!!!\b")
    re_html = re.compile(r"^\s*<[/!?]?")

    def flush():
        nonlocal buf
        if buf:
            out.append(" ".join(s.strip() for s in buf))
            buf = []

    in_fence = False
    for raw in lines:
        line = raw.rstrip("\n")
        if in_fence:
            out.append(line)
            if re_fence.match(line):
                in_fence = False
            continue
        if re_fence.match(line):
            flush()
            in_fence = True
            out.append(line)
            continue

        if (
            re_blank.match(line)
            or re_indented_code.match(line)
            or re_heading.match(line)
            or re_blockquote.match(line)
            or re_table.match(line)
            or re_hr.match(line)
            or re_admon.match(line)
            or re_html.match(line)
        ):
            flush()
            out.append(line)
            continue

        if re_list.match(line):
            flush()
            if out and out[-1] != "":
                out.append("")
            out.append(line)
            continue

        buf.append(line)

    flush()
    return "\n".join(out)


def render_markdown_to_html(
    markdown_text: str,
    *,
    newline_to_space: Optional[bool] = None,
    font_size_px: Optional[int] = None,
    custom_css: Optional[str] = None,
    page_size: Optional[str] = None,
    orientation: Optional[str] = None,
    margin: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (html_document, css) where html_document is a full HTML page.

    The Markdown pipeline is tuned to approximate GROWI v7 rendering behavior
    (GFM-like lists, admonitions, tasklist, footnotes, tables, fences).
    """

    # Normalize GitHub-style callouts and :::admonitions into !!! admonitions
    markdown_text = _normalize_admonitions(markdown_text)

    if (newline_to_space is True) or (
        newline_to_space is None and settings.newline_as_space
    ):
        markdown_text = collapse_soft_newlines(markdown_text)

    extensions = [
        "admonition",
        "abbr",
        "attr_list",
        "def_list",
        "footnotes",
        "tables",
        "pymdownx.details",
        "pymdownx.superfences",
        "pymdownx.tasklist",
        "pymdownx.tilde",
        "pymdownx.mark",
        "pymdownx.betterem",
        "pymdownx.magiclink",
        "codehilite",
        "toc",
    ]
    extension_configs = {
        "codehilite": {"guess_lang": False, "linenums": False},
        "pymdownx.tasklist": {"custom_checkbox": True},
        "pymdownx.magiclink": {"repo_url_shortener": True, "hide_protocol": True},
        # Add a visible permalink similar to GROWI's heading anchors
        "toc": {"permalink": True, "permalink_class": "gw-heading-anchor"},
    }

    html_body = md.markdown(markdown_text, extensions=extensions, extension_configs=extension_configs)

    base_size = font_size_px if font_size_px is not None else settings.pdf_base_font_size
    base_css = f"body{{font-size:{base_size}px}}\n" if base_size else ""

    # Page setup CSS (@page)
    page_css = _build_page_css(
        page_size or settings.pdf_page_size_default,
        orientation or settings.pdf_page_orientation_default,
        margin or settings.pdf_page_margin_default,
    )
    page_vars_css = _build_page_vars_css(
        page_size or settings.pdf_page_size_default,
        orientation or settings.pdf_page_orientation_default,
        margin or settings.pdf_page_margin_default,
    )
    theme_css = custom_css if custom_css else get_theme_css()

    html_doc = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <style>{base_css}{page_css}{page_vars_css}{theme_css}</style>
      </head>
      <body class=\"gw-screen\">
        <div class=\"gw-page-wrapper\">
          <article class=\"gw-page\">
            <div class=\"gw-container\">{html_body}</div>
          </article>
        </div>
      </body>
    </html>
    """
    return html_doc, (base_css + theme_css)


def _build_page_css(size: str, orientation: str, margin: str) -> str:
    size = (size or "A4").strip()
    orient = (orientation or "portrait").strip().lower()
    if orient not in ("portrait", "landscape"):
        orient = "portrait"
    # Allow combined values like "A4 landscape"
    if "landscape" in size or "portrait" in size:
        size_spec = size
    else:
        size_spec = f"{size} {orient}".strip()

    margin_spec = margin.strip() if margin else settings.pdf_page_margin_default
    return f"@page{{size:{size_spec};margin:{margin_spec};}}\n"


def _build_page_vars_css(size: str, orientation: str, margin: str) -> str:
    w_mm, h_mm = _page_dimensions_mm(size)
    orient = (orientation or "portrait").strip().lower()
    if orient == "landscape":
        w_mm, h_mm = h_mm, w_mm

    # Convert to px using 96 dpi: 1in=96px, 1in=25.4mm
    def mm_to_px(mm: float) -> int:
        return int(round(mm / 25.4 * 96))

    w_px = mm_to_px(w_mm)
    h_px = mm_to_px(h_mm)
    margin_spec = margin.strip() if margin else settings.pdf_page_margin_default
    return f":root{{--page-width-px:{w_px}px;--page-height-px:{h_px}px;--page-margin:{margin_spec};}}\n"


def _page_dimensions_mm(size: str) -> tuple[float, float]:
    s = (size or "A4").strip().lower()
    # map common sizes (width x height in mm, portrait)
    sizes = {
        "a3": (297.0, 420.0),
        "a4": (210.0, 297.0),
        "a5": (148.0, 210.0),
        "letter": (215.9, 279.4),  # 8.5 x 11 in
        "legal": (215.9, 355.6),   # 8.5 x 14 in
    }
    # Support combined forms like "A4 landscape" by stripping the word
    base = s.replace("landscape", "").replace("portrait", "").strip()
    return sizes.get(base, sizes["a4"])  # default A4


def _normalize_admonitions(md: str) -> str:
    """Convert common admonition syntaxes to Python-Markdown's !!! form.

    Supports:
    - GitHub callouts: blockquotes with "> [!NOTE]" etc.
    - Triple-colon blocks: ":::note" ... ":::"
    """
    if not md:
        return md

    lines = md.splitlines()
    out: list[str] = []

    import re

    # GitHub callouts inside blockquotes
    callout_re = re.compile(r"^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|DANGER|INFO)\]\s*(.*)$", re.I)

    i = 0
    n = len(lines)
    while i < n:
        m = callout_re.match(lines[i])
        if m:
            kind = m.group(1).lower()
            # Gather following blockquote lines that are part of this block
            content: list[str] = []
            # First line may have trailing text after the tag, but typical syntax doesn't.
            trailing = m.group(2).strip()
            if trailing:
                content.append(trailing)

            i += 1
            while i < n:
                ln = lines[i]
                if not ln.lstrip().startswith('>'):
                    break
                # Strip one leading ">" and one optional space
                stripped = ln.lstrip()[1:]
                if stripped.startswith(' '):
                    stripped = stripped[1:]
                content.append(stripped)
                i += 1

            # Emit !!! admonition with indented content
            out.append(f"!!! {kind}")
            for c in content:
                out.append(f"    {c}")
            continue  # skip increment; already advanced i

        # Triple-colon admonitions :::note ... :::
        if lines[i].lstrip().startswith(':::'):
            # Parse opening
            opener = lines[i].lstrip()[3:].strip()
            # opener can be like 'note', 'note Title', etc.
            if opener:
                parts = opener.split(None, 1)
                typ = parts[0].lower()
                raw_title = parts[1] if len(parts) > 1 else None
                title = _strip_admonition_title_leading_emoji(raw_title) if raw_title else None
            else:
                typ = 'note'
                title = None

            i += 1
            body: list[str] = []
            while i < n and not lines[i].lstrip().startswith(':::'):
                body.append(lines[i])
                i += 1
            # Skip closing ':::' if present
            if i < n and lines[i].lstrip().startswith(':::'):
                i += 1

            title_part = f' "{title}"' if title else ''
            out.append(f"!!! {typ}{title_part}")
            for b in body:
                out.append(f"    {b}")
            continue

        # Default: passthrough
        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _strip_admonition_title_leading_emoji(title: str | None) -> str | None:
    if not title:
        return title
    t = title.strip()
    # Known emoji prefixes used in our CSS map or common aliases
    prefixes = [
        "⚠", "❗", "ℹ", "✎", "💡", "⛔",
        ":warning:", ":info:", ":bulb:", ":pencil:", ":exclamation:", ":no_entry:",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].lstrip(" -:|\t")
            break
    return t or None
