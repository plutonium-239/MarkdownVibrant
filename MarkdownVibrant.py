import sublime
import sublime_plugin
import re
import html

# Track active preview sheets per window/view: { view_id: sheet_id }
PREVIEW_SHEETS = {}
PREVIEW_VIEWS = {} # { sheet_id: view_id }


class MiniHtmlMarkdownParser:
    """
    Lightweight, robust Markdown to Minihtml converter for Sublime Text.
    Designed specifically to output HTML compatible with Sublime's Minihtml engine.
    """
    def __init__(self, settings=None):
        self.settings = settings or {}

    def parse(self, text):
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
            # --- Code Fence Handling ---
            if line.strip().startswith("```"):
                if in_code_block:
                    # Close code block
                    code_content = html.escape("\n".join(code_lines))
                    lang_class = f' class="language-{code_lang}"' if code_lang else ''
                    html_out.append(f'<pre><code{lang_class}>{code_content}</code></pre>')
                    in_code_block = False
                    code_lines = []
                    code_lang = ""
                else:
                    # Close open blocks if any
                    self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                    in_list, in_blockquote, in_table = False, False, False
                    blockquote_lines, table_rows = [], []

                    in_code_block = True
                    code_lang = line.strip().lstrip("```").strip()
                continue

            if in_code_block:
                code_lines.append(line)
                continue

            # --- Table Handling ---
            if "|" in line and not line.strip().startswith(">"):
                stripped = line.strip()
                # Check if table row
                if stripped.startswith("|") and stripped.endswith("|"):
                    if not in_table:
                        self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, False, [])
                        in_list, in_blockquote = False, False
                        blockquote_lines = []
                        in_table = True
                    table_rows.append(stripped)
                    continue
            elif in_table:
                # Flush table
                html_out.append(self._render_table(table_rows))
                in_table = False
                table_rows = []

            # --- Blockquote Handling ---
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

            # --- Horizontal Rule ---
            if re.match(r'^\s*([-*_])\s*\1\s*\1\s*$', line):
                self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                in_list, in_blockquote, in_table = False, False, False
                blockquote_lines, table_rows = [], []
                html_out.append("<hr>")
                continue

            # --- Headings ---
            heading_match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if heading_match:
                self._close_open_blocks(html_out, in_list, in_blockquote, blockquote_lines, in_table, table_rows)
                in_list, in_blockquote, in_table = False, False, False
                blockquote_lines, table_rows = [], []

                level = len(heading_match.group(1))
                content = self._inline_parse(heading_match.group(2))
                html_out.append(f'<h{level}>{content}</h{level}>')
                continue

            # --- Lists & Checkboxes ---
            unordered_match = re.match(r'^\s*([*+-])\s+(.*)$', line)
            ordered_match = re.match(r'^\s*(\d+)\.\s+(.*)$', line)

            if unordered_match or ordered_match:
                item_content = unordered_match.group(2) if unordered_match else ordered_match.group(2)
                curr_type = 'ul' if unordered_match else 'ol'

                # Task list handling
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

            # --- Blank lines / Paragraphs ---
            if not line.strip():
                continue

            # Regular paragraph
            inline_html = self._inline_parse(line)
            html_out.append(f'<p>{inline_html}</p>')

        # Close any trailing blocks
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
        # Check for callouts like [!NOTE], [!WARNING], [!TIP], [!IMPORTANT]
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
            # Check if delimiter line (e.g. |---|---|)
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
        # Escape raw HTML
        text = html.escape(text)

        # Bold & Italic (***)
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # Bold (**)
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #ff79c6;">\1</strong>', text)
        # Italic (*)
        text = re.sub(r'\*(.*?)\*', r'<em style="color: #8be9fd;">\1</em>', text)
        # Strikethrough (~~)
        text = re.sub(r'~~(.*?)~~', r'<del style="color: #6b7280;">\1</del>', text)
        # Inline code (`)
        text = re.sub(r'`(.*?)`', r'<code style="background-color: #1e2238; color: #f1fa8c; padding: 2px 5px; border-radius: 3px; font-family: monospace;">\1</code>', text)
        # Images (![alt](url))
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1" style="max-width: 100%; border-radius: 4px;">', text)
        # Links ([title](url))
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: #38ef7d; text-decoration: none; font-weight: bold;">\1</a>', text)

        return text


