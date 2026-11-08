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
- `vendor/` contains a copy of wenmode 0.15.2 (pure Python, zero dependencies), and every entry-point module does `sys.path.insert(0, vendor)` at import time. Keep that preamble at the top of any new module that imports wenmode. wenmode is **not** available as a Package Control dependency, so the vendored copy is the delivery mechanism for real installs too.
- Leftovers from the mistune era (intentionally not removed): `vendor/mistune/`, `vendor/typing_extensions.py`, and the mistune entry in `dependencies.json`. Nothing imports them anymore.
- Local dev uses `uv` (no `.venv`, no project file): run scripts with `uv run --python 3.14 python <script>`.
- ruff has been used here (`.ruff_cache/` exists) but there is no config file and no lint step wired anywhere.

## Running / testing

There is no test framework. To iterate on rendering logic without Sublime:

```
uv run --python 3.14 python script_test.py
```

Run it **from the repo root** — its imports (`from renderer import ...`) rely on the CWD, and imports happen at the bottom of the file under `__main__` (importing `renderer` first also puts `vendor/` on `sys.path`). It renders `README.md` through `CustomRenderer` + wenmode and prints HTML.

`test.md`, `test_embedded.yml`, and `last_output.html` are scratch/manual-test files, not part of the package. `_render_preview_html` in `MarkdownVibrant.py` can write a debug copy of each preview render to `last_output.html` in the package root, but only when the `preview_debug_write_html` setting is enabled (off by default).

## Architecture

Three Python modules, all loaded by Sublime:

- **`MarkdownVibrant.py`** — all `sublime_plugin` commands plus `MarkdownVibrantEventListener`. Owns the live-preview lifecycle: `PREVIEW_SHEETS` (view_id -> (sheet_id, source_view)) and `PREVIEW_VIEWS` (sheet_id -> view_id). The preview is a `window.new_html_sheet` opened with `NewFileFlags.ADD_TO_SELECTION` so it appears as a split pane inside the current group without changing the window layout; `on_modified_async` re-renders and calls `sheet.set_contents`. Preview CSS is loaded with `sublime.load_resource("Packages/MarkdownVibrant/preview.css")` — that resource path is tied to the package name.
- **`renderer.py`** — `CustomRenderer(wenmode.HTMLRenderer)` with instance-registered handlers (module-level `render_list`/`render_table` functions wired up in `__init__`, so the shared `HTMLRenderer` dispatch table stays untouched), plus `PRESET = github()` — the shared GFM rule set (tables, task lists, strikethrough, autolinks, footnotes) used by both the preview and the formatter. The renderer is constructed with `escape=False, sanitize_urls=False, sanitize_attrs=False` for raw-HTML passthrough. Handlers walk nodes directly: ordered lists become `<div class="ol-item">` with explicit numbers (one per `ListItem` child), tables become a Unicode box-drawing ASCII table (`<div class="ascii-table">`) from `Table`/`TableRow`/`TableCell` nodes. Task markers are re-emitted as literal `[x] `/`[ ] ` text to match the old mistune output.
- **`table_formatter.py`** — `markdown_vibrant_format_table` command. Table detection does **not** use regex scanning: `find_tables()` parses the document with a module-level `Parser` built from PRESET's block rules only (inline rules filtered out for speed) with `positions=True`, then records source spans of top-level `table` nodes, so the formatter and the preview agree on what a table is (and code blocks/quotes/lists are excluded automatically). Caveat vs the old mistune version: non-piped "nptable" syntax is no longer detected (wenmode only parses GFM pipe tables). Note: it bails out entirely if the text contains `\r`.

### Known inconsistencies / dead references

None currently.

## Sublime conventions used here

- Command names are derived from class names: `MarkdownVibrantLivePreviewCommand` -> `markdown_vibrant_live_preview` (CamelCase class minus `Command`, snake_cased). All commands are prefixed `markdown_vibrant_`. Follow this when adding commands.
- All keybindings (`Default.sublime-keymap`, `Default (OSX).sublime-keymap`) are gated by a context selector `text.html.markdown`, so they only fire in Markdown views. Keep the two platform files in sync (macOS uses `super+`, others use `ctrl+`).
- The color scheme is auto-applied per syntax via `Markdown.sublime-settings`, `MultiMarkdown.sublime-settings`, and `Markdown Extended.sublime-settings`, each just setting `"color_scheme"` to the package's `.sublime-color-scheme`.
- User-facing settings live in `MarkdownVibrant.sublime-settings` and are read through a single module-level `_SETTINGS` object in `MarkdownVibrant.py`. Sublime automatically caches settings objects — `sublime.load_settings()` returns the same live instance and never re-reads from disk — so `.get()` is always cheap and always reflects current values.

## Release notes (Package Control)

`messages.json` at the package root maps keys (`"install"` or exact version strings) to files under `messages/`. On upgrade, Package Control shows every message file for versions between the old and new one; versions newer than the installed one are skipped, so future release notes can be pre-written. Message files render as raw text in the "Package Control Messages" view — `.md` is allowed but not formatted. Add a new `messages/<version>.md` (and its `messages.json` entry) with every release.

## Files that are pure Sublime resources

`MarkdownVibrant.sublime-color-scheme` (theme colors), `preview.css` (live-preview HTML styling), `Context.sublime-menu` (right-click menu), `Main.sublime-menu` (Tools menu). These are data, not code — edit carefully, they are JSON-with-comments and trailing-comma-tolerant (Sublime's format, stricter JSON parsers will reject them).
