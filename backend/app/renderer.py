from __future__ import annotations

import base64
from functools import lru_cache
from html import escape as _escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional, Tuple

import re

import markdown as md

from app.config import settings


_FALLBACK_BOOTSTRAP_CSS = (
    ".text-primary{color:#0d6efd!important;}\n"
    ".text-secondary{color:#6c757d!important;}\n"
    ".text-success{color:#198754!important;}\n"
    ".text-info{color:#0dcaf0!important;}\n"
    ".text-warning{color:#ffc107!important;}\n"
    ".text-danger{color:#dc3545!important;}\n"
    ".text-light{color:#f8f9fa!important;}\n"
    ".text-dark{color:#212529!important;}\n"
    ".bg-primary{background-color:#0d6efd!important;color:#fff!important;}\n"
    ".bg-secondary{background-color:#6c757d!important;color:#fff!important;}\n"
    ".bg-success{background-color:#198754!important;color:#fff!important;}\n"
    ".bg-info{background-color:#0dcaf0!important;color:#000!important;}\n"
    ".bg-warning{background-color:#ffc107!important;color:#000!important;}\n"
    ".bg-danger{background-color:#dc3545!important;color:#fff!important;}\n"
    ".bg-light{background-color:#f8f9fa!important;color:#000!important;}\n"
    ".bg-dark{background-color:#212529!important;color:#fff!important;}\n"
    ".badge{display:inline-block;padding:.35em .65em;font-size:.75em;font-weight:700;line-height:1;color:#fff;background-color:#6c757d;border-radius:.375rem;}\n"
    ".badge.bg-danger{background-color:#dc3545!important;}\n"
    ".badge.bg-success{background-color:#198754!important;}\n"
    ".border{border:1px solid #dee2e6!important;}\n"
    ".border-0{border:0!important;}\n"
    ".rounded{border-radius:.375rem!important;}\n"
    ".d-flex{display:flex!important;}\n"
    ".d-inline-flex{display:inline-flex!important;}\n"
    ".d-none{display:none!important;}\n"
    ".flex-column{flex-direction:column!important;}\n"
    ".flex-row{flex-direction:row!important;}\n"
    ".justify-content-center{justify-content:center!important;}\n"
    ".align-items-center{align-items:center!important;}\n"
    ".p-3{padding:1rem!important;}\n"
    ".m-3{margin:1rem!important;}\n"
    ".table{width:100%;margin-bottom:1rem;color:inherit;vertical-align:top;border-color:#dee2e6;}\n"
    ".table td,.table th{padding:.5rem;border-color:inherit;}\n"
)

_FALLBACK_THEME_CSS = (
    "body{font-family:'AppSans','Noto Sans CJK JP','Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic',Meiryo,'Segoe UI','Helvetica Neue',Arial,sans-serif;font-synthesis:none;line-height:1.7;color:#222;max-width:880px;margin:0 auto;padding:24px;}"
    "h1,h2,h3{color:#222;margin:1.2em 0 .6em;font-weight:700;}"
    "strong,b{font-weight:700;font-family:'AppSans','Noto Sans CJK JP','Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic',Meiryo,'Segoe UI','Helvetica Neue',Arial,sans-serif;}"
    "code{background:#f6f8fa;padding:.2em .4em;border-radius:4px}"
)

_FALLBACK_FONT_FACE = (
    "@font-face{font-family:'AppSans';font-style:normal;font-weight:400;"  # noqa: E501
    "src:local('Noto Sans CJK JP'),local('Noto Sans JP'),local('Yu Gothic'),sans-serif;font-display:swap;}"
    "@font-face{font-family:'AppSans';font-style:normal;font-weight:700;"
    "src:local('Noto Sans CJK JP Bold'),local('Noto Sans JP Bold'),local('Yu Gothic Bold'),sans-serif;font-display:swap;}"
)


