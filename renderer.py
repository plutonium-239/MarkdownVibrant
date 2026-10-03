import os
import re
import sys
from typing import Any, List, Optional

_vendor = os.path.join(os.path.dirname(__file__), 'vendor')
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import mistune


class CustomRenderer(mistune.HTMLRenderer):
    def list(self, text: str, ordered: bool, **attrs: Any) -> str:
        if not ordered:
            return "<ul>\n" + text + "</ul>\n"
        start = attrs.get("start")
        idx = int(start) if start is not None else 1
        items = _split_top_level_items(text)
        out = [f'<div class="ol-item">{idx + i}. {item}</div>' for i, item in enumerate(items)]
        return '<div class="ol">\n' + "\n".join(out) + '\n</div>\n'

    def table(self, text: str) -> str:
        rows = [r.split("\x01") for r in text.split("\x00") if r]
        if not rows:
            return ""
        for r in rows:
            if r and r[-1] == "":
                r.pop()
        ncols = max(len(r) for r in rows) if rows else 0
        for r in rows:
            while len(r) < ncols:
                r.append("")
        _strip = lambda s: re.sub(r"<[^>]+>", "", s)
        widths = [max(len(_strip(r[i])) for r in rows) for i in range(ncols)]
        def _pad(cell, w):
            stripped = _strip(cell)
            return cell + " " * (w - len(stripped))
        def fmt_row(r):
            return "│ " + " │ ".join(_pad(r[i], widths[i]) for i in range(ncols)) + " │"
        top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
        mid = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
        bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"
        out = [top]
        for idx_r, r in enumerate(rows):
            out.append(fmt_row(r))
            if idx_r == 0:
                out.append(mid)
        out.append(bot)
        return '<div class="ascii-table">\n' + "\n".join(out) + '\n</div>\n'

    def table_head(self, text: str) -> str:
        return text + "\x00"

    def table_body(self, text: str) -> str:
        return text

    def table_row(self, text: str) -> str:
        return text + "\x00"

    def table_cell(self, text: str, align: Optional[str] = None, head: bool = False) -> str:
        return text + "\x01"


def _split_top_level_items(text: str) -> list:
    """Split rendered list HTML into top-level <li> items, preserving nested sub-lists."""
    items = []
    depth = 0
    current = []
    i = 0
    while i < len(text):
        if text[i:].startswith("<li>"):
            if depth == 0:
                current = []
            else:
                current.append(text[i:i+4])
            depth += 1
            i += 4
        elif text[i:].startswith("</li>"):
            depth -= 1
            if depth == 0:
                items.append("".join(current))
            else:
                current.append(text[i:i+5])
            i += 5
        else:
            if depth > 0:
                current.append(text[i])
            i += 1
    return items
