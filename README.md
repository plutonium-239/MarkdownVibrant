# MarkdownVibrant for Sublime Text 4

An all-encompassing, high-contrast, feature-packed Markdown plugin for Sublime Text 4.

## Features

1. **Automatic Theme Activation**:
   - Automatically detects and applies `MarkdownVibrant.sublime-color-scheme` whenever you open or switch to a Markdown file in Sublime Text.

2. **Native Side-by-Side HTML Live Preview (Powered by Mistune)**:
   - Uses Sublime Text 4's native `window.new_html_sheet` API and the fast `mistune` Python Markdown parser.
   - Live renders Markdown directly within Sublime Text in a split pane without opening an external browser window or external WebKit process.
   - Instant re-rendering as you type.

3. **Vibrant Modern Color Scheme**:
   - Replaces dull/grey default themes with vivid, neon-accented syntax highlighting (`MarkdownVibrant.sublime-color-scheme`).
   - Styled Headings (H1–H6), Bold, Italic, Code Fences, Blockquotes, Callouts, Tables, Links, and Task Checkboxes.

4. **Built-in Markdown Enhancements**:
   - **GitHub-style Callouts**: Renders `[!NOTE]`, `[!WARNING]`, `[!TIP]`, `[!IMPORTANT]`, `[!CAUTION]` blockquotes with badges and accent borders.
   - **Task Checkboxes**: Easy toggling of `[ ]` and `[x]` items (`ToggleTaskCheckboxCommand`).
   - **Table of Contents (TOC) Generator**: Scans headings and inserts anchor links at cursor position (`GenerateMarkdownTocCommand`).

## Recommended Packages

- **[Markdown Table Formatter](https://packagecontrol.io/packages/Markdown%20Table%20Formatter)**: We recommend installing this package via Package Control for fast, automatic table formatting and pipe alignment in Sublime Text.

## Keybindings

| Command | Windows / Linux | macOS |
|---|---|---|
| Toggle Split Live Preview | `Ctrl+Alt+M` | `Cmd+Option+M` |
| Toggle Task Checkbox | `Ctrl+Alt+C` | `Cmd+Option+C` |
| Generate Table of Contents | `Ctrl+Alt+G` | `Cmd+Option+G` |
| Apply Vibrant Theme | `Ctrl+Alt+V` | `Cmd+Option+V` |

