# Project Documentation

This folder contains the deeper project documentation for the editor. The root `README.md` stays as the quick start; these files explain how the system is organized and how to extend it.

## Contents

- [Architecture](architecture.md): package layout, onion boundaries, and runtime composition.
- [Configuration](configuration.md): declarative config files and what each one controls.
- [Extension Points](extension-points.md): adding tokenizers, renderers, subrenderers, colors, and toolbar commands.
- [Renderers and Toolbar](renderers-and-toolbar.md): how CLI and Tk render the same editing model and shared toolbar.
- [Development](development.md): setup, test commands, and maintenance notes.

## High-Level Shape

The editor is intentionally split into layers:

- `domain`: pure value objects and the text model.
- `application`: editor use cases, registries, tokenization interfaces, subrendering interfaces, and undo history.
- `infrastructure`: concrete tokenizer and subrenderer implementations.
- `presentation`: user interfaces such as CLI and Tk.
- `config`: declarative lists and defaults.
- `composition`: runtime assembly that imports config and creates registries.

The main entry point is deliberately thin. `main.py` delegates to `editor.composition.launcher.run_editor()`, which parses arguments, creates the editor core, selects a renderer, and starts it.
