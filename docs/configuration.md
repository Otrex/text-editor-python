# Configuration

Configuration lives in `editor/config`. These files should stay declarative: constants, tuples, strings, and simple values only. Runtime object creation belongs in `editor/composition`.

## Appearance

File: `editor/config/appearance.py`

```python
DEFAULT_FONT_FAMILY = "Menlo"
DEFAULT_FONT_SIZE = 13
DEFAULT_FOREGROUND_COLOR = "BLACK"
```

- `DEFAULT_FONT_FAMILY`: used by the Tk renderer for the editor font.
- `DEFAULT_FONT_SIZE`: used by Tk as the base point size and by CLI as the baseline for bold/dim size hints.
- `DEFAULT_FOREGROUND_COLOR`: name of a color from `COLOR_DEFINITIONS`.

The configured foreground is resolved in `editor/composition/appearance.py`.

## Colors

File: `editor/config/colors.py`

Each color definition is:

```python
("NAME", "tk value", "terminal value")
```

Example:

```python
("RED", "#b04d35", "red")
```

At runtime, `editor/composition/colors.py` registers each definition onto `editor.domain.color.Color`, which allows tokenizers to refer to `Color.RED`, `Color.BLUE`, and so on.

## Tokenizers

File: `editor/config/tokenizers.py`

```python
TOKENIZERS = (
	"editor.infrastructure.tokenizers.python.PythonTokenizer",
	"editor.infrastructure.tokenizers.javascript.JavaScriptTokenizer",
	"editor.infrastructure.tokenizers.writing.WritingTokenizer",
)
```

Each entry is a dotted import path. `editor/composition/registries.py` imports each class and registers it with `TokenizerRegistry`.

## Subrenderers

File: `editor/config/subrenderers.py`

```python
SUB_RENDERERS = (
	"editor.infrastructure.subrenderers.markdown.MarkdownSubRenderer",
)
```

Subrenderers compose additional view spans or processed preview text without taking ownership of input or document state.

## Renderers

File: `editor/config/renderers.py`

Each renderer entry is:

```python
(name, factory_path, aliases)
```

Example:

```python
("tk", "editor.presentation.renderers.tk.create_tk_renderer", ("tkinter",))
```

Renderer factories receive a shared `EditorCore` and return an object with a `run()` method.

## Rule of Thumb

If the file needs loops, object creation, imports from concrete layers, or registry mutation, it belongs in `composition`, not `config`.
