"""LaTeX数式を静的SVGに変換するMarkdown拡張。PDFとプレビューで共用する。"""

from __future__ import annotations

import base64
import logging
import re
from uuid import uuid4
from functools import lru_cache
import xml.etree.ElementTree as ET

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.util import AtomicString

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _render_formula(tex: str, inline: bool) -> tuple[str, float, float]:
    # 遅延importにより数式を含まない文書の処理に追加コストをかけない。
    import ziamath

    equation = ziamath.Latex(tex, size=16, inline=inline)
    svg = equation.svgxml()
    width = float(svg.get("width", "16")) / 16
    baseline = (equation.getyofst() - equation.margin) / 16
    encoded = base64.b64encode(ET.tostring(svg, encoding="utf-8")).decode("ascii")
    return encoded, width, baseline


class _MathSvgProcessor(Treeprocessor):
    def run(self, root):
        for element in root.iter():
            if element.get("class") != "arithmatex":
                continue
            inline = element.tag == "span"
            wrapped = element.text or ""
            tex = wrapped[2:-2]  # arithmatexの正規化済みの \(...\) または \[...\]
            element.text = None
            try:
                encoded, width, baseline = _render_formula(tex, inline)
            except Exception:
                # 変換できない式は消さず、原文を残す。
                logger.warning("LaTeX数式のSVG変換に失敗しました", exc_info=True)
                element.set("class", "math-error")
                element.text = AtomicString(wrapped)
                continue
            element.set("class", "math-inline" if inline else "math-display")
            if not inline:
                element.set(
                    "style", "text-align:center;margin:1em 0;break-inside:avoid;"
                )
            ET.SubElement(
                element,
                "img",
                {
                    "class": "math-svg",
                    "src": f"data:image/svg+xml;base64,{encoded}",
                    "alt": tex,
                    "style": f"display:inline-block;margin:0;padding:0;border:0;width:{width:.4f}em;max-width:100%;height:auto;vertical-align:{baseline:.4f}em;",
                },
            )
        return root


class MathSvgExtension(Extension):
    def extendMarkdown(self, md):
        # inline処理(20)の直後。code/fenceは既存拡張で保護される。
        md.treeprocessors.register(_MathSvgProcessor(md), "math-svg", 15)


def protect_math_blocks(text: str) -> tuple[str, dict[str, str]]:
    """数式内の改行・コメントを段落整形から守り、本文との境界に空行を置く。"""
    text, saved = _protect_spans(text)
    lines = text.splitlines()
    result: list[str] = []
    fence_char = ""
    fence_length = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        fence = re.match(r"^[ ]{0,3}(`{3,}|~{3,})", line)
        if fence:
            delim = fence.group(1)
            if not fence_char:
                fence_char, fence_length = delim[0], len(delim)
            elif (
                delim[0] == fence_char
                and len(delim) >= fence_length
                and not line[fence.end() :].strip()
            ):
                fence_char = ""
            result.append(line)
            i += 1
            continue
        if fence_char:
            result.append(line)
            i += 1
            continue
        start = re.match(r"^[ ]{0,3}(\\\[|\$\$|\\begin\{([a-zA-Z]+\*?)\})", line)
        if start:
            opener = start.group(1)
            closer = {"\\[": "\\]", "$$": "$$"}.get(
                opener, "\\end{" + (start.group(2) or "") + "}"
            )
            end = i
            # 閉じ区切りのない入力はそのまま残す。
            while end < len(lines):
                candidate = lines[end][start.end() :] if end == i else lines[end]
                if candidate.rstrip().endswith(closer):
                    token = "ODRMATHBLOCK" + uuid4().hex + "END"
                    saved[token] = "\n".join(lines[i : end + 1])
                    result.extend(["", token, ""])
                    i = end + 1
                    break
                end += 1
            else:
                result.append(line)
                i += 1
            continue
        result.append(line)
        i += 1
    return "\n".join(result), saved


def _protect_spans(text: str) -> tuple[str, dict[str, str]]:
    """複数行コードスパン・行内数式を、フェンス内を変更せず退避する。"""
    saved: dict[str, str] = {}
    pattern = re.compile(
        r"(?<![\\`])(?P<ticks>`+)(?!`)(?P<code>.*?)(?<!`)(?P=ticks)(?!`)"
        r"|(?P<round>(?<!\\)\\\(.*?\\\))",
        re.DOTALL,
    )

    def replace(match):
        source = match.group(0)
        if "\n" not in source:
            return source
        token = "ODRSPAN" + uuid4().hex + "END"
        saved[token] = source
        return token

    result: list[str] = []
    plain: list[str] = []
    fence_char = ""
    fence_length = 0

    def flush():
        if plain:
            result.append(pattern.sub(replace, "\n".join(plain)))
            plain.clear()

    for line in text.splitlines():
        fence = re.match(r"^[ ]{0,3}(`{3,}|~{3,})", line)
        if fence_char:
            result.append(line)
            if fence:
                delim = fence.group(1)
                if (
                    delim[0] == fence_char
                    and len(delim) >= fence_length
                    and not line[fence.end() :].strip()
                ):
                    fence_char = ""
        elif fence:
            flush()
            delim = fence.group(1)
            fence_char, fence_length = delim[0], len(delim)
            result.append(line)
        else:
            plain.append(line)
    flush()
    return "\n".join(result), saved


def restore_math_blocks(text: str, saved: dict[str, str]) -> str:
    # ブロックを先に戻し、その中に退避済みスパンがあれば後から戻す。
    for token, source in reversed(list(saved.items())):

        def replace(match):
            indent = match.group(1)
            return "\n".join(indent + line for line in source.splitlines())

        text = re.sub(
            r"^([ \t]*)" + re.escape(token) + r"(?=\s*$)",
            replace,
            text,
            flags=re.MULTILINE,
        )
        text = text.replace(token, source)
    return text
