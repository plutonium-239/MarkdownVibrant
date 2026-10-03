import sys
import os

_vendor = os.path.join(os.path.dirname(__file__), 'vendor')
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)

from .renderer import CustomRenderer
import mistune
import sublime
import sublime_plugin
import re
import html

# view_id -> (preview_sheet_id, source_view)
PREVIEW_SHEETS = {}
PREVIEW_VIEWS = {}  # sheet_id -> view_id (reverse lookup)

def _close_preview_sheet(view_id, sheet_id):
    """Close a preview HTML sheet and clean up tracking dicts."""
    for w in sublime.windows():
        for sheet in w.sheets():
            if sheet.id() == sheet_id:
                sheet.close()
                break
    PREVIEW_SHEETS.pop(view_id, None)
    PREVIEW_VIEWS.pop(sheet_id, None)



def _render_preview_html(text):
    renderer = CustomRenderer()
    markdown = mistune.create_markdown(
        renderer=renderer,
        escape=False,
        plugins=["strikethrough", "footnotes", "table"],
    )
    body_html = markdown(text)
    assert isinstance(body_html, str)
    preview_css = sublime.load_resource("Packages/MarkdownVibrant/preview.css")
    full_html = (
        "<html>\n<head>\n<style>\n"
        + preview_css
        + "\n</style>\n</head>\n<body>\n"
        + body_html
        + "\n</body>\n</html>"
    )
    with open('/Users/pu239/MarkdownVibrant/last_output.html', 'w') as f:
        f.write(full_html)
    return full_html


class MarkdownLivePreviewCommand(sublime_plugin.TextCommand):
    """
    Toggles a live HTML Markdown preview in Sublime Text 4 using window.new_html_sheet.

    Uses the "split view" mechanism (a temporary pane within the same group)
    instead of creating a new column group, so the existing window layout is preserved.

    Uses Mistune parser for rendering.
    """
    def run(self, edit):
        window = self.view.window()
        if not window:
            return

        view_id = self.view.id()

        # Check if preview already open for this view
        if view_id in PREVIEW_SHEETS:
            _close_preview_sheet(view_id, PREVIEW_SHEETS[view_id][0])
            sublime.status_message("Markdown Preview Closed")
            return

        # Render initial HTML via Mistune
        full_text = self.view.substr(sublime.Region(0, self.view.size()))
        html_content = _render_preview_html(full_text)
        doc_title = self.view.file_name() or "Markdown Preview"
        if doc_title and "/" in doc_title:
            doc_title = doc_title.split("/")[-1]
        sheet_title = f"Preview: {doc_title}"

        # Use ADD_TO_SELECTION so the HTML sheet opens as a temporary split pane
        # within the current group, mirroring the built-in "Split View" behavior
        # without altering the window's column/row layout.
        html_sheet = window.new_html_sheet(
            sheet_title,
            html_content,
            flags=sublime.NewFileFlags.ADD_TO_SELECTION,
            group=-1,
        )
        PREVIEW_SHEETS[view_id] = (html_sheet.id(), self.view)
        PREVIEW_VIEWS[html_sheet.id()] = view_id

        window.focus_view(self.view)
        sublime.status_message("Markdown Split Live Preview Opened")


class MarkdownVibrantEventListener(sublime_plugin.EventListener):
    """
    Listens for markdown text edits and automatically refreshes the HTML live preview.
    """
    def on_activated_async(self, view):
        settings = sublime.load_settings("MarkdownVibrant.sublime-settings")
        if settings.get("auto_close_singled_out_preview", True):
            sublime.set_timeout(self._close_singled_out_previews, 50)

    def _close_singled_out_previews(self):
        if not PREVIEW_SHEETS:
            return
        for view_id, (sheet_id, source_view) in list(PREVIEW_SHEETS.items()):
            if not source_view.is_valid():
                _close_preview_sheet(view_id, sheet_id)
                continue
            window = source_view.window()
            if window is None:
                _close_preview_sheet(view_id, sheet_id)
                continue
            source_sheet = source_view.sheet()
            if source_sheet is None:
                _close_preview_sheet(view_id, sheet_id)
                continue
            selected_ids = {s.id() for s in window.selected_sheets()}
            if source_sheet.id() not in selected_ids:
                _close_preview_sheet(view_id, sheet_id)

    def on_modified_async(self, view):
        view_id = view.id()
        if view_id not in PREVIEW_SHEETS:
            return
        sheet_id = PREVIEW_SHEETS[view_id][0]
        window = view.window()
        if not window:
            return

        for sheet in window.sheets():
            if sheet.id() == sheet_id:
                full_text = view.substr(sublime.Region(0, view.size()))
                full_html = _render_preview_html(full_text)
                sheet.set_contents(full_html)
                break

    def on_close(self, view):
        view_id = view.id()
        if view_id in PREVIEW_SHEETS:
            _close_preview_sheet(view_id, PREVIEW_SHEETS[view_id][0])


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