def get_theme_css() -> str:
    themes_dir = Path(__file__).with_suffix("").parent / "themes"
    theme_path = themes_dir / "growi_v7.css"
    bootstrap_path = themes_dir / "bootstrap5.min.css"
    custom_path = themes_dir / "custom_style.css"
    font_regular = themes_dir / "NotoSansJP-Regular.otf"
    font_bold = themes_dir / "NotoSansJP-Bold.otf"

    try:
        theme_mtime = theme_path.stat().st_mtime
    except Exception:
        theme_mtime = -1.0

    try:
        bootstrap_mtime = bootstrap_path.stat().st_mtime
    except Exception:
        bootstrap_mtime = -1.0

    try:
        custom_mtime = custom_path.stat().st_mtime
    except Exception:
        custom_mtime = -1.0

    try:
        regular_mtime = font_regular.stat().st_mtime
    except Exception:
        regular_mtime = -1.0

    try:
        bold_mtime = font_bold.stat().st_mtime
    except Exception:
        bold_mtime = -1.0

    return _load_theme_css_cached(
        (
            str(theme_path),
            theme_mtime,
            str(bootstrap_path),
            bootstrap_mtime,
            str(custom_path),
            custom_mtime,
            str(font_regular),
            regular_mtime,
            str(font_bold),
            bold_mtime,
        )
    )


@lru_cache(maxsize=8)
def _load_theme_css_cached(
    cache_key: tuple[str, float, str, float, str, float, str, float, str, float]
) -> str:
    (
        theme_path_str,
        _theme_mtime,
        bootstrap_path_str,
        _bootstrap_mtime,
        custom_path_str,
        _custom_mtime,
        font_regular_str,
        _reg_mtime,
        font_bold_str,
        _bold_mtime,
    ) = cache_key
    css_parts: list[str] = []

    font_faces = _build_font_face_css(Path(font_regular_str), Path(font_bold_str))
    if font_faces:
        css_parts.append(font_faces)
    else:
        css_parts.append("".join(_FALLBACK_FONT_FACE))

    bootstrap_path = Path(bootstrap_path_str)
    try:
        css_parts.append(bootstrap_path.read_text(encoding="utf-8"))
    except Exception:
        css_parts.append("".join(_FALLBACK_BOOTSTRAP_CSS))

    theme_path = Path(theme_path_str)
    try:
        css_parts.append(theme_path.read_text(encoding="utf-8"))
    except Exception:
        css_parts.append("".join(_FALLBACK_THEME_CSS))

    custom_path = Path(custom_path_str)
    try:
        custom_css = custom_path.read_text(encoding="utf-8")
        conflicts = _detect_custom_css_conflicts(custom_css)
        if conflicts:
            notice = (
                "/* WARNING: custom_style.css overrides {}. "
                "GUI controls for these settings may not have effect. */\n"
            ).format(
                ", ".join(conflicts)
            )
            css_parts.append(notice + custom_css)
        else:
            css_parts.append(custom_css)
    except Exception:
        # Custom CSS is optional; missing file is acceptable.
        pass

    return "\n".join(css_parts)


def _detect_custom_css_conflicts(css_text: str) -> list[str]:
    conflicts: list[str] = []
    lowered = css_text.lower()
    if "@page" in lowered:
        conflicts.append("page size")
    if re.search(r"body\s*\{[^}]*font-size", lowered):
        conflicts.append("font size")
    return conflicts


def _build_font_face_css(font_regular: Path, font_bold: Path) -> str:
    parts: list[str] = []
    for weight, path in ((400, font_regular), (700, font_bold)):
        try:
            data = path.read_bytes()
        except Exception:
            return ""
        encoded = base64.b64encode(data).decode("ascii")
        parts.append(
            "@font-face{"  # noqa: E501
            "font-family:'AppSans';font-style:normal;"
            f"font-weight:{weight};src:url(data:font/otf;base64,{encoded}) format('opentype');"
            "font-display:swap;}"
        )
    return "".join(parts)


_RE_FONT_OPEN = re.compile(r"<font\b([^>]*)>", re.IGNORECASE)
_RE_FONT_CLOSE = re.compile(r"</font>", re.IGNORECASE)
_RE_ATTR = re.compile(r"(\w+)\s*=\s*(\".*?\"|'.*?'|[^\s>]+)")


