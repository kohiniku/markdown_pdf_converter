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


_PREVIEW_PAGE_SIZE_ALIASES = {"preview", "preview use", "preview-use"}


def is_preview_flow_size(page_size: Optional[str]) -> bool:
    if not page_size:
        return False
    return page_size.strip().lower() in _PREVIEW_PAGE_SIZE_ALIASES


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
        # Custom CSS is optional, so missing file is acceptable
        # カスタムCSSは任意なので存在しなくても問題ない
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
    out = []
    buf: list[tuple[str, bool]] = []

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
        if not buf:
            return

        paragraph_parts: list[str] = []
        for content, hard_break in buf:
            stripped = content.strip()
            if stripped:
                paragraph_parts.append(stripped)
            if hard_break:
                combined = " ".join(paragraph_parts)
                if combined:
                    out.append(combined + "  ")
                else:
                    out.append("  ")
                paragraph_parts = []

        if paragraph_parts:
            combined = " ".join(paragraph_parts)
            out.append(combined)

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

        trailing_spaces = len(line) - len(line.rstrip(" "))
        hard_break = trailing_spaces >= 2
        buf.append((line, hard_break))

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
    # Title page (cover) options
    # タイトルページ（表紙相当）のオプション
    title_page: Optional[bool] = None,
    title_text: Optional[str] = None,
    title_date: Optional[str] = None,
    title_author: Optional[str] = None,
    preview_flow_override: Optional[bool] = None,
    for_preview: bool = False,
) -> Tuple[str, str]:
    """Render Markdown to full HTML plus CSS.

    Tuned to mimic GROWI v7 styling.
    HTML全文と適用CSSを返すMarkdownレンダリング関数。GROWI v7と近い見た目になるように拡張や整形処理を施している。
    """

    markdown_text = _replace_reserved_page_breaks(markdown_text)

    # Normalize GitHub-style callouts and ::: blocks into !!! admonitions
    # GitHubスタイルのコールアウトや:::記法を!!!記法に正規化する
    # Optionally collapse soft newlines inside admonitions
    # 必要に応じてアドモニション内部のソフト改行もまとめる
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
        # Add permalinks similar to GROWI heading anchors
        # GROWIの見出しアンカーと同等のパーマリンクを付与する
        "toc": {"permalink": True, "permalink_class": "gw-heading-anchor"},
    }

    html_body = md.markdown(markdown_text, extensions=extensions, extension_configs=extension_configs)
    html_body = _convert_deprecated_font_tags(html_body)

    # Prepend a title-page block when requested
    # 必要なら表紙用のHTMLブロックを本文の前に差し込む
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

    preview_alias_requested = is_preview_flow_size(page_size)
    if preview_flow_override is None:
        preview_only_layout = preview_alias_requested
    else:
        preview_only_layout = preview_flow_override
    paginated_preview = for_preview and not preview_only_layout
    resolved_page_size = (
        settings.pdf_page_size_default
        if preview_alias_requested
        else (page_size or settings.pdf_page_size_default)
    )
    resolved_orientation = orientation or settings.pdf_page_orientation_default
    resolved_margin = margin or settings.pdf_page_margin_default

    # Assemble @page rules for size and margins
    # 用紙サイズや余白を指定する@pageルールを組み立てる
    page_css = "" if preview_only_layout else _build_page_css(
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
        "  function paginateList(list){\n"
        "    if(!list || !list.children || !list.children.length){\n"
        "      var clone=list.cloneNode(true);\n"
        "      cur.cont.appendChild(clone);\n"
        "      if(!fits()){\n"
        "        cur.cont.removeChild(clone);\n"
        "        cur=makePage();\n"
        "        cur.cont.appendChild(clone);\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    var items=[];\n"
        "    for(var ci=0;ci<list.children.length;ci++){\n"
        "      var child=list.children[ci];\n"
        "      if(child.tagName && child.tagName.toLowerCase()==='li'){ items.push(child.cloneNode(true)); }\n"
        "    }\n"
        "    if(!items.length){\n"
        "      var passthrough=list.cloneNode(true);\n"
        "      cur.cont.appendChild(passthrough);\n"
        "      if(!fits()){\n"
        "        cur.cont.removeChild(passthrough);\n"
        "        cur=makePage();\n"
        "        cur.cont.appendChild(passthrough);\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    var isOrdered=list.tagName.toLowerCase()==='ol';\n"
        "    var baseStart=1;\n"
        "    if(isOrdered){\n"
        "      var startAttr=list.getAttribute('start');\n"
        "      if(startAttr){ baseStart=parseInt(startAttr,10) || 1; }\n"
        "    }\n"
        "    var index=0;\n"
        "    function newShell(){\n"
        "      var shell=list.cloneNode(false);\n"
        "      copyAttributes(list, shell);\n"
        "      if(isOrdered){\n"
        "        var startVal=baseStart + index;\n"
        "        if(startVal !== 1){ shell.setAttribute('start', startVal); } else { shell.removeAttribute('start'); }\n"
        "      }\n"
        "      cur.cont.appendChild(shell);\n"
        "      return shell;\n"
        "    }\n"
        "    var shell=null;\n"
        "    while(index < items.length){\n"
        "      if(!shell){ shell=newShell(); }\n"
        "      var li=items[index];\n"
        "      shell.appendChild(li.cloneNode(true));\n"
        "      if(!fits()){\n"
        "        shell.removeChild(shell.lastChild);\n"
        "        if(!shell.childElementCount){\n"
        "          cur.cont.removeChild(shell);\n"
        "        }\n"
        "        cur=makePage();\n"
        "        shell=newShell();\n"
        "        shell.appendChild(li.cloneNode(true));\n"
        "        if(!fits()){\n"
        "          // If even a single item does not fit, force it onto a new page.\n"
        "          shell.removeChild(shell.lastChild);\n"
        "          cur.cont.removeChild(shell);\n"
        "          cur=makePage();\n"
        "          shell=newShell();\n"
        "          shell.appendChild(li.cloneNode(true));\n"
        "        }\n"
        "      }else{\n"
        "        index++;\n"
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
        "    if(node.nodeType===1 && node.tagName){\n"
        "      var tag=node.tagName.toLowerCase();\n"
        "      if(tag==='ul' || tag==='ol'){\n"
        "        paginateList(node);\n"
        "        continue;\n"
        "      }\n"
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

    if preview_only_layout:
        preview_script = ""
    elif paginated_preview:
        preview_script = ""
    preview_flow_css = _build_preview_flow_css() if preview_only_layout else ""
    static_preview_css = _build_static_preview_css() if paginated_preview else ""

    if preview_only_layout:
        html_doc = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
            <style>{theme_css}{title_css}{base_css}{page_vars_css}{preview_flow_css}</style>
          </head>
          <body class=\"gw-screen gw-preview-flow\">
            <div class=\"gw-preview-scroll\">
              <div class=\"gw-container\">{html_body}</div>
            </div>
            {preview_script}
          </body>
        </html>
        """
        combined_css = theme_css + title_css + base_css + page_vars_css + preview_flow_css
    elif paginated_preview:
        template_markup = (
            f"<template id=\"gw-preview-template\">"
            f"<div class=\"gw-container\">{html_body}</div>"
            "</template>"
        )
        html_doc = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
            <style>{theme_css}{title_css}{base_css}{page_css}{page_vars_css}{static_preview_css}</style>
          </head>
          <body class=\"gw-screen gw-static-preview\">
            {template_markup}
            <div class=\"gw-page-wrapper\" data-preview-mode=\"static\">
              <div id=\"gw-pages\"></div>
            </div>
            {_build_static_preview_script()}
          </body>
        </html>
        """
        combined_css = theme_css + title_css + base_css + page_css + page_vars_css + static_preview_css
    else:
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


def _build_preview_flow_css() -> str:
    return (
        "@media screen{"  # Continuous scroll preview styling
        "body.gw-preview-flow{background:var(--gw-bg);}" \
        ".gw-preview-scroll{max-width:min(100%, calc(var(--page-width-px, 900px) + 48px));margin:0 auto;padding:24px 0 72px;}" \
        ".gw-preview-scroll .gw-container{" \
        "background-color:#fff;border-radius:16px;border:1px solid rgba(15,23,42,0.08);" \
        "box-shadow:0 20px 45px rgba(15,23,42,0.12);max-width:100%;" \
        "padding:var(--page-margin-top,12mm) var(--page-margin-right,12mm) var(--page-margin-bottom,12mm) var(--page-margin-left,12mm);" \
        "background-image:repeating-linear-gradient(" \
        "to bottom," \
        "transparent 0 calc(var(--page-height-px, 1123px) - 1px)," \
        "rgba(15,23,42,0.18) calc(var(--page-height-px, 1123px) - 1px) calc(var(--page-height-px, 1123px) + 1px)" \
        ");" \
        "background-size:100% calc(var(--page-height-px, 1123px));" \
        "background-repeat:repeat-y;" \
        "background-origin:content-box;" \
        "background-clip:content-box;" \
        "}" \
        ".gw-preview-flow .gw-container > *:first-child{margin-top:0;}" \
        ".gw-preview-flow .gw-container > *:last-child{margin-bottom:0;}" \
        ".gw-preview-flow .gw-page-break{display:block;border-top:1px dashed rgba(148,163,184,0.6);margin:56px auto;height:0;}" \
        "}" \
        "@media (prefers-color-scheme: dark){" \
        "body.gw-preview-flow{background:#0b1220;}" \
        ".gw-preview-scroll .gw-container{" \
        "background-color:#111827;border-color:rgba(148,163,184,0.35);" \
        "box-shadow:0 24px 60px rgba(0,0,0,0.45);" \
        "background-image:repeating-linear-gradient(" \
        "to bottom," \
        "transparent 0 calc(var(--page-height-px, 1123px) - 1px)," \
        "rgba(148,163,184,0.35) calc(var(--page-height-px, 1123px) - 1px) calc(var(--page-height-px, 1123px) + 1px)" \
        ");" \
        "}" \
        ".gw-preview-flow .gw-page-break{border-top-color:rgba(148,163,184,0.45);}" \
        "}\n"
    )


def _build_static_preview_css() -> str:
    return (
        ".gw-static-preview template{display:none;}"
        ".gw-preview-probe{position:absolute;visibility:hidden;pointer-events:none;left:-9999px;top:0;"
        "width:var(--page-width-px,794px);z-index:-1;}"
        ".gw-page-wrapper[data-preview-mode=\"static\"]{display:flex;justify-content:center;padding:16px;overflow:auto;}"
        ".gw-page-wrapper[data-preview-mode=\"static\"] #gw-pages{display:flex;flex-direction:column;align-items:center;"
        "gap:18px;width:100%;}"
        ".gw-page-wrapper[data-preview-mode=\"static\"] .gw-page-outer{position:relative;"
        "width:calc(var(--page-width-px,794px)*var(--scale,1));"
        "height:calc(var(--page-height-px,1123px)*var(--scale,1));}"
        ".gw-page-wrapper[data-preview-mode=\"static\"] .gw-page-outer>.gw-page{position:absolute;top:0;left:0;"
        "width:100%;height:100%;transform-origin:top left;transform:scale(var(--scale,1));overflow:hidden;"
        "background:#fff;}"
        ".gw-page-slice{position:absolute;top:0;left:0;width:100%;}"
        ".gw-page-slice .gw-container{max-width:none;padding:var(--page-margin-top,12mm) "
        "var(--page-margin-right,12mm) var(--page-margin-bottom,12mm) var(--page-margin-left,12mm);}"
        ".gw-static-preview .gw-page-break{display:block;margin:0;height:0;}"
    )


def _build_static_preview_script() -> str:
    return (
        "<script>(function(){\n"
        "var rebuildTimer=null;\n"
        "function clear(el){while(el.firstChild){el.removeChild(el.firstChild);}}\n"
        "function buildPages(){\n"
        "  var tmpl=document.getElementById('gw-preview-template');\n"
        "  var host=document.getElementById('gw-pages');\n"
        "  if(!tmpl||!host) return;\n"
        "  var markup=tmpl.innerHTML;\n"
        "  var probe=document.createElement('div');probe.className='gw-preview-probe';\n"
        "  var probeArticle=document.createElement('article');probeArticle.className='gw-page';\n"
        "  var probeContainer=document.createElement('div');probeContainer.className='gw-container';\n"
        "  probeContainer.innerHTML=markup;probeArticle.appendChild(probeContainer);probe.appendChild(probeArticle);\n"
        "  document.body.appendChild(probe);\n"
        "  var root=document.documentElement;var styles=getComputedStyle(root);\n"
        "  var pageHeight=parseFloat(styles.getPropertyValue('--page-height-px'))||1123;\n"
        "  var innerHeight=pageHeight;\n"
        "  var baseTop=probeContainer.getBoundingClientRect().top;\n"
        "  var breaks=probeContainer.querySelectorAll('.gw-page-break');\n"
        "  if(breaks&&breaks.length){\n"
        "    for(var b=0;b<breaks.length;b++){\n"
        "      var node=breaks[b];\n"
        "      var rect=node.getBoundingClientRect();\n"
        "      var offset=rect.top-baseTop;\n"
        "      var remainder=offset%innerHeight;\n"
        "      if(remainder<0){remainder+=innerHeight;}\n"
        "      var gap=remainder===0?0:(innerHeight-remainder);\n"
        "      node.style.display='block';\n"
        "      node.style.height=gap+'px';\n"
        "    }\n"
        "  }\n"
        "  var normalized=probeContainer.outerHTML;\n"
        "  var totalHeight=probeContainer.scrollHeight;\n"
        "  document.body.removeChild(probe);\n"
        "  clear(host);\n"
        "  var pages=Math.max(1, Math.ceil(totalHeight/innerHeight));\n"
        "  for(var i=0;i<pages;i++){\n"
        "    var outer=document.createElement('div');outer.className='gw-page-outer';\n"
        "    var page=document.createElement('article');page.className='gw-page';\n"
        "    var slice=document.createElement('div');slice.className='gw-page-slice';\n"
        "    slice.innerHTML=normalized;\n"
        "    slice.style.transform='translateY(-'+(i*innerHeight)+'px)';\n"
        "    page.appendChild(slice);outer.appendChild(page);host.appendChild(outer);\n"
        "  }\n"
        "  scalePages();\n"
        "}\n"
        "function scalePages(){\n"
        "  var wrapper=document.querySelector('.gw-page-wrapper[data-preview-mode=\"static\"]');\n"
        "  if(!wrapper) return;\n"
        "  var root=document.documentElement;var cs=getComputedStyle(root);\n"
        "  var pageWidth=parseFloat(cs.getPropertyValue('--page-width-px'))||794;\n"
        "  var avail=wrapper.clientWidth-32;var scale=1;\n"
        "  if(pageWidth>0){scale=Math.min(1, Math.max(0.35, avail/pageWidth));}\n"
        "  var pages=wrapper.querySelectorAll('.gw-page-outer');\n"
        "  for(var i=0;i<pages.length;i++){\n"
        "    pages[i].style.setProperty('--scale', String(scale));\n"
        "  }\n"
        "}\n"
        "function schedule(){\n"
        "  clearTimeout(rebuildTimer);\n"
        "  rebuildTimer=setTimeout(buildPages,150);\n"
        "}\n"
        "if(document.readyState==='loading'){\n"
        "  document.addEventListener('DOMContentLoaded', buildPages);\n"
        "}else{\n"
        "  buildPages();\n"
        "}\n"
        "window.addEventListener('resize', schedule);\n"
        "})();</script>"
    )

def _build_title_css(size: str, orientation: str, margin: str) -> str:
    """Build CSS for the generated title page block.

    - Keep vertical centering for both preview and print.
    - プレビューと印刷の両方で縦方向の中央揃えを維持する。
    - Force a page break right after the title block when printing.
    - 印刷時にはタイトルブロック直後で改ページさせる。
    - Align preview sizing via CSS custom properties.
    - CSSカスタムプロパティを使ってプレビュー時の見た目を揃える。
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

    # Render only when at least one field is provided
    # いずれかの項目が設定されているときだけ表紙を描画する
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

    # Preview already reserves page height, so no gw-page-break is needed
    # プレビューでは高さを確保しているためgw-page-breakは不要
    # Printing splits pages via CSS break-after
    # 印刷時はCSSのbreak-afterでページ分割する
    return "".join(parts)


def _build_page_css(size: str, orientation: str, margin: str) -> str:
    size = (size or "A4").strip()
    orient = (orientation or "portrait").strip().lower()
    if orient not in ("portrait", "landscape"):
        orient = "portrait"
    # Support combined forms like "A4 landscape"
    # "A4 landscape"のような複合指定にも対応する
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
    # Map common paper sizes (width × height mm, portrait)
    # 一般的な用紙サイズ（幅×高さ[mm]、縦向き）を対応付ける
    sizes = {
        "a3": (297.0, 420.0),
        "a4": (210.0, 297.0),
        "a5": (148.0, 210.0),
        "letter": (215.9, 279.4),  # 8.5 x 11 in
        "legal": (215.9, 355.6),   # 8.5 x 14 in
    }
    # Strip trailing orientation keywords such as "landscape"
    # "A4 landscape"などの表記では末尾の単語を除去して検索する
    base = s.replace("landscape", "").replace("portrait", "").strip()
    return sizes.get(base, sizes["a4"])  # Default to A4 when not found


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
            # Insert a blank line after the page-break marker when needed
            # 必要に応じて改ページマーカーと後続コンテンツの間に空行を挿入する
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

    # pragma: no cover - rare case
    # 稀なケース
    def unknown_decl(self, data: str) -> None:
        self._chunks.append(f"<![{data}]>")

    # pragma: no cover - rare case
    # 稀なケース
    def handle_pi(self, data: str) -> None:
        self._chunks.append(f"<?{data}>")

    # pragma: no cover - compatibility hook
    # 互換性維持用のフック
    def error(self, message: str) -> None:
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
    """Normalize major admonition syntaxes to Python-Markdown's !!! form.

    Supports GitHub callouts ("> [!NOTE]") and triple-colon blocks.
    主要なアドモニション記法をPython-Markdownの!!!形式にそろえ、GitHub系コールアウトとトリプルコロン記法に対応する。
    """
    if not md:
        return md

    lines = md.splitlines()
    out: list[str] = []

    import re

    # Process GitHub-style callouts inside blockquotes
    # 引用ブロック内のGitHubスタイルコールアウトを処理する
    callout_re = re.compile(r"^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|DANGER|INFO)\]\s*(.*)$", re.I)

    i = 0
    n = len(lines)
    while i < n:
        m = callout_re.match(lines[i])
        if m:
            kind = m.group(1).lower()
            # Gather subsequent quoted lines belonging to the callout
            # 同じコールアウトに含まれる後続の引用行を集める
            content: list[str] = []
            # The first line may carry trailing text beyond the tag
            # 先頭行にはタグの後に文章が続く場合があるが基本は空
            trailing = m.group(2).strip()
            if trailing:
                content.append(trailing)

            i += 1
            while i < n:
                ln = lines[i]
                if not ln.lstrip().startswith('>'):
                    break
                # Strip the leading '>' and optional space
                # 先頭の">"と任意のスペース1つを取り除く
                stripped = ln.lstrip()[1:]
                if stripped.startswith(' '):
                    stripped = stripped[1:]
                content.append(stripped)
                i += 1

            # Collapse admonition body lines when requested
            # 必要に応じてアドモニション本文の改行をまとめる
            if collapse_inside and content:
                content = _collapse_inside_block(content)

            # Convert to !!! syntax and indent body content
            # !!! 記法に変換し本文にはインデントを付与する
            out.append(f"!!! {kind}")
            for c in content:
                out.append(f"    {c}")
            # Do not advance index here; it was already moved above
            # ここでインデックスは進めず、それまでに更新した位置を使う
            continue

        # Handle :::note ... ::: style admonitions
        # :::note ... ::: 形式のアドモニションを処理する
        if lines[i].lstrip().startswith(':::'):
            # Parse the opening definition line to extract type and title
            # 先頭の定義行を解析して種別とタイトルを取り出す
            opener = lines[i].lstrip()[3:].strip()
            # Support variants such as 'note' or 'note Title'
            # 'note' や 'note タイトル' といったバリエーションに対応する
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
            # Skip the closing ':::' marker if present
            # 終端の':::'があれば読み飛ばす
            if i < n and lines[i].lstrip().startswith(':::'):
                i += 1

            title_part = f' "{title}"' if title else ''
            if collapse_inside and body:
                body = _collapse_inside_block(body)
            out.append(f"!!! {typ}{title_part}")
            for b in body:
                out.append(f"    {b}")
            continue

        # Otherwise pass the line through unchanged
        # どちらにも該当しない場合はそのまま出力する
        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _strip_admonition_title_leading_emoji(title: str | None) -> str | None:
    if not title:
        return title
    t = title.strip()
    # Known emoji prefixes used in our CSS or common aliases
    # CSS側で利用している、または一般的な絵文字プレフィクスの一覧
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

    Mirrors collapse_soft_newlines for pre-indented admonition content.
    空行を保ちながらブロック内の柔らかい改行を詰める（collapse_soft_newlinesと同じ判定をインデント前のアドモニション本文に適用）。
    """
    text = "\n".join(lines)
    collapsed = collapse_soft_newlines(text)
    return collapsed.splitlines()