class MarkdownLivePreviewCommand(sublime_plugin.TextCommand):
    """
    Toggles side-by-side live HTML Markdown preview in Sublime Text 4 using window.new_html_sheet.
    """
    def run(self, edit):
        window = self.view.window()
        if not window:
            return

        view_id = self.view.id()

        # Check if preview already open for this view
        if view_id in PREVIEW_SHEETS:
            sheet_id = PREVIEW_SHEETS[view_id]
            # Close preview sheet
            for sheet in window.sheets():
                if sheet.id() == sheet_id:
                    sheet.close()
                    break
            del PREVIEW_SHEETS[view_id]
            if sheet_id in PREVIEW_VIEWS:
                del PREVIEW_VIEWS[sheet_id]
            
            # Reset layout if 2 groups and group 1 empty
            if len(window.sheets_in_group(1)) == 0:
                window.set_layout({
                    "cols": [0.0, 1.0],
                    "rows": [0.0, 1.0],
                    "cells": [[0, 0, 1, 1]]
                })
            sublime.status_message("Markdown Preview Closed")
            return

        # Ensure split 2-column layout
        if window.num_groups() < 2:
            window.set_layout({
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 1.0],
                "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
            })

        # Render initial HTML
        html_content = self.render_html()
        doc_title = self.view.file_name() or "Markdown Preview"
        if doc_title and "/" in doc_title:
            doc_title = doc_title.split("/")[-1]
        sheet_title = f"Preview: {doc_title}"

        # Create HTML sheet in Group 1
        html_sheet = window.new_html_sheet(sheet_title, html_content, group=1)
        PREVIEW_SHEETS[view_id] = html_sheet.id()
        PREVIEW_VIEWS[html_sheet.id()] = view_id

        # Refocus the source markdown view in Group 0
        window.focus_view(self.view)
        sublime.status_message("Markdown Split Live Preview Opened")

    def render_html(self):
        full_text = self.view.substr(sublime.Region(0, self.view.size()))
        parser = MiniHtmlMarkdownParser()
        body_html = parser.parse(full_text)

        full_html = f"""
        <html>
        <head>
            <style>
                body {{
                    background-color: #0f111a;
                    color: #f0f4fc;
                    font-family: system-ui, -apple-system, sans-serif;
                    padding: 16px 20px;
                    line-height: 1.6;
                    font-size: 14px;
                }}
                h1 {{ color: #ff007f; border-bottom: 2px solid #ff007f; padding-bottom: 6px; margin-top: 20px; font-size: 22px; }}
                h2 {{ color: #bd93f9; border-bottom: 1px solid #323859; padding-bottom: 4px; margin-top: 18px; font-size: 18px; }}
                h3 {{ color: #00f5d4; margin-top: 16px; font-size: 16px; }}
                h4 {{ color: #50fa7b; margin-top: 14px; font-size: 14px; }}
                h5 {{ color: #ffb86c; margin-top: 12px; font-size: 13px; }}
                h6 {{ color: #ff5555; margin-top: 10px; font-size: 12px; }}
                a {{ color: #38ef7d; text-decoration: none; font-weight: bold; }}
                p {{ margin: 8px 0; }}
                ul, ol {{ padding-left: 20px; margin: 8px 0; }}
                li {{ margin: 4px 0; color: #f0f4fc; }}
                hr {{ border: none; height: 1px; background: linear-gradient(90deg, #ff007f, #00f5d4); margin: 20px 0; }}
                pre {{
                    background-color: #161824;
                    border: 1px solid #323859;
                    border-radius: 6px;
                    padding: 12px;
                    overflow-x: auto;
                    margin: 12px 0;
                }}
                code {{
                    font-family: Consolas, "Courier New", monospace;
                    color: #f1fa8c;
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            {body_html}
        </body>
        </html>
        """
        return full_html


class MarkdownVibrantEventListener(sublime_plugin.EventListener):
    """
    Listens for markdown text edits and automatically refreshes the HTML live preview.
    """
    def on_modified_async(self, view):
        view_id = view.id()
        if view_id in PREVIEW_SHEETS:
            sheet_id = PREVIEW_SHEETS[view_id]
            window = view.window()
            if not window:
                return
            
            # Find the preview sheet
            for sheet in window.sheets():
                if sheet.id() == sheet_id:
                    parser = MiniHtmlMarkdownParser()
                    full_text = view.substr(sublime.Region(0, view.size()))
                    body_html = parser.parse(full_text)
                    
                    full_html = f"""
                    <html>
                    <head>
                        <style>
                            body {{ background-color: #0f111a; color: #f0f4fc; font-family: sans-serif; padding: 16px; line-height: 1.6; }}
                            h1 {{ color: #ff007f; border-bottom: 2px solid #ff007f; font-size: 22px; }}
                            h2 {{ color: #bd93f9; border-bottom: 1px solid #323859; font-size: 18px; }}
                            h3 {{ color: #00f5d4; font-size: 16px; }}
                            h4 {{ color: #50fa7b; font-size: 14px; }}
                            a {{ color: #38ef7d; font-weight: bold; }}
                            hr {{ border: none; height: 1px; background: linear-gradient(90deg, #ff007f, #00f5d4); margin: 16px 0; }}
                            pre {{ background-color: #161824; border: 1px solid #323859; border-radius: 6px; padding: 10px; }}
                            code {{ font-family: monospace; color: #f1fa8c; }}
                        </style>
                    </head>
                    <body>{body_html}</body>
                    </html>
                    """
                    sheet.set_contents(full_html)
                    break

    def on_close(self, view):
        view_id = view.id()
        if view_id in PREVIEW_SHEETS:
            sheet_id = PREVIEW_SHEETS[view_id]
            del PREVIEW_SHEETS[view_id]
            if sheet_id in PREVIEW_VIEWS:
                del PREVIEW_VIEWS[sheet_id]


