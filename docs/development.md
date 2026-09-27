# Development

## Setup

Create and activate a virtual environment, then install the project:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The writing tokenizer uses spaCy's English model:

```sh
python -m spacy download en_core_web_sm
```

## Run the Editor

```sh
python main.py --renderer cli [file]
python main.py --renderer tk [file]
```

The CLI renderer is the default:

```sh
python main.py [file]
```

## Tests

Run the full test suite:

```sh
python -m unittest discover -s tests
```

Compile-check the project:

```sh
python -m compileall -q editor tests main.py
```

When running in environments where writing `__pycache__` beside source is undesirable, set `PYTHONPYCACHEPREFIX`:

```sh
PYTHONPYCACHEPREFIX=/tmp/editor-pycache python -m unittest discover -s tests
```

## Maintenance Notes

- Keep `main.py` thin. Startup orchestration belongs in `editor/composition/launcher.py`.
- Keep config declarative. Registration and object creation belong in `editor/composition`.
- Keep editing behavior in `EditorCore`, not in renderers.
- Keep tokenizer implementations behind the `Tokenizer` interface.
- Keep renderer command sets aligned through `editor/presentation/toolbar.py`.
- Avoid duplicate module/package names such as both `writing.py` and `writing/`.

## Verification Checklist

Before handing off a structural change, run:

```sh
python -m unittest discover -s tests
python -m compileall -q editor tests main.py
```

For architecture changes, also scan imports to make sure inner layers do not depend on outer layers.
