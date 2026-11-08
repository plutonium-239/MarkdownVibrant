import re

import sublime
import sublime_plugin
from wenmode import Parser
from wenmode.rules import BlockRule

from .renderer import PRESET


def _block_scan_rules():
    """PRESET reduced to its block rules: enough to find top-level tables
    (code blocks, quotes and lists still consume their lines) without
    paying for inline parsing."""
    rules = []
    for rule in PRESET:
        if isinstance(rule, type):
            if issubclass(rule, BlockRule):
                rules.append(rule)
        elif isinstance(rule, BlockRule):
            rules.append(rule)
    return rules


_BLOCK_SCAN_RULES = _block_scan_rules()
_PARSER = Parser(_BLOCK_SCAN_RULES, positions=True)


_CENTER = re.compile(r":-+:")
_LEFT = re.compile(r":-+")
_RIGHT = re.compile(r"-+:")
_NONE = re.compile(r"-+")


def _split_row(line):
    """Split a table row into cell texts, tolerating missing outer pipes."""
    text = line.strip()
    text = text.removeprefix("|")
    text = text.removesuffix("|")
    cells = []
    start = 0
    for pos, char in enumerate(text):
        if char != "|" or _is_escaped(text, pos):
            continue
        cells.append(text[start:pos].strip())
        start = pos + 1
    cells.append(text[start:].strip())
    return cells


def _is_escaped(text, pos):
    backslashes = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        backslashes += 1
        pos -= 1
    return backslashes % 2 == 1


def _alignment(cell):
    text = cell.strip()
    if _CENTER.fullmatch(text) or not text:
        return "center" if text else None
    if _LEFT.fullmatch(text):
        return "left"
    if _RIGHT.fullmatch(text):
        return "right"
    if _NONE.fullmatch(text):
        return None
    return "invalid"


def find_tables(text):
    """Return all top-level markdown tables in *text*.

    Each table is a dict with the source span (``start``, ``end``) into
    *text*, the per-column alignment (``aligns``, from the separator row)
    and the cell contents of header and body rows (``rows``).
    Tables inside fenced code blocks, block quotes or lists are ignored.

    Wenmode only parses GFM pipe tables; mistune's non-piped "nptable"
    syntax is not detected.
    """
    if "\r" in text:
        return []

    src = text if text.endswith("\n") else text + "\n"
    root = _PARSER.parse(src)

    tables = []
    for node in root.children:
        if node.type != "table" or node.position is None:
            continue
        start = node.position.start
        end = min(node.position.end, len(text))
        lines = [line for line in text[start:end].split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        cell_rows = [_split_row(line) for line in lines]
        aligns = [_alignment(cell) for cell in cell_rows[1]]
        if "invalid" in aligns:
            continue
        ncols = len(cell_rows[0])
        if any(len(cells) != ncols for cells in cell_rows):
            continue
        tables.append({
            "start": start,
            "end": end,
            "aligns": aligns,
            "rows": cell_rows[:1] + cell_rows[2:],
        })
    return tables


def format_table(table, margin=1, padding=0, default_justify="left"):
    """Rebuild a table found by :func:`find_tables` as aligned text.

    Every row is normalized to outer pipes; cells keep their content
    verbatim. Column justification comes from the separator row, falling
    back to *default_justify* for columns without colons.
    """
    aligns = table["aligns"]
    rows = table["rows"]
    ncols = len(aligns)
    widths = [max(len(row[i]) for row in rows) for i in range(ncols)]
    col_widths = [max(w + margin * 2 + padding, 3) for w in widths]
    justs = [a if a is not None else default_justify for a in aligns]

    lines = [_render_row(rows[0], col_widths, justs, margin, padding),
             _render_separator(aligns, col_widths)]
    for row in rows[1:]:
        lines.append(_render_row(row, col_widths, justs, margin, padding))
    return "\n".join(lines)


def _render_row(row, col_widths, justs, margin, padding):
    parts = ["|"]
    for i, cell in enumerate(row):
        if justs[i] == "center":
            div, mod = divmod(col_widths[i] - len(cell), 2)
            parts.append(" " * div + cell + " " * (div + mod) + "|")
        else:
            inner = col_widths[i] - margin * 2
            if justs[i] == "right":
                text = cell.rjust(inner)
            else:
                text = cell.ljust(inner)
            parts.append(" " * margin + text + " " * margin + "|")
    return "".join(parts)


def _render_separator(aligns, col_widths):
    cells = []
    for i, align in enumerate(aligns):
        dashes = "-" * col_widths[i]
        if align == "center":
            cells.append(":" + dashes[1:-1] + ":")
        elif align == "left":
            cells.append(":" + dashes[1:])
        elif align == "right":
            cells.append(dashes[:-1] + ":")
        else:
            cells.append(dashes)
    return "|" + "|".join(cells) + "|"


class MarkdownVibrantFormatTableCommand(sublime_plugin.TextCommand):
    """Formats markdown tables: the whole file, or only the tables that
    intersect the current selection."""

    def run(self, edit, format_all=False):
        settings = sublime.load_settings("MarkdownVibrant.sublime-settings")
        margin = settings.get("table_margin", 1)
        padding = settings.get("table_padding", 0)
        default_justify = str(settings.get("table_default_justification", "LEFT")).lower()

        text = self.view.substr(sublime.Region(0, self.view.size()))
        tables = find_tables(text)
        if not tables:
            if not format_all:
                sublime.status_message("No Markdown Tables Found")
            return

        if not format_all:
            selections = [r for r in self.view.sel() if r.size() > 0]
            if selections:
                tables = [t for t in tables
                          if any(t["start"] < r.end() and r.begin() < t["end"]
                                 for r in selections)]

        offset = 0
        formatted_regions = []
        for table in tables:
            region = sublime.Region(table["start"] + offset, table["end"] + offset)
            new_text = format_table(table, margin, padding, default_justify)
            if table["end"] > 0 and text[table["end"] - 1] == "\n":
                new_text += "\n"
            self.view.replace(edit, region, new_text)
            offset += len(new_text) - region.size()
            formatted_regions.append(sublime.Region(region.begin(), region.begin() + len(new_text)))

        if formatted_regions and not format_all:
            self.view.sel().clear()
            self.view.sel().add_all(formatted_regions)
            self.view.show(formatted_regions[0])
        if not format_all:
            sublime.status_message("Formatted {} Markdown Table{}".format(
                len(formatted_regions), "s" if len(formatted_regions) != 1 else ""))