class FormatMarkdownTableCommand(sublime_plugin.TextCommand):
    """
    Automatically formats and aligns Markdown pipe tables.
    """
    def run(self, edit):
        for sel in self.view.sel():
            region = self.view.line(sel) if sel.empty() else sel
            lines = self.view.substr(region).splitlines()

            table_lines = [l.strip() for l in lines if "|" in l]
            if not table_lines:
                continue

            rows = []
            for line in table_lines:
                cells = [c.strip() for c in line.strip("|").split("|")]
                rows.append(cells)

            if not rows:
                continue

            # Determine max width per column
            num_cols = max(len(r) for r in rows)
            col_widths = [0] * num_cols

            for row in rows:
                for idx, cell in enumerate(row):
                    # Ignore delimiter line dashes in length calculation
                    if not re.match(r'^:?-+:?$', cell):
                        col_widths[idx] = max(col_widths[idx], len(cell))

            col_widths = [max(w, 3) for w in col_widths]

            # Format rows
            formatted_lines = []
            for row_idx, row in enumerate(rows):
                # Padding row cells
                cells_padded = []
                is_delimiter = all(re.match(r'^:?-+:?$', c) for c in row if c)

                for col_idx in range(num_cols):
                    cell = row[col_idx] if col_idx < len(row) else ""
                    width = col_widths[col_idx]

                    if is_delimiter:
                        # Retain alignment indicators
                        left_colon = ":" if cell.startswith(":") else "-"
                        right_colon = ":" if cell.endswith(":") else "-"
                        padded = left_colon + ("-" * (width - 2)) + right_colon
                    else:
                        padded = cell.ljust(width)
                    cells_padded.append(padded)

                formatted_lines.append("| " + " | ".join(cells_padded) + " |")

            formatted_table = "\n".join(formatted_lines)
            self.view.replace(edit, region, formatted_table)
            sublime.status_message("Markdown Table Formatted")


class GenerateMarkdownTocCommand(sublime_plugin.TextCommand):
    """
    Generates a Markdown Table of Contents from headings in the active document.
    """
    def run(self, edit):
        full_text = self.view.substr(sublime.Region(0, self.view.size()))
        lines = full_text.splitlines()
        toc_items = []

        for line in lines:
            match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                # Create anchor slug
                slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
                indent = "  " * (level - 1)
                toc_items.append(f"{indent}- [{title}](#{slug})")

        if not toc_items:
            sublime.status_message("No Markdown Headings Found")
            return

        toc_content = "<!-- TOC -->\n## Table of Contents\n\n" + "\n".join(toc_items) + "\n\n<!-- /TOC -->\n"
        
        # Insert at current cursor position or top of file
        pos = self.view.sel()[0].begin() if self.view.sel() else 0
        self.view.insert(edit, pos, toc_content)
        sublime.status_message("Table of Contents Inserted")


class ToggleMarkdownTaskCommand(sublime_plugin.TextCommand):
    """
    Toggles Markdown task checkbox [ ] <-> [x] on current line(s).
    """
    def run(self, edit):
        for sel in self.view.sel():
            line_region = self.view.line(sel)
            line_text = self.view.substr(line_region)

            if "[ ]" in line_text:
                new_text = line_text.replace("[ ]", "[x]", 1)
            elif "[x]" in line_text or "[X]" in line_text:
                new_text = line_text.replace("[x]", "[ ]", 1).replace("[X]", "[ ]", 1)
            else:
                # Add task checkbox to list item or line
                if re.match(r'^\s*[*+-]\s+', line_text):
                    new_text = re.sub(r'^(\s*[*+-]\s+)', r'\1[ ] ', line_text)
                else:
                    new_text = "- [ ] " + line_text

            self.view.replace(edit, line_region, new_text)


class ApplyMarkdownVibrantThemeCommand(sublime_plugin.TextCommand):
    """
    Applies the vibrant custom color scheme to the current view or settings.
    """
    def run(self, edit):
        scheme = "Packages/MarkdownVibrant/MarkdownVibrant.sublime-color-scheme"
        self.view.settings().set("color_scheme", scheme)
        sublime.status_message("Applied Markdown Vibrant Color Scheme")
