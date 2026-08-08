import sublime
import sublime_plugin
import re
import html

# Try importing mistune (system or bundled)
try:
    import mistune
except ImportError:
    from . import mistune

PREVIEW_SHEETS = {}
PREVIEW_VIEWS = {}


class MarkdownLivePreviewCommand(sublime_plugin.TextCommand):
    """
    Toggles side-by-side live HTML Markdown preview in Sublime Text 4 using window.new_html_sheet.
    Uses Mistune parser for rendering.
    """
    def run(self, edit):
        window = self.view.window()
        if not window:
            return

        view_id = self.view.id()

        # Check if preview already open for this view
        if view_id in PREVIEW_SHEETS:
            sheet_id = PREVIEW_SHEETS[view_id]
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

        # Render initial HTML via Mistune
        html_content = self.render_html()
        doc_title = self.view.file_name() or "Markdown Preview"
        if doc_title and "/" in doc_title:
            doc_title = doc_title.split("/")[-1]
        sheet_title = f"Preview: {doc_title}"

        html_sheet = window.new_html_sheet(sheet_title, html_content, group=1)
        PREVIEW_SHEETS[view_id] = html_sheet.id()
        PREVIEW_VIEWS[html_sheet.id()] = view_id

        window.focus_view(self.view)
        sublime.status_message("Markdown Split Live Preview Opened")

    def render_html(self):
        full_text = self.view.substr(sublime.Region(0, self.view.size()))
        
        # Parse using mistune
        if hasattr(mistune, 'html'):
            body_html = mistune.html(full_text)
        elif hasattr(mistune, 'markdown'):
            body_html = mistune.markdown(full_text)
        elif callable(mistune):
            body_html = mistune(full_text)
        else:
            body_html = html.escape(full_text)

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
    Automatically applies the MarkdownVibrant color scheme whenever a Markdown file is opened or activated.
    """
    def on_load_async(self, view):
        self._auto_apply_vibrant_theme(view)

    def on_activated_async(self, view):
        self._auto_apply_vibrant_theme(view)

    def _auto_apply_vibrant_theme(self, view):
        if not view or not view.is_valid():
            return
        syntax = view.settings().get("syntax", "")
        if "markdown" in syntax.lower() or view.match_selector(0, "text.html.markdown"):
            vibrant_scheme = "Packages/MarkdownVibrant/MarkdownVibrant.sublime-color-scheme"
            if view.settings().get("color_scheme") != vibrant_scheme:
                view.settings().set("color_scheme", vibrant_scheme)

    def on_modified_async(self, view):
        view_id = view.id()
        if view_id in PREVIEW_SHEETS:
            sheet_id = PREVIEW_SHEETS[view_id]
            window = view.window()
            if not window:
                return
            
            for sheet in window.sheets():
                if sheet.id() == sheet_id:
                    full_text = view.substr(sublime.Region(0, view.size()))
                    if hasattr(mistune, 'html'):
                        body_html = mistune.html(full_text)
                    elif hasattr(mistune, 'markdown'):
                        body_html = mistune.markdown(full_text)
                    else:
                        body_html = html.escape(full_text)
                    
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
                slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
                indent = "  " * (level - 1)
                toc_items.append(f"{indent}- [{title}](#{slug})")

        if not toc_items:
            sublime.status_message("No Markdown Headings Found")
            return

        toc_content = "<!-- TOC -->\n## Table of Contents\n\n" + "\n".join(toc_items) + "\n\n<!-- /TOC -->\n"
        
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
