import html
import sys
from typing import Match, Optional

sys.path.append('./vendor')
from vendor import mistune
from vendor.mistune.plugins.table import (
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
