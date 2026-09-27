# Renderers and Toolbar

The project currently has two renderers:

- CLI renderer: `editor/presentation/renderers/cli.py`
- Tk renderer: `editor/presentation/renderers/tk.py`

Both receive the same `EditorCore`, so they operate on the same editing behavior and application state.

## Renderer Responsibilities

A renderer should:

- draw the current document state,
- translate user input into `EditorCore` calls,
- show application messages and token inspection details,
- handle renderer-specific clipboard, prompt, or window behavior.

A renderer should not:

- implement core text editing rules,
- own tokenization logic,
- own file persistence logic,
- create global registration defaults.

## Shared Toolbar

Toolbar commands live in `editor/presentation/toolbar.py`.

The shared definitions include:

- file commands: open, save, save as, quit,
- history commands: undo, redo,
- clipboard commands: cut, copy, paste,
- formatting commands: bold, italic, font size up/down,
- inspection command: inspect token.

Each renderer maps command IDs to implementation methods with `_toolbar_actions()`.

### CLI Toolbar

The CLI renderer uses `toolbar_summary()` to render the shared commands as a top status line. Keyboard shortcuts execute the same command IDs through `_run_toolbar_action()`.

Because terminal UIs do not have clickable buttons, the toolbar is informational and shortcut-driven.

### Tk Toolbar

The Tk renderer builds buttons from `TOOLBAR_ITEMS`. It also inserts a font-size spinbox between font-size decrease and font-size increase.

Tk button commands call the same action map used by keyboard shortcuts.

## Formatting Differences

Tk can render actual font sizes, bold, and italic using `tkinter.font.Font`.

CLI cannot set per-character point sizes through curses. It represents larger text with bold, smaller text with dim, and reports the configured point size in the footer.

## Token Inspection

Tk supports hover inspection. Moving over a token updates the status bar with `TokenInfo.description`.

CLI supports inspection through F1 at the caret.

Both modes ask the active tokenizer for token metadata through `EditorCore.token_info_at()`.
