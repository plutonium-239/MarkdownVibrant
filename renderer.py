import re

from wenmode import HTMLRenderer
from wenmode.nodes import List, ListItem, Paragraph, Table
from wenmode.presets import github
from wenmode.renderers import RenderContext

# Shared rule set: GFM (tables, task lists, strikethrough, autolinks,
# footnotes) with raw HTML passthrough handled by the renderer.
PRESET = github()


class CustomRenderer(HTMLRenderer):
    """Wenmode equivalent of renderer.CustomRenderer (mistune.HTMLRenderer).

    Handlers are registered on the instance so the shared HTMLRenderer class
    dispatch table stays untouched.
    """

    def __init__(self) -> None:
        super().__init__(escape=False, sanitize_urls=False, sanitize_attrs=False)
        self.register_handler('list', render_list)
        self.register_handler('table', render_table)


def render_list(renderer: HTMLRenderer, node: List, context: RenderContext) -> str:
    items = [_render_list_item(renderer, item, node.spread, context) for item in node.children]
    if not node.ordered:
        text = ''.join(f'<li>{inner}</li>\n' for inner in items)
        return "<ul>\n" + text + "</ul>\n"
    start = node.start if node.start is not None else 1
    out = [f'<div class="ol-item">{start + i}. {inner}</div>' for i, inner in enumerate(items)]
    return '<div class="ol">\n' + "\n".join(out) + '\n</div>\n'


def _render_list_item(
    renderer: HTMLRenderer,
    item: ListItem,
    spread: bool,
    context: RenderContext,
) -> str:
    """Render the inner content of one <li>, like mistune's list_item()."""
    parts: list[str] = []
    if item.checked is not None:
        parts.append('[x] ' if item.checked else '[ ] ')
    if not spread and item.children and isinstance(item.children[0], Paragraph):
        rendered: list[str] = []
        for index, child in enumerate(item.children):
            if isinstance(child, Paragraph):
                rendered.append(renderer.render_children(child.children, context))
                if index < len(item.children) - 1:
                    rendered.append('\n')
            else:
                rendered.append(renderer.render_node(child, context))
        parts.append(''.join(rendered))
    else:
        parts.append(''.join(renderer.render_node(child, context) for child in item.children))
    return ''.join(parts)


def render_table(renderer: HTMLRenderer, node: Table, context: RenderContext) -> str:
    rows = [
        [renderer.render_children(cell.children, context) for cell in row.children]
        for row in node.children
    ]
    return _render_ascii_table(rows)


def _render_ascii_table(rows: list) -> str:
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
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
