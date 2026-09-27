# Extension Points

The editor is designed so new behavior can be added by implementing a small interface and registering it through config.

## Add a Tokenizer

Create a class that subclasses `Tokenizer`:

```python
from editor.application.tokenization.base import TokenStyle, Tokenizer
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
```

Then add its import path to `editor/config/tokenizers.py`:

```python
TOKENIZERS = (
	"editor.infrastructure.tokenizers.demo.DemoTokenizer",
)
```

### Tokenizer Contract

`tokenize(source)` returns one list per source line. Each span is:

```python
(start_column, end_column, style_name)
```

The `style_name` should match one of the declared `TokenStyle` names when you want renderer colors.

### Token Inspection

Optional tokenizers can implement:

```python
def inspect(self, source, offset):
	return TokenInfo(...)
```

Renderers use this for hover/status inspection in Tk and F1 inspection in CLI.

## Add a Color

Add a tuple to `editor/config/colors.py`:

```python
("ROSE", "#b84b6a", "red")
```

After composition registers colors, the project can use `Color.ROSE`.

Terminal colors are limited by curses color names. Tk can use hex values.

## Add a Subrenderer

Subclass `SubRenderer`:

```python
from editor.application.subrendering.base import SubRenderer


class DemoSubRenderer(SubRenderer):
	extensions = ("demo",)

	def render_document(self, lines, base_spans):
		return base_spans
```

Then register it in `editor/config/subrenderers.py`:

```python
SUB_RENDERERS = (
	"editor.infrastructure.subrenderers.demo.DemoSubRenderer",
)
```

Subrenderers are best for view-level composition such as Markdown overlays or preview text. They should not mutate the document model.

## Add a Renderer

Create a renderer object with a `run()` method and a factory that accepts `core`:

```python
class DemoRenderer:
	def __init__(self, core):
		self.core = core

	def run(self):
		pass


def create_demo_renderer(core, **_options):
	return DemoRenderer(core)
```

Register it in `editor/config/renderers.py`:

```python
RENDERERS = (
	("demo", "editor.presentation.renderers.demo.create_demo_renderer", ()),
)
```

Renderers should use `EditorCore` as the source of truth for text, selections, formatting, messages, token spans, and file state.

## Add a Toolbar Command

Toolbar commands live in `editor/presentation/toolbar.py`.

Add a `ToolbarCommand` to `TOOLBAR_ITEMS`, then implement that command ID in each renderer's `_toolbar_actions()` method.

The shared toolbar definition keeps the command set consistent while still allowing each renderer to present commands in its native UI.