def _convert_deprecated_font_tags(html_fragment: str) -> str:
    if "<font" not in html_fragment.lower():
        return html_fragment

    def repl(match: re.Match[str]) -> str:
        raw_attrs = match.group(1)
        attrs = []
        style_parts: list[str] = []
        color_value: Optional[str] = None
        for attr_match in _RE_ATTR.finditer(raw_attrs):
            name = attr_match.group(1).strip()
            value = attr_match.group(2).strip()
            lower_name = name.lower()
            if lower_name == "color":
                color_value = value.strip("'\"")
                continue
            if lower_name == "style":
                style_parts.append(value.strip("'\""))
                continue
            attrs.append(f"{name}={value}")

        if color_value:
            style_parts.append(f"color:{color_value}")
        if style_parts:
            attrs.append(f'style="{";".join(style_parts)}"')

        attr_str = " ".join(attrs).strip()
        if attr_str:
            return f"<span {attr_str}>"
        return "<span>"

    html_fragment = _RE_FONT_OPEN.sub(repl, html_fragment)
    html_fragment = _RE_FONT_CLOSE.sub("</span>", html_fragment)
    return html_fragment


def _ensure_block_spacing(md: str) -> str:
    if not md:
        return md
    lines = md.splitlines()
    out: list[str] = []
    in_fence = False
    fence_delim = ""
    prev_was_table = False
    for line in lines:
        stripped = line.strip()

        fence_start = stripped[:3] if len(stripped) >= 3 else stripped
        if fence_start in ("```", "~~~"):
            out.append(line)
            if in_fence and fence_start == fence_delim:
                in_fence = False
                fence_delim = ""
            else:
                in_fence = True
                fence_delim = fence_start
            continue

        if in_fence:
            out.append(line)
            continue

        is_hr = stripped in {"---", "***", "___"}
        is_table = stripped.startswith("|") and stripped.count("|") >= 2

        if (is_hr or is_table) and out:
            prev = out[-1]
            if prev.strip() and prev != "" and not (is_table and prev_was_table):
                out.append("")

        out.append(line)
        prev_was_table = is_table

    return "\n".join(out)


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
    # Title page options (for slide/cover page)
    title_page: Optional[bool] = None,
    title_text: Optional[str] = None,
    title_date: Optional[str] = None,
    title_author: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (html_document, css) where html_document is a full HTML page.

    The Markdown pipeline is tuned to approximate GROWI v7 rendering behavior
    (GFM-like lists, admonitions, tasklist, footnotes, tables, fences).
    """

    markdown_text = _replace_reserved_page_breaks(markdown_text)

    # Normalize GitHub-style callouts and :::admonitions into !!! admonitions
    # Also optionally collapse soft newlines inside admonition bodies if requested.
    _collapse = (newline_to_space is True) or (
        newline_to_space is None and settings.newline_as_space
    )
    markdown_text = _normalize_admonitions(markdown_text, collapse_inside=_collapse)

    markdown_text = _ensure_block_spacing(markdown_text)

    if _collapse:
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
    html_body = _convert_deprecated_font_tags(html_body)

    # Optional title page block (cover slide). Insert before markdown body.
    title_block = _build_title_page_html(
        enabled=bool(title_page),
        title=title_text or "",
        date=title_date or "",
        author=title_author or "",
    )
    if title_block:
        html_body = title_block + html_body

    html_body = _normalize_image_widths(html_body)

    base_size = font_size_px if font_size_px is not None else settings.pdf_base_font_size
    base_css = f"body{{font-size:{base_size}px}}\n" if base_size else ""

    resolved_page_size = page_size or settings.pdf_page_size_default
    resolved_orientation = orientation or settings.pdf_page_orientation_default
    resolved_margin = margin or settings.pdf_page_margin_default

    # Page setup CSS (@page)
    page_css = _build_page_css(
        resolved_page_size,
        resolved_orientation,
        resolved_margin,
    )
    page_vars_css = _build_page_vars_css(
        resolved_page_size,
        resolved_orientation,
        resolved_margin,
    )
    theme_css = custom_css if custom_css else get_theme_css()
    title_css = _build_title_css(
        resolved_page_size,
        resolved_orientation,
        resolved_margin,
    )
    preview_script = (
        "<script>(function(){\n"
        "var SRC_HTML=null;\n"
        "function paginate(){\n"
        "  var wrapper=document.querySelector('.gw-page-wrapper');\n"
        "  if(!wrapper) return;\n"
        "  var source=null;\n"
        "  if(!SRC_HTML){\n"
        "    var first=wrapper.querySelector('.gw-page'); if(!first) return;\n"
        "    var content=first.querySelector('.gw-container'); if(!content) return;\n"
        "    SRC_HTML=content.innerHTML;\n"
        "  }\n"
        "  source=document.createElement('div'); source.innerHTML=SRC_HTML;\n"
        "  var nodes=Array.prototype.slice.call(source.childNodes);\n"
        "  var pages=document.createElement('div');pages.className='gw-pages';\n"
        "  wrapper.innerHTML='';wrapper.appendChild(pages);\n"
        "  function makePage(){\n"
        "    var outer=document.createElement('div');outer.className='gw-page-outer';\n"
        "    var pg=document.createElement('article');pg.className='gw-page';\n"
        "    var cont=document.createElement('div');cont.className='gw-container';\n"
        "    pg.appendChild(cont);outer.appendChild(pg);pages.appendChild(outer);\n"
        "    return {outer:outer, pg:pg, cont:cont};\n"
        "  }\n"
        "  var cur=makePage();\n"
        "  function fits(){return cur.pg.scrollHeight <= cur.pg.clientHeight + 0.5;}\n"
        "  function copyAttributes(src,dest){\n"
        "    if(!src||!src.attributes) return;\n"
        "    for(var i=0;i<src.attributes.length;i++){ var attr=src.attributes[i]; dest.setAttribute(attr.name, attr.value); }\n"
        "  }\n"
        "  function createTableShell(table){\n"
        "    var shell=table.cloneNode(false);\n"
        "    var child=table.firstElementChild;\n"
        "    var colgroups=[];\n"
        "    while(child){\n"
        "      if(child.tagName==='COLGROUP'){ colgroups.push(child); }\n"
        "      child=child.nextElementSibling;\n"
        "    }\n"
        "    for(var i=0;i<colgroups.length;i++){ shell.appendChild(colgroups[i].cloneNode(true)); }\n"
        "    if(table.tHead){ shell.appendChild(table.tHead.cloneNode(true)); }\n"
        "    var currentBody=null;\n"
        "    var currentTemplate=null;\n"
        "    var lastRow=null;\n"
        "    var footerNode=null;\n"
        "    return {\n"
        "      table:shell,\n"
        "      ensureBody:function(template){\n"
        "        if(!currentBody || (template && template!==currentTemplate)){\n"
        "          currentBody=document.createElement('tbody');\n"
        "          if(template && template.tagName==='TBODY'){ copyAttributes(template,currentBody); }\n"
        "          shell.appendChild(currentBody);\n"
        "          currentTemplate=template;\n"
        "        }\n"
        "      },\n"
        "      appendRow:function(row,template){\n"
        "        this.ensureBody(template);\n"
        "        currentBody.appendChild(row);\n"
        "        lastRow=row;\n"
        "      },\n"
        "      removeLastRow:function(){\n"
        "        if(lastRow && currentBody && lastRow.parentNode===currentBody){\n"
        "          currentBody.removeChild(lastRow);\n"
        "          if(!currentBody.childElementCount){\n"
        "            shell.removeChild(currentBody);\n"
        "            currentBody=null;\n"
        "            currentTemplate=null;\n"
        "          }\n"
        "        }\n"
        "        lastRow=null;\n"
        "      },\n"
        "      appendFooter:function(node){\n"
        "        if(footerNode && footerNode.parentNode===shell){ shell.removeChild(footerNode); }\n"
        "        footerNode=node;\n"
        "        if(footerNode){ shell.appendChild(footerNode); }\n"
        "      },\n"
        "      removeFooter:function(){\n"
        "        if(footerNode && footerNode.parentNode===shell){ shell.removeChild(footerNode); }\n"
        "        footerNode=null;\n"
        "      },\n"
        "      hasBody:function(){ return !!currentBody; }\n"
        "    };\n"
        "  }\n"
        "  function paginateTable(table){\n"
        "    if(!table || !table.tBodies || !table.tBodies.length){\n"
        "      var clone=table.cloneNode(true);\n"
        "      cur.cont.appendChild(clone);\n"
        "      if(!fits()){\n"
        "        cur.cont.removeChild(clone);\n"
        "        cur=makePage();\n"
        "        cur.cont.appendChild(clone);\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    var foot=table.tFoot ? table.tFoot.cloneNode(true) : null;\n"
        "    var sections=[];\n"
        "    for(var b=0;b<table.tBodies.length;b++){\n"
        "      var body=table.tBodies[b];\n"
        "      var rows=Array.prototype.slice.call(body.rows||[]);\n"
        "      if(!rows.length) continue;\n"
        "      for(var r=0;r<rows.length;r++){\n"
        "        sections.push({row: rows[r].cloneNode(true), template: body});\n"
        "      }\n"
        "    }\n"
        "    if(!sections.length){\n"
        "      var emptyClone=table.cloneNode(true);\n"
        "      cur.cont.appendChild(emptyClone);\n"
        "      if(!fits()){\n"
        "        cur.cont.removeChild(emptyClone);\n"
        "        cur=makePage();\n"
        "        cur.cont.appendChild(emptyClone);\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    function newShell(){\n"
        "      var shell=createTableShell(table);\n"
        "      cur.cont.appendChild(shell.table);\n"
        "      return shell;\n"
        "    }\n"
        "    var shell=newShell();\n"
        "    for(var s=0;s<sections.length;s++){\n"
        "      var spec=sections[s];\n"
        "      shell.appendRow(spec.row, spec.template);\n"
        "      if(!fits()){\n"
        "        shell.removeLastRow();\n"
        "        cur=makePage();\n"
        "        shell=newShell();\n"
        "        shell.appendRow(spec.row, spec.template);\n"
        "      }\n"
        "    }\n"
        "    if(foot){\n"
        "      shell.appendFooter(foot.cloneNode(true));\n"
        "      if(!fits()){\n"
        "        shell.removeFooter();\n"
        "        cur=makePage();\n"
        "        shell=newShell();\n"
        "        shell.appendFooter(foot.cloneNode(true));\n"
        "      }\n"
        "    }\n"
      "  }\n"
        "  for(var i=0;i<nodes.length;i++){\n"
        "    var node=nodes[i];\n"
        "    if(node.nodeType===1 && node.classList && node.classList.contains('gw-page-break')){\n"
        "      if(cur.cont.childNodes.length===0) continue;\n"
        "      cur=makePage();\n"
        "      continue;\n"
        "    }\n"
        "    if(node.nodeType===1 && node.tagName && node.tagName.toLowerCase()==='table'){\n"
        "      paginateTable(node);\n"
        "      continue;\n"
        "    }\n"
        "    var toAdd=node.cloneNode(true);\n"
        "    cur.cont.appendChild(toAdd);\n"
        "    if(!fits()){\n"
        "      cur.cont.removeChild(toAdd);\n"
        "      cur=makePage();\n"
        "      cur.cont.appendChild(toAdd);\n"
        "    }\n"
        "  }\n"
        "}\n"
        "function scalePages(){\n"
        "  var wrapper=document.querySelector('.gw-page-wrapper');\n"
        "  if(!wrapper) return;\n"
        "  var root=document.documentElement;\n"
        "  var cs=getComputedStyle(root);\n"
        "  var pageWidth=parseFloat(cs.getPropertyValue('--page-width-px'))||794;\n"
        "  var avail=wrapper.clientWidth - 32;\n"
        "  var scale=1; if(pageWidth>0){ scale=Math.min(1, Math.max(0.35, avail/pageWidth)); }\n"
        "  var list=wrapper.querySelectorAll('.gw-page-outer');\n"
        "  for(var i=0;i<list.length;i++){ list[i].style.setProperty('--scale', String(scale)); }\n"
        "}\n"
        "function init(){paginate(); scalePages(); window.addEventListener('resize', scalePages);\n"
        "  var imgs=document.images||[]; for(var k=0;k<imgs.length;k++){ imgs[k].addEventListener('load', function(){ paginate(); scalePages(); }); }\n"
        "}\n"
        "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded', init);}else{init();}\n"
        "})();</script>"
    )

    html_doc = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <style>{theme_css}{title_css}{base_css}{page_css}{page_vars_css}</style>
      </head>
      <body class=\"gw-screen\">
        <div class=\"gw-page-wrapper\">
          <article class=\"gw-page\">
            <div class=\"gw-container\">{html_body}</div>
          </article>
        </div>
        {preview_script}
      </body>
    </html>
    """
    combined_css = theme_css + title_css + base_css + page_css + page_vars_css
    return html_doc, combined_css


