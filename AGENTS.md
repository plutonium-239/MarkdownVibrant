# AGENTS.md

Guidance for AI agents working in this repository.

## What this is

A **Sublime Text 4 package** (not a standalone Python project). There is no build system, package manager manifest, or CI. The repo is symlinked into Sublime's Packages directory:

```
~/Library/Application Support/Sublime Text/Packages/MarkdownVibrant -> /Users/pu239/MarkdownVibrant
```

Because of the symlink, saving files reloads the plugin live (AutomaticPackageReloader is installed). Changes take effect immediately in the running editor.

## Python environments (important)

- **Plugin code runs inside Sublime Text's Python 3.14 plugin host**, selected via `.python-version` (`3.14`) in the package root.
- `vendor/` contains a copy of mistune 3.3.4 and typing_extensions, and every entry-point module does `sys.path.insert(0, vendor)` at import time. Keep that preamble at the top of any new module that imports mistune.
- `dependencies.json` also declares mistune as a Package Control dependency for real installs; `vendor/` exists so local dev and `script_test.py` work without Package Control.
- Local dev uses `uv` (no `.venv`, no project file): run scripts with `uv run --python 3.14 python <script>`.
- ruff has been used here (`.ruff_cache/` exists) but there is no config file and no lint step wired anywhere.

## Running / testing

There is no test framework. To iterate on rendering logic without Sublime:

```
uv run --python 3.14 python script_test.py
```

Run it **from the repo root** — its imports (`from renderer import ...`, `sys.path.append('./vendor')`) rely on the CWD, and imports happen at the bottom of the file under `__main__`. It renders `README.md` through `CustomRenderer` + mistune and prints HTML.

`test.md`, `test_embedded.yml`, and `last_output.html` are scratch/manual-test files, not part of the package. `_render_preview_html` in `MarkdownVibrant.py` can write a debug copy of each preview render to `last_output.html` in the package root, but only when the `preview_debug_write_html` setting is enabled (off by default).

## Architecture

Three Python modules, all loaded by Sublime:

- **`MarkdownVibrant.py`** — all `sublime_plugin` commands plus `MarkdownVibrantEventListener`. Owns the live-preview lifecycle: `PREVIEW_SHEETS` (view_id -> (sheet_id, source_view)) and `PREVIEW_VIEWS` (sheet_id -> view_id). The preview is a `window.new_html_sheet` opened with `NewFileFlags.ADD_TO_SELECTION` so it appears as a split pane inside the current group without changing the window layout; `on_modified_async` re-renders and calls `sheet.set_contents`. Preview CSS is loaded with `sublime.load_resource("Packages/MarkdownVibrant/preview.css")` — that resource path is tied to the package name.
- **`renderer.py`** — `CustomRenderer(mistune.HTMLRenderer)` and custom mistune plugins. Tables are the tricky part: the standard mistune `"table"` plugin calls `table_cell`/`table_row`/etc., which the renderer hijacks to serialize rows/cells with `\x00` (row) and `\x01` (cell) sentinel characters; `table()` then reassembles them into a Unicode box-drawing ASCII table (`<div class="ascii-table">`). Ordered lists are also re-rendered as `<div class="ol-item">` with explicit numbers, using `_split_top_level_items` to keep nested sub-lists intact.
- **`table_formatter.py`** — `markdown_vibrant_format_table` command. Table detection does **not** use regex scanning: `find_tables()` runs the same mistune parser over the document and records source spans of top-level `table` tokens, so the formatter and the preview always agree on what a table is (and code blocks/quotes/lists are excluded automatically). Note: it bails out entirely if the text contains `\r`.

### Known inconsistencies / dead references

- `renderer.py` contains only the renderer; table parsing uses mistune's built-in `"table"` plugin in both the live preview (`MarkdownVibrant.py`) and `script_test.py`.
- `Main.sublime-menu` still references the command `apply_markdown_vibrant_theme`, which no longer exists (removed in commit a73ad64). That menu entry is dead.
- The README mentions `ToggleTaskCheckboxCommand`; the actual class is `ToggleMarkdownTaskCommand`.

## Sublime conventions used here

- Command names are derived from class names: `MarkdownLivePreviewCommand` -> `markdown_live_preview` (CamelCase class minus `Command`, snake_cased). Follow this when adding commands.
- All keybindings (`Default.sublime-keymap`, `Default (OSX).sublime-keymap`) are gated by a context selector `text.html.markdown`, so they only fire in Markdown views. Keep the two platform files in sync (macOS uses `super+`, others use `ctrl+`).
- The color scheme is auto-applied per syntax via `Markdown.sublime-settings`, `MultiMarkdown.sublime-settings`, and `Markdown Extended.sublime-settings`, each just setting `"color_scheme"` to the package's `.sublime-color-scheme`.
- User-facing settings live in `MarkdownVibrant.sublime-settings` and are read through a single module-level `_SETTINGS` object in `MarkdownVibrant.py`. Sublime automatically caches settings objects — `sublime.load_settings()` returns the same live instance and never re-reads from disk — so `.get()` is always cheap and always reflects current values.

## Release notes (Package Control)

`messages.json` at the package root maps keys (`"install"` or exact version strings) to files under `messages/`. On upgrade, Package Control shows every message file for versions between the old and new one; versions newer than the installed one are skipped, so future release notes can be pre-written. Message files render as raw text in the "Package Control Messages" view — `.md` is allowed but not formatted. Add a new `messages/<version>.md` (and its `messages.json` entry) with every release.

## Files that are pure Sublime resources

`MarkdownVibrant.sublime-color-scheme` (theme colors), `preview.css` (live-preview HTML styling), `Context.sublime-menu` (right-click menu), `Main.sublime-menu` (Tools menu). These are data, not code — edit carefully, they are JSON-with-comments and trailing-comma-tolerant (Sublime's format, stricter JSON parsers will reject them).
