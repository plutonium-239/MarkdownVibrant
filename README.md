# MarkdownVibrant for Sublime Text 4

![img](./logo.svg)

An all-encompassing, high-contrast, feature-packed Markdown plugin for Sublime Text 4.

## Features

1. **A Vibrant Modern Color Scheme, applied automatically**:
   - Applies a vivid, accented color scheme designed to make typography fun. Made for humans that want to read.
   - Styled Headings (H1–H6), Bold, Italic, Code Fences, Blockquotes, Callouts, Tables, Links, and Task Checkboxes.
   - `MarkdownVibrant.sublime-color-scheme` is applied the moment a Markdown file opens, via syntax-specific settings files shipped for the `Markdown`, `MultiMarkdown`, and `Markdown Extended` syntaxes (look at #other-markdown-flavors).

2. **Native Side-by-Side HTML Live Preview**:
   - Live renders Markdown directly within Sublime Text in a split pane without opening an external browser window or external WebKit process.
   - Instant re-rendering as you type.
   - Uses Sublime Text 4's native `window.new_html_sheet` API and the fast `wenmode` Python Markdown parser.

4. **Built-in Markdown Enhancements**:
   - **GitHub-style Callouts**: Renders `[!NOTE]`, `[!WARNING]`, `[!TIP]`, `[!IMPORTANT]`, `[!CAUTION]` blockquotes with badges and accent borders.
   - **Task Checkboxes**: Easy toggling of `[ ]` and `[x]` items (`ToggleTaskCheckboxCommand`).
   - **Table of Contents (TOC) Generator**: Scans headings and inserts anchor links at cursor position (`GenerateMarkdownTocCommand`).
   - **Table Formatter**: Aligns pipe tables on demand (`Ctrl+Alt+Shift+T`) or automatically on save. Understands escaped pipes, rows with or without outer pipes, and `:---`/`:---:`/`---:` justification; tables inside code blocks are left alone. Table detection shares the same Markdown parser as the live preview, so the two features always agree on what a table is. (Inspired by the abandoned *Markdown Table Formatter* package. :( )
   - **Save Without Table Formatting** (`MarkdownVibrantSaveWithoutFormatCommand`, in the right-click menu): saves the file while skipping the on-save table autoformat once.

## Other Markdown Flavors

The theme ships settings files for the `Markdown`, `MultiMarkdown`, and `Markdown Extended` syntaxes. If you use another markdown-family syntax, create a file `Packages/User/<Syntax Name>.sublime-settings` containing:

```json
{
   "color_scheme": "Packages/MarkdownVibrant/MarkdownVibrant.sublime-color-scheme"
}
```

Settings in `Packages/User/` always take precedence over the ones this package ships, so you can also use the same file to opt out for a specific syntax by setting your own `color_scheme`.

## Keybindings

| Command                    | Windows / Linux    | macOS             |
|:---------------------------|:-------------------|:------------------|
| Toggle Split Live Preview  | `Ctrl+Alt+M`       | `Cmd+Option+M`    |
| Toggle Task Checkbox       | `Ctrl+Alt+C`       | `Cmd+Option+C`    |
| Generate Table of Contents | `Ctrl+Alt+G`       | `Cmd+Option+G`    |
| Format Markdown Tables     | `Ctrl+Alt+Shift+T` | `Cmd+Alt+Shift+T` |

## Table Formatting Settings

Configured in `MarkdownVibrant.sublime-settings`:

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

With a selection active, only the tables intersecting it are formatted; the formatted tables are then selected so the change is visible.

