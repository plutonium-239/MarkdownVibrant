# MarkdownVibrant for Sublime Text 4

An all-encompassing, high-contrast, feature-packed Markdown plugin for Sublime Text 4.

## Features

1. **Native Side-by-Side HTML Live Preview**:
   - Uses Sublime Text 4's native `window.new_html_sheet` API.
   - Live renders Markdown directly within Sublime Text in a split pane without opening an external browser window or external WebKit process.
   - Instant re-rendering as you type.

2. **Vibrant Modern Color Scheme**:
   - Replaces dull/grey default themes with vivid, neon-accented syntax highlighting (`MarkdownVibrant.sublime-color-scheme`).
   - Distinct, glowing color palette for Headings (H1-H6), Bold, Italic, Code Fences, Blockquotes, Callouts, Tables, Links, and Task Checkboxes.

3. **Built-in Markdown Enhancements**:
   - **Table Auto-Formatting**: Calculates column widths and cleanly aligns pipe tables (`| col1 | col2 |`).
   - **GitHub-style Callouts**: Renders `[!NOTE]`, `[!WARNING]`, `[!TIP]`, `[!IMPORTANT]`, `[!CAUTION]` blockquotes with badges and accent borders.
   - **Task Checkboxes**: Easy toggling of `[ ]` and `[x]` items.
   - **Table of Contents (TOC) Generator**: Scans headings and inserts anchor links at cursor position.

## Installation

1. Open Sublime Text.
2. Click **Preferences** > **Browse Packages...**
3. Copy or clone the `MarkdownVibrant` folder into your `Packages` directory.
4. Open any `.md` file in Sublime Text!

## Keybindings

| Command | Windows / Linux | macOS |
|---|---|---|
| Toggle Split Live Preview | `Ctrl+Alt+M` | `Cmd+Option+M` |
| Format Pipe Table | `Ctrl+Shift+T` | `Cmd+Shift+T` |
| Toggle Task Checkbox | `Ctrl+Alt+C` | `Cmd+Option+C` |
| Generate Table of Contents | `Ctrl+Alt+G` | `Cmd+Option+G` |
| Apply Vibrant Theme | `Ctrl+Alt+V` | `Cmd+Option+V` |

