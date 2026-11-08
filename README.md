# MarkdownVibrant for Sublime Text 4

![img](./logo.svg)

An all-encompassing, high-contrast, feature-packed Markdown plugin for Sublime Text 4.

## Features

1. **A Vibrant Modern Color Scheme, applied automatically**:
   - Applies a vivid, accented color scheme designed to make typography fun. Made for humans that want to read.
   - Styled Headings (H1–H6), Bold, Italic, Code Fences, Blockquotes, Callouts, Tables, Links, and Task Checkboxes.
   - `MarkdownVibrant.sublime-color-scheme` is applied the moment a Markdown file opens, via syntax-specific settings files shipped for the `Markdown`, `MultiMarkdown`, and `Markdown Extended` syntaxes ([some more detail here](#other-markdown-flavors)).

2. **Native Side-by-Side HTML Live Preview**:
   - Live renders Markdown directly within Sublime Text in a split pane without opening an external browser window or external WebKit process.
   - Instant re-rendering as you type.
   - Uses Sublime Text 4's native `window.new_html_sheet` API and the fast `wenmode` Python Markdown parser.

4. **Built-in Markdown Enhancements**:
   - **GitHub-style Callouts**: Renders `[!NOTE]`, `[!WARNING]`, `[!TIP]`, `[!IMPORTANT]`, `[!CAUTION]` blockquotes with badges and accent borders.
   - **Task Checkboxes**: Easy toggling of `[ ]` and `[x]` items (`MarkdownVibrantToggleTaskCommand`).
   - **Table of Contents (TOC) Generator**: Scans headings and inserts anchor links at cursor position (`MarkdownVibrantGenerateTocCommand`).
   - **Table Formatter**: Aligns pipe tables on demand (`Ctrl+Alt+Shift+T`) or automatically on save. Understands escaped pipes, rows with or without outer pipes, and `:---`/`:---:`/`---:` justification; tables inside code blocks are left alone. Table detection shares the same Markdown parser as the live preview, so the two features always agree on what a table is. (Inspired by the abandoned *Markdown Table Formatter* package. :( )
   - **Save Without Table Formatting** (`MarkdownVibrantSaveWithoutFormatCommand`, in the right-click menu): saves the file while skipping the on-save table autoformat once.

## Keybindings and Commands

| Command                    | Windows / Linux    | macOS             | Command Name |
|:---------------------------|:-------------------|:------------------|:-------------|
| Toggle Split Live Preview  | `Ctrl+Alt+M`       | `Cmd+Option+M`    |              |
| Toggle Task Checkbox       | `Ctrl+Alt+C`       | `Cmd+Option+C`    |              |
| Generate Table of Contents | `Ctrl+Alt+G`       | `Cmd+Option+G`    |              |
| Format Markdown Tables     | `Ctrl+Alt+Shift+T` | `Cmd+Alt+Shift+T` |              |

## Configuration

Configured in `MarkdownVibrant.sublime-settings`:

### Preview Settings

```json
{
   "preview_update_delay_ms": 150,
   "preview_background": "#0f111a",
   "preview_font_size_px": 14,
   "preview_enable_callouts": true,
   "preview_auto_close_singled_out": true,
   "preview_debug_write_html": false,
}
```

- `preview_update_delay_ms`: debounce for the live preview. While you are typing, re-rendering waits until this many milliseconds pass without a change, so the preview refreshes once per pause instead of on every keystroke. Set to `0` to refresh on every change.
- `preview_background`: background color of the preview pane (any CSS color, e.g. `#0f111a` or `white`).
- `preview_font_size_px`: base font size of the preview. Everything scales relative to it (headings, code, tables).
- `preview_enable_callouts`: render GitHub-style *admonitions*; `[!NOTE]` / `[!TIP]` / `[!IMPORTANT]` / `[!WARNING]` / `[!CAUTION]` blockquotes as colored callout boxes in the preview. Affects the preview only.
- `preview_auto_close_singled_out`: close the split preview automatically when its source view is no longer part of the window's selected sheets.
- `preview_debug_write_html`: write every rendered preview to `last_output.html` in the package folder, for debugging the HTML output. please dont forget to turn this off, unnecessary writes will wear out your disk very quickly!


### Table Formatting Settings

```json
{
   "table_margin": 1,
   "table_padding": 0,
   "table_default_justification": "LEFT",
   "table_autoformat_on_save": true
}
```

- `table_margin`: spaces kept between the `|` delimiters and the cell text, on both sides.
- `table_padding`: extra space inside each column, distributed according to justification (trailing for left, leading for right, split for centered).
- `table_default_justification`: `LEFT`, `CENTER` or `RIGHT`, applied to columns whose separator has no colons.
- `table_autoformat_on_save`: reformat all tables when a Markdown file is saved.

With a selection active, only the tables intersecting it are formatted. The formatted tables are selected so the change is visible.

### Other Markdown Flavors

The theme ships settings files for the `Markdown`, `MultiMarkdown`, and `Markdown Extended` syntaxes. If you use another markdown-family syntax, create a file `Packages/User/<Syntax Name>.sublime-settings` containing:

```json
{
   "color_scheme": "Packages/MarkdownVibrant/MarkdownVibrant.sublime-color-scheme"
}
```

Settings in `Packages/User/` always take precedence over the ones this package ships, so you can also use the same file to opt out for a specific syntax by setting your own `color_scheme`.