def _build_title_css(size: str, orientation: str, margin: str) -> str:
    """CSS for the generated title page block.

    - Centers contents vertically on a single page in preview and print
    - Forces a page break after the title block when printing
    - Uses page var CSS custom properties for consistent sizing in preview
    """
    margin_spec = margin.strip() if margin else settings.pdf_page_margin_default
    margin_top, _, margin_bottom, _ = _expand_margin_shorthand(margin_spec)

    page_width_mm, page_height_mm = _page_dimensions_mm(size)
    orient = (orientation or "portrait").strip().lower()
    if orient == "landscape":
        page_width_mm, page_height_mm = page_height_mm, page_width_mm

    page_height_px = _mm_to_px(page_height_mm)

    default_top, _, default_bottom, _ = _expand_margin_shorthand(settings.pdf_page_margin_default)
    margin_top_px = _css_length_to_px(margin_top)
    margin_bottom_px = _css_length_to_px(margin_bottom)
    if margin_top_px is None:
        margin_top_px = _css_length_to_px(default_top) or 0
    if margin_bottom_px is None:
        margin_bottom_px = _css_length_to_px(default_bottom) or 0

    total_margin_px = int(round(margin_top_px + margin_bottom_px))
    available_height_px = max(page_height_px - total_margin_px, 0)
    screen_min_height = (
        "calc(var(--page-height-px, "
        f"{page_height_px}px) - (var(--page-margin-top, {margin_top}) + var(--page-margin-bottom, {margin_bottom})))"
    )

    return (
        ".gw-title-page{"
        f"min-height:{available_height_px}px;"
        "display:flex;align-items:center;justify-content:center;"
        "text-align:center;padding:0 8mm;}"
        "@media screen{.gw-title-page{"
        f"min-height:{screen_min_height};"
        "}}"
        "@media print{.gw-title-page{"
        f"min-height:{available_height_px}px;height:{available_height_px}px;"
        "break-after: page;page-break-after: always;}}"
        ".gw-title-page .gw-title{font-size:5.0em;font-weight:800;margin:0;color:#111;}"
        ".gw-title-page .gw-sub{margin-top:1.1em;color:#555;font-size:1.3em;line-height:1.6;display:inline-flex;gap:.8em;align-items:baseline;justify-content:center;flex-wrap:wrap;}"
        ".gw-title-page .gw-sub > * + *::before{content:'\u00B7';margin:0 .25em;color:#99a1ad;}"
        "@media (prefers-color-scheme: dark){.gw-title-page .gw-title{color:#e6e8ef;} .gw-title-page .gw-sub{color:#a0a7c1;} .gw-title-page .gw-sub > * + *::before{color:#5a648a;}}"
    )


