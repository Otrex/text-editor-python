# Text Editor

A small Python text editor with a shared editing core and switchable renderers. The terminal renderer uses standard-library `curses`; the Tk renderer uses a Canvas and does not use Tkinter text-entry widgets.

For deeper documentation, see [`docs/`](docs/README.md).

Source is organized under `editor/` by responsibility:

- `domain/` contains pure editor value objects and the text model.
- `application/` contains editor orchestration, ports/interfaces, registries, and undo history.
- `infrastructure/` contains tokenizer and subrenderer adapter implementations.
- `presentation/` contains concrete CLI and Tk renderers.
- `config/` contains declarative registration settings only.
- `composition/` imports config declarations and builds runtime registries.

Choose a renderer when launching:

```sh
python main.py --renderer cli [file]
python main.py --renderer tk [file]
```

The terminal renderer is the default, so `python main.py [file]` is also valid. Renderers use the same document model, selections, edits, undo/redo, and tokenization results.

Use arrow keys to move. Hold Shift with an arrow key to extend a selection. In the terminal renderer, use Alt+Up or Alt+Down to add a caret on the neighboring line. Typing replaces selected text at every caret.

| Shortcut                 | Action                                     |
| ------------------------ | ------------------------------------------ |
| Ctrl+S                   | Save; prompts for a path on a new document |
| F6                       | Save As; always prompts for a target path  |
| Ctrl+O                   | Open a file                                |
| Ctrl+Q                   | Quit, with an unsaved-changes prompt       |
| Ctrl+A                   | Select all                                 |
| Ctrl+C / Ctrl+X / Ctrl+V | Copy / cut / paste                         |
| Ctrl+Z / Ctrl+Y          | Undo / redo                                |
| Ctrl+B / Ctrl+I          | Toggle bold / italic on selected text      |
| Ctrl++ / Ctrl+-          | Increase / decrease selected text size     |
| F2 / F3                  | Bold / italic in CLI renderer              |
| F4 / F5                  | Increase / decrease size in CLI renderer   |
| F1                       | Inspect token at caret (CLI renderer)      |
| Backspace / Delete       | Delete before / after each caret           |

Toolbar commands are defined once in `editor/presentation/toolbar.py`. Tk renders them as buttons and a font-size control; CLI renders the same command set in the top toolbar line.

In the Tk renderer, hover over a token to see its type and writing roles in the status bar; moving away clears the details. This uses the existing status area rather than an overlay, so it does not cover editor text. The CLI renderer supports terminals without mouse-motion events through F1 at the caret.

Formatting applies to selected text. Tk renders bold, italic, and 8–24 pt font sizes. Terminal emulators do not provide per-range point sizes through curses, so CLI uses bold/dim emphasis for larger/smaller sizes and reports the chosen size in the status line. These are editor display styles and are not serialized into the plain source file.

Default editor appearance lives in `editor/config/appearance.py`. Set `DEFAULT_FONT_FAMILY`, `DEFAULT_FONT_SIZE`, and `DEFAULT_FOREGROUND_COLOR` there; the foreground color name must exist in `editor/config/colors.py`.

Syntax coloring is selected by the active tokenizer plugin. Each plugin owns its file extensions, tokenizer function, and a `style_name -> Color` palette. A tokenizer accepts source text and returns one list per line, containing `(start_column, end_column, style_name)` spans. Each `Color` supplies renderer-specific values, so renderers do not need their own style-to-color table.

Super renderers can host subrenderers that compose view spans without owning input or document state. The configured `MarkdownSubRenderer` overlays heading, list, quote, link, emphasis, inline-code, and fenced-code styles for Markdown files, and exposes `render_view()` for preview renderers that need processed display lines. Add another import path to `editor/config/subrenderers.py` to register a subrenderer in the application.

`Color` accepts backend names as keyword arguments (for example, `Color(tk="#b04d35", terminal="red")`). The Tk renderer requests `tk`; the terminal renderer requests `terminal`. A new renderer can request its own backend key without changing tokenizer logic.

Plain-text and Markdown files also use the built-in English writing analyzer. It identifies common parts of speech (nouns, proper nouns, pronouns, verbs, auxiliaries, adjectives, adverbs, determiners, prepositions, conjunctions, numbers, and punctuation) and heuristic roles (subject, direct object, indirect object, object of a preposition, and subject complement). Role styling takes precedence for color, while the token records retain both `pos` and `roles`.

Writing analysis uses spaCy's `en_core_web_sm` pipeline. Install project dependencies and the trained English model before opening `.txt` or `.md` files:

```sh
source .venv/bin/activate
python -m pip install -e .
python -m spacy download en_core_web_sm
python main.py --renderer cli [file]
```

The analyzer maps spaCy `Doc` part-of-speech and dependency labels to editor styles and roles. It also preserves the spaCy dependency label in each `WritingToken`. The model is statistical and may misparse ambiguous words or complex clauses.

Custom POS detectors accept `(token, index, tokens)` and return a style/POS name or `None` to defer. Custom role detectors accept the tokens in one sentence and return `{token_index: role_or_roles}`.

To add a language tokenizer, subclass `Tokenizer`, declare its extensions and token styles, then register the class:

```python
from editor.application.core import EditorCore
from editor.application.tokenization.base import TokenStyle, Tokenizer
from editor.composition.registries import create_tokenizer_registry
from editor.domain.color import Color

class DemoTokenizer(Tokenizer):
	name = "Demo"
	extensions = ("demo",)
	styles = (
		TokenStyle("function", Color.RED),
		TokenStyle("variable", Color.BLUE),
	)

	def tokenize(self, source):
		return [[(0, 2, "function"), (3, len(source), "variable")]]

tokenizers = create_tokenizer_registry()
tokenizers.register(DemoTokenizer)
core = EditorCore("example.demo", tokenizers=tokenizers)
```

Each span is `(start_column, end_column, token_style_name)` for a single line. The registry still accepts the older function form through `TokenizerPlugin`, but class tokenizers are the preferred extension point.

To add a renderer, register a factory with `RendererRegistry.register(name, factory, *aliases)`. Factories receive the shared `core` and return an object with a `run()` method. Pass that registry to `main(..., renderers=registry)` to expose the renderer as a `--renderer` choice.

Clipboard integration in the terminal renderer uses `pbcopy`/`pbpaste` on macOS, `wl-copy`/`wl-paste` on Wayland, or `xclip` when available; otherwise, copy/paste works within the running editor.
