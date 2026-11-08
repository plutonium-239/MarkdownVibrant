import sys
import os
import time
from functools import partial, wraps

_vendor = os.path.join(os.path.dirname(__file__), 'vendor')
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)

from .renderer import CustomRenderer, PRESET
from wenmode import Wenmode
from wenmode.plugins import github_alert, mark, superscript, subscript
import sublime
import sublime_plugin
import re

# view_id -> (preview_sheet_id, source_view)
PREVIEW_SHEETS = {}
PREVIEW_VIEWS = {}  # sheet_id -> view_id (reverse lookup)
_SKIP_NEXT_AUTOFORMAT = set()  # view ids: skip table autoformat on the next save

_SETTINGS = sublime.load_settings("MarkdownVibrant.sublime-settings")

def _render_alert(renderer, node, context):
    """Draw a GitHub-alert node, honoring `preview_enable_callouts` live:
    a styled callout box when on, a plain blockquote (with the `[!NAME]`
    marker re-emitted) when off."""
    if _SETTINGS.get("preview_enable_callouts", True):
        return github_alert.render_github_html_alert(renderer, node, context)
    marker = f"<p>[!{node.name.upper()}]</p>\n"
    return "<blockquote>\n" + marker + renderer.render_children(node.children, context) + "</blockquote>\n"


_wen = Wenmode(PRESET, renderer=CustomRenderer(), plugins=[mark, superscript, subscript, github_alert.configure()])
_wen.renderer.register_handler("githubAlert", _render_alert)


def debounced(delay_in_ms, sync=False):
    """Delay calls to an event hook until it wasn't triggered for n ms.

    *delay_in_ms* is a number, or a callable returning one, so the delay
    can be read live from settings. Adapted from
    https://forum.sublimetext.com/t/70017.
    """
    set_timeout = sublime.set_timeout if sync else sublime.set_timeout_async

    def decorator(func):
        to_call_times = {}

        def _debounced_callback(view, callback):
            vid = view.id()
            threshold = to_call_times.get(vid)
            if not threshold:
                return
            if not view.is_valid():
                del to_call_times[vid]
                return
            diff = threshold - time.time() * 1000
            if diff > 0:
                set_timeout(partial(_debounced_callback, view, callback), diff)
            else:
                del to_call_times[vid]
                callback()

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            view = self.view if hasattr(self, 'view') else args[0]
            if not view.is_valid():
                return
            delay = delay_in_ms() if callable(delay_in_ms) else delay_in_ms
            delay = max(delay, 0)
            vid = view.id()
            busy = vid in to_call_times
            to_call_times[vid] = time.time() * 1000 + delay
            if busy:
                return
            callback = partial(func, self, *args, **kwargs)
            set_timeout(partial(_debounced_callback, view, callback), delay)

        return wrapper

    return decorator


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
    body_html = _wen.render(text)
    preview_css = sublime.load_resource("Packages/MarkdownVibrant/preview.css")
    font_size = _SETTINGS.get("preview_font_size_px", 14)
    background = _SETTINGS.get("preview_background", "#0f111a")
    override_css = (
        f"html {{ font-size: {font_size}px; }}\n"
        f"body {{ background-color: {background}; }}\n"
    )
    full_html = (
        "<html>\n<head>\n<style>\n"
        + preview_css
        + "\n" + override_css
        + "</style>\n</head>\n<body>\n"
        + body_html
        + "\n</body>\n</html>"
    )
    if _SETTINGS.get("preview_debug_write_html", False):
        debug_path = os.path.join(os.path.dirname(__file__), "last_output.html")
        with open(debug_path, "w") as f:
            f.write(full_html)
    return full_html


class MarkdownVibrantLivePreviewCommand(sublime_plugin.TextCommand):
    """
    Toggles a live HTML Markdown preview in Sublime Text 4 using window.new_html_sheet.

    Uses the "split view" mechanism (a temporary pane within the same group)
    instead of creating a new column group, so the existing window layout is preserved.

    Uses the Wenmode parser for rendering.
    """
    def is_visible(self):
        return self.view.match_selector(0, "text.html.markdown")

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

        # Render initial HTML via Wenmode
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


class MarkdownVibrantSaveWithoutFormatCommand(sublime_plugin.TextCommand):
    """Saves the view while skipping the on-save table autoformat once."""

    def is_visible(self):
        return self.view.match_selector(0, "text.html.markdown")

    def run(self, edit):
        _SKIP_NEXT_AUTOFORMAT.add(self.view.id())
        self.view.run_command("save")


class MarkdownVibrantEventListener(sublime_plugin.EventListener):
    """
    Listens for markdown text edits and automatically refreshes the HTML live preview.
    """
    def on_activated_async(self, view):
        if _SETTINGS.get("preview_auto_close_singled_out", True):
            sublime.set_timeout(self._close_singled_out_previews, 50)

    def on_pre_save(self, view):
        if view.id() in _SKIP_NEXT_AUTOFORMAT:
            _SKIP_NEXT_AUTOFORMAT.discard(view.id())
            return
        if not _SETTINGS.get("table_autoformat_on_save", True):
            return
        if not view.match_selector(0, "text.html.markdown"):
            return
        view.run_command("markdown_vibrant_format_table", {"format_all": True})

    def on_post_save(self, view):
        _SKIP_NEXT_AUTOFORMAT.discard(view.id())

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

    @debounced(lambda: _SETTINGS.get("preview_update_delay_ms", 150))
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


class MarkdownVibrantGenerateTocCommand(sublime_plugin.TextCommand):
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


class MarkdownVibrantToggleTaskCommand(sublime_plugin.TextCommand):
    """
    Toggles Markdown task checkbox [ ] <-> [x] on current line(s).
    """
    def is_visible(self):
        return self.view.match_selector(0, "text.html.markdown")

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