def _format_title_field(value: str) -> str:
    if not value:
        return ""
    import html as _html
    import re as _re

    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""
    escaped = _html.escape(normalized)
    escaped = escaped.replace("\n", "<br />")
    escaped = _re.sub(r"&lt;br\s*/?&gt;", "<br />", escaped, flags=_re.IGNORECASE)
    return escaped


def _build_title_page_html(*, enabled: bool, title: str, date: str, author: str) -> str:
    if not enabled:
        return ""
    title_value = title or ""
    date_value = date or ""
    author_value = author or ""

    t = _format_title_field(title_value)
    d = _format_title_field(date_value)
    a = _format_title_field(author_value)

    # Render only if at least one field is provided
    if not (t or d or a):
        return ""

    parts: list[str] = ["<section class=\"gw-title-page\">",
                        "<div>"]
    if t:
        parts.append(f"<h1 class=\"gw-title\">{t}</h1>")
    if d or a:
        parts.append("<div class=\"gw-sub\">")
        if d:
            parts.append(f"<div class=\"gw-date\">{d}</div>")
        if a:
            parts.append(f"<div class=\"gw-author\">{a}</div>")
        parts.append("</div>")
    parts.append("</div></section>")

    # No explicit gw-page-break needed in preview since min-height fills a page;
    # print uses CSS break-after.
    return "".join(parts)


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

    w_px = _mm_to_px(w_mm)
    h_px = _mm_to_px(h_mm)
    margin_spec = margin.strip() if margin else settings.pdf_page_margin_default
    margin_top, margin_right, margin_bottom, margin_left = _expand_margin_shorthand(margin_spec)
    return (
        ":root{"
        f"--page-width-px:{w_px}px;"
        f"--page-height-px:{h_px}px;"
        f"--page-margin:{margin_spec};"
        f"--page-margin-top:{margin_top};"
        f"--page-margin-right:{margin_right};"
        f"--page-margin-bottom:{margin_bottom};"
        f"--page-margin-left:{margin_left};"
        "}\n"
    )


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


