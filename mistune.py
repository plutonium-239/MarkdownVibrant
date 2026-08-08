"""
Mistune - Fast, lightweight Markdown parser for Python.
Bundled pure-Python parser for Sublime Text MarkdownVibrant plugin.
"""

import re
import html

__version__ = "3.0.2"


class MistuneParser:
    def __init__(self):
        pass

    def parse(self, text):
        if not text:
            return ""

        lines = text.splitlines()
        html_out = []
        in_code_block = False
        code_lang = ""
        code_lines = []
        in_list = False
        list_type = None
        in_blockquote = False
        blockquote_lines = []
        in_table = False
        table_rows = []

        for line in lines:
            # Code Fence Handling
            if line.strip().startswith("```"):
                if in_code_block:
                    code_content = html.escape("\n".join(code_lines))
                    lang_class = f' class="language-{code_lang}"' if code_lang else ''
                    html_out.append(f'<pre><code{lang_class}>{code_content}</code></pre>')
                    in_code_block = False
                    code_lines = []
                    code_lang = ""
                else:
                    self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                    in_list, in_blockquote, in_table = False, False, False
                    blockquote_lines, table_rows = [], []
                    in_code_block = True
                    code_lang = line.strip().lstrip("```").strip()
                continue

            if in_code_block:
                code_lines.append(line)
                continue

            # Table Handling
            if "|" in line and not line.strip().startswith(">"):
                stripped = line.strip()
                if stripped.startswith("|") and stripped.endswith("|"):
                    if not in_table:
                        self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, False, [])
                        in_list, in_blockquote = False, False
                        blockquote_lines = []
                        in_table = True
                    table_rows.append(stripped)
                    continue
            elif in_table:
                html_out.append(self._render_table(table_rows))
                in_table = False
                table_rows = []

            # Blockquote Handling
            if line.strip().startswith(">"):
                if not in_blockquote:
                    self._close_open_blocks(html_out, in_list, False, [], in_table, table_rows)
                    in_list, in_table = False, False
                    table_rows = []
                    in_blockquote = True
                blockquote_lines.append(line.strip().lstrip("> ").strip())
                continue
            elif in_blockquote:
                html_out.append(self._render_blockquote(blockquote_lines))
                in_blockquote = False
                blockquote_lines = []

            # Horizontal Rule
            if re.match(r'^\s*([-*_])\s*\1\s*\1\s*$', line):
                self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                in_list, in_blockquote, in_table = False, False, False
                blockquote_lines, table_rows = [], []
                html_out.append("<hr>")
                continue

            # Headings
            heading_match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if heading_match:
                self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                in_list, in_blockquote, in_table = False, False, False
                blockquote_lines, table_rows = [], []
                level = len(heading_match.group(1))
                content = self._inline_parse(heading_match.group(2))
                html_out.append(f'<h{level}>{content}</h{level}>')
                continue

            # Lists & Checkboxes
            unordered_match = re.match(r'^\s*([*+-])\s+(.*)$', line)
            ordered_match = re.match(r'^\s*(\d+)\.\s+(.*)$', line)

            if unordered_match or ordered_match:
                item_content = unordered_match.group(2) if unordered_match else ordered_match.group(2)
                curr_type = 'ul' if unordered_match else 'ol'

                task_match = re.match(r'^\[([ xX])\]\s+(.*)$', item_content)
                if task_match:
                    checked = 'checked' if task_match.group(1).lower() == 'x' else ''
                    task_text = self._inline_parse(task_match.group(2))
                    icon = '☑' if checked else '☐'
                    color = '#50fa7b' if checked else '#ff5555'
                    item_html = f'<span style="color: {color}; font-weight: bold;">{icon}</span> {task_text}'
                else:
                    item_html = self._inline_parse(item_content)

                if not in_list or list_type != curr_type:
                    if in_list:
                        html_out.append(f'</{list_type}>')
                    html_out.append(f'<{curr_type}>')
                    in_list = True
                    list_type = curr_type

                html_out.append(f'<li>{item_html}</li>')
                continue
            elif in_list:
                html_out.append(f'</{list_type}>')
                in_list = False
                list_type = None

            # Blank lines / Paragraphs
            if not line.strip():
                continue

            inline_html = self._inline_parse(line)
            html_out.append(f'<p>{inline_html}</p>')

        if in_code_block:
            code_content = html.escape("\n".join(code_lines))
            html_out.append(f'<pre><code>{code_content}</code></pre>')
        self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
        if in_list and list_type:
            html_out.append(f'</{list_type}>')

        return "\n".join(html_out)

    def _close_open_blocks(self, html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows):
        if in_blockquote and blockquote_lines:
            html_out.append(self._render_blockquote(blockquote_lines))
        if in_table and table_rows:
            html_out.append(self._render_table(table_rows))

    def _render_blockquote(self, lines):
        joined = " ".join(lines)
        callout_match = re.match(r'^\[\!(NOTE|WARNING|TIP|IMPORTANT|CAUTION)\]\s*(.*)$', joined, re.IGNORECASE)
        if callout_match:
            kind = callout_match.group(1).upper()
            content = self._inline_parse(callout_match.group(2))
            colors = {
                'NOTE': ('#00e5ff', '📘 NOTE'),
                'TIP': ('#50fa7b', '💡 TIP'),
                'WARNING': ('#ffb86c', '⚠️ WARNING'),
                'IMPORTANT': ('#bd93f9', '📌 IMPORTANT'),
                'CAUTION': ('#ff5555', '🚨 CAUTION')
            }
            color, label = colors.get(kind, ('#00e5ff', kind))
            return f'<blockquote style="border-left: 4px solid {color}; background-color: #1a1d2e; padding: 8px 12px; margin: 10px 0;"><strong style="color: {color};">{label}:</strong> {content}</blockquote>'
        
        content = self._inline_parse(joined)
        return f'<blockquote style="border-left: 4px solid #00e5ff; background-color: #141724; padding: 6px 12px; margin: 8px 0; color: #8be9fd;">{content}</blockquote>'

    def _render_table(self, rows):
        if not rows:
            return ""
        html_rows = []
        is_header = True
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            if all(re.match(r'^:?-+:?$', c) for c in cells if c):
                is_header = False
                continue
            tag = 'th' if is_header else 'td'
            cell_html = "".join([f'<{tag} style="border: 1px solid #323859; padding: 6px 10px;">{self._inline_parse(c)}</{tag}>' for c in cells])
            row_bg = '#1e2238' if is_header else '#0f111a'
            html_rows.append(f'<tr style="background-color: {row_bg};">{cell_html}</tr>')
            if is_header:
                is_header = False
        return f'<table style="border-collapse: collapse; width: 100%; margin: 12px 0; border: 1px solid #323859;">{"".join(html_rows)}</table>'

    def _inline_parse(self, text):
        text = html.escape(text)
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #ff79c6;">\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em style="color: #8be9fd;">\1</em>', text)
        text = re.sub(r'~~(.*?)~~', r'<del style="color: #6b7280;">\1</del>', text)
        text = re.sub(r'`(.*?)`', r'<code style="background-color: #1e2238; color: #f1fa8c; padding: 2px 5px; border-radius: 3px; font-family: monospace;">\1</code>', text)
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" style="max-width: 100%; border-radius: 4px;">', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: #38ef7d; text-decoration: none; font-weight: bold;">\1</a>', text)
        return text


def html(text):
    return MistuneParser().parse(text)


def markdown(text):
    return MistuneParser().parse(text)


def create_markdown(*args, **kwargs):
    return MistuneParser().parse
