import html
import os
import re
import sys
from typing import Any, List, Match, Optional

_vendor = os.path.join(os.path.dirname(__file__), 'vendor')
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import mistune
from mistune.plugins.table import (
    TABLE_PATTERN,
    NP_TABLE_PATTERN,
    _strip_pipe_table_row,
    _strip_table_line,
    _process_thead,
    _process_row,
    _parse_invalid_pipe_table,
)


class CustomRenderer(mistune.HTMLRenderer):
    def custom_table(self, text: str) -> str:
        if self._escape:
            text = html.escape(text.strip())
        return f'<div class="custom-table">\n{text}\n</div>\n'

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


def _parse_raw_table(block: mistune.BlockParser, m: Match[str], state: mistune.BlockState) -> Optional[int]:
    pos = m.end()
    header = _strip_pipe_table_row(m.group(0))
    if header is None:
        return None

    align_line = state.get_line(pos)
    align = _strip_pipe_table_row(align_line)
    if align is None:
        return None

    thead, aligns = _process_thead(header, align)
    if not thead:
        return _parse_invalid_pipe_table(state, pos + len(align_line))
    assert aligns is not None

    pos += len(align_line)

    while pos < state.cursor_max:
        line = state.get_line(pos)
        text = _strip_pipe_table_row(line)
        if text is None:
            break
        row = _process_row(text, aligns)
        if not row:
            return _parse_invalid_pipe_table(state, pos + len(line))
        pos += len(line)

    raw_text = state.src[state.cursor:pos]
    state.append_token({"type": "custom_table", "raw": raw_text})
    return pos


def _parse_raw_nptable(block: mistune.BlockParser, m: Match[str], state: mistune.BlockState) -> Optional[int]:
    pos = m.end()
    header = _strip_table_line(m.group(0))
    if header is None:
        return None

    align_line = state.get_line(pos)
    align = _strip_table_line(align_line)
    if align is None:
        return None

    thead, aligns = _process_thead(header, align)
    if not thead:
        return None
    assert aligns is not None

    pos += len(align_line)

    while pos < state.cursor_max:
        line = state.get_line(pos)
        text = _strip_table_line(line)
        if text is None:
            break
        row = _process_row(text, aligns)
        if not row:
            return None
        pos += len(line)

    raw_text = state.src[state.cursor:pos]
    state.append_token({"type": "custom_table", "raw": raw_text})
    return pos


def raw_table_plugin(md: mistune.Markdown) -> None:
    md.block.register('custom_table', TABLE_PATTERN, _parse_raw_table, before='paragraph')
    md.block.register('custom_nptable', NP_TABLE_PATTERN, _parse_raw_nptable, before='paragraph')