def _mm_to_px(mm: float) -> int:
    return int(round(mm / 25.4 * 96))


def _expand_margin_shorthand(margin: str) -> tuple[str, str, str, str]:
    parts = [p for p in margin.split() if p]
    if not parts:
        return ("0", "0", "0", "0")
    if len(parts) == 1:
        return (parts[0], parts[0], parts[0], parts[0])
    if len(parts) == 2:
        return (parts[0], parts[1], parts[0], parts[1])
    if len(parts) == 3:
        return (parts[0], parts[1], parts[2], parts[1])
    return (parts[0], parts[1], parts[2], parts[3])


def _css_length_to_px(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    lower = raw.lower()
    try:
        if lower.endswith("mm"):
            return float(_mm_to_px(float(lower[:-2])))
        if lower.endswith("cm"):
            return float(_mm_to_px(float(lower[:-2]) * 10))
        if lower.endswith("in"):
            return float(lower[:-2]) * 96.0
        if lower.endswith("px"):
            return float(lower[:-2])
        if lower.endswith("pt"):
            return float(lower[:-2]) * (96.0 / 72.0)
        if lower.endswith("pc"):
            return float(lower[:-2]) * 12.0 * (96.0 / 72.0)
        if re.fullmatch(r"[0-9]*\.?[0-9]+", lower):
            return float(lower)
    except ValueError:
        return None
    return None


def _replace_reserved_page_breaks(md: str) -> str:
    if not md:
        return md

    reserved_markers = {"[[pagebreak]]", "[[PAGEBREAK]]", ":::pagebreak"}
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        if raw.strip().lower() in reserved_markers:
            if out and out[-1] != "":
                out.append("")
            out.append('<div class="gw-page-break"></div>')
            i += 1
            # ensure a blank line separates the break from following content when needed
            if i < n and lines[i].strip() != "":
                out.append("")
            continue
        out.append(raw)
        i += 1
    return "\n".join(out)


def _normalize_image_widths(html_fragment: str) -> str:
    if not html_fragment or "<img" not in html_fragment.lower():
        return html_fragment
    parser = _ImageWidthNormalizer()
    parser.feed(html_fragment)
    parser.close()
    return parser.get_html()


class _ImageWidthNormalizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._chunks.append(self._serialize_start(tag, attrs, False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._chunks.append(self._serialize_start(tag, attrs, True))

    def handle_endtag(self, tag: str) -> None:
        self._chunks.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        self._chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._chunks.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._chunks.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._chunks.append(f"<!{decl}>")

    def unknown_decl(self, data: str) -> None:  # pragma: no cover - rare
        self._chunks.append(f"<![{data}]>")

    def handle_pi(self, data: str) -> None:  # pragma: no cover - rare
        self._chunks.append(f"<?{data}>")

    def error(self, message: str) -> None:  # pragma: no cover - compatibility hook
        return

    def get_html(self) -> str:
        return "".join(self._chunks)

    def _serialize_start(
        self, tag: str, attrs: list[tuple[str, Optional[str]]], self_closing: bool
    ) -> str:
        normalized_attrs = _normalize_img_attrs(tag, attrs)
        attr_chunks: list[str] = []
        for name, value in normalized_attrs:
            if value is None:
                attr_chunks.append(f" {name}")
            else:
                attr_chunks.append(f" {name}={_quote_attr(value)}")
        closing = " /" if self_closing else ""
        return f"<{tag}{''.join(attr_chunks)}{closing}>"


def _normalize_img_attrs(
    tag: str, attrs: list[tuple[str, Optional[str]]]
) -> list[tuple[str, Optional[str]]]:
    if tag.lower() != "img":
        return attrs

    width_value: Optional[str] = None
    style_value: Optional[str] = None
    for name, value in attrs:
        lower = name.lower()
        if lower == "width" and value is not None:
            width_value = value
        elif lower == "style" and value is not None:
            style_value = value

    css_width = _normalize_width_value(width_value)
    if not css_width:
        return attrs

    style_merged = _merge_style_declarations(style_value, f"width:{css_width};")
    updated: list[tuple[str, Optional[str]]] = []
    style_applied = False
    for name, value in attrs:
        if name.lower() == "style":
            updated.append((name, style_merged))
            style_applied = True
        else:
            updated.append((name, value))
    if not style_applied:
        updated.append(("style", style_merged))
    return updated


def _normalize_width_value(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    value = raw.strip()
    if not value:
        return None
    lower = value.lower()
    if lower in {"auto", "initial", "inherit"}:
        return None
    allowed_units = (
        "px",
        "%",
        "em",
        "rem",
        "vw",
        "vh",
        "vmin",
        "vmax",
        "cm",
        "mm",
        "in",
        "pt",
    )
    for unit in allowed_units:
        if lower.endswith(unit):
            return value
    if re.fullmatch(r"[0-9]*\.?[0-9]+", lower):
        return f"{lower}px"
    return None


def _merge_style_declarations(existing: Optional[str], addition: str) -> str:
    base = (existing or "").strip()
    if base:
        base = re.sub(r"(?i)\bwidth\s*:[^;]+;?", "", base).strip()
        if base and not base.endswith(";"):
            base += ";"
    addition = addition.strip()
    if not addition.endswith(";"):
        addition += ";"
    if base:
        return f"{base} {addition}".strip()
    return addition


def _quote_attr(value: str) -> str:
    return f'"{_escape(value, quote=True)}"'


def _normalize_admonitions(md: str, *, collapse_inside: bool = False) -> str:
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

            # Optionally collapse lines within admon content
            if collapse_inside and content:
                content = _collapse_inside_block(content)

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
            if collapse_inside and body:
                body = _collapse_inside_block(body)
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


def _collapse_inside_block(lines: list[str]) -> list[str]:
    """Collapse soft newlines within a block while preserving blank lines.

    Uses the same rules as collapse_soft_newlines but operates on a list of lines
    that are not yet indented (admonition body before indentation).
    """
    text = "\n".join(lines)
    collapsed = collapse_soft_newlines(text)
    return collapsed.splitlines()
