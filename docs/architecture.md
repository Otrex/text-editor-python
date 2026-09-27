# Architecture

The project follows an onion-style architecture. Inner layers describe the editor model and application behavior. Outer layers provide concrete adapters, runtime wiring, and UI.

## Dependency Direction

Dependencies should point inward:

- `domain` should not import other editor layers.
- `application` can import `domain`, but should not import `infrastructure`, `presentation`, `composition`, or `config`.
- `infrastructure` implements application interfaces and can import `application` and `domain`.
- `presentation` adapts the application to UI frameworks.
- `config` contains declarative values only.
- `composition` imports config and concrete adapters, then builds runtime objects.

## Package Responsibilities

### `editor/domain`

Pure editor data and behavior:

- `TextModel`: text storage, line access, and position/offset conversion.
- `Position` and `Selection`: caret and selection value objects.
- `Color`: renderer-specific color values behind one semantic object.
- `TokenInfo`: token inspection metadata shown in status/inspection UI.

### `editor/application`

Application behavior and interfaces:

- `EditorCore`: central editing use case object. It owns the text model, selections, formatting, history, tokenization lookup, file open/save, and change notification.
- `UndoHistory`: grouped undo/redo state management.
- `application.tokenization`: tokenizer interface classes and adapters.
- `application.subrendering`: subrenderer interfaces and rendered-document value object.
- `application.registries`: generic, tokenizer, renderer, and subrenderer registries.

### `editor/infrastructure`

Concrete implementations:

- `tokenizers/python.py`: Python tokenizer.
- `tokenizers/javascript.py`: JavaScript tokenizer.
- `tokenizers/writing/`: English writing tokenizer and analyzer.
- `subrenderers/markdown.py`: Markdown style overlays and preview-line processing.

Infrastructure is replaceable. A tokenizer or subrenderer can be added without changing `EditorCore`.

### `editor/presentation`

Renderer-facing code:

- `renderers/cli.py`: curses renderer.
- `renderers/tk.py`: Tk Canvas renderer.
- `toolbar.py`: shared toolbar command definitions consumed by renderers.

Renderers should translate user input into `EditorCore` calls. They should not own editing rules.

### `editor/config`

Declarative project settings:

- `appearance.py`: default font family, font size, and foreground color.
- `colors.py`: configured semantic colors.
- `renderers.py`: renderer factory import paths and aliases.
- `tokenizers.py`: tokenizer class import paths.
- `subrenderers.py`: subrenderer import paths.

Config files should contain definitions only. Avoid object creation, imports of concrete application objects, or registration logic here.

### `editor/composition`

Runtime assembly:

- `launcher.py`: application startup orchestration.
- `registries.py`: builds renderer, tokenizer, and subrenderer registries from config.
- `appearance.py`: resolves configured appearance values into runtime objects.
- `colors.py`: registers configured colors onto the `Color` class.
- `importing.py`: imports objects by dotted path.

Composition is where config definitions become runtime objects.

## Startup Flow

1. `main.py` calls `run_editor()`.
2. `EditorLauncher` parses CLI arguments.
3. Composition builds the renderer registry and tokenizer registry.
4. `EditorCore` is created with the configured tokenizer registry.
5. The selected renderer receives the shared `EditorCore`.
6. The renderer runs and translates UI events into `EditorCore` operations.

## Editing Flow

1. A renderer receives input.
2. The renderer calls methods such as `replace_selections()`, `move_carets()`, `set_format()`, `undo()`, or `save_file()`.
3. `EditorCore` updates model state and records undo history where appropriate.
4. `EditorCore` calls `on_change`.
5. The renderer redraws from current model, selections, formatting, tokenizer spans, and subrenderer spans.
