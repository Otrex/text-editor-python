import argparse
import curses
import sys

from editor.application.core import EditorCore
from editor.composition.registries import create_renderer_registry
from editor.composition.registries import create_tokenizer_registry


class EditorLauncher:
	def __init__(self, renderers=None, stderr=None):
		self.renderers = renderers or create_renderer_registry()
		self.stderr = stderr or sys.stderr

	def run(self, argv=None):
		args = self._parse_args(argv)
		core = self._create_core(args.file)
		return self._run_renderer(args.renderer, core)

	def _parse_args(self, argv):
		parser = argparse.ArgumentParser(description="A small text editor with switchable renderers")
		parser.add_argument("--renderer", choices=self.renderers.names, default="cli")
		parser.add_argument("file", nargs="?")
		return parser.parse_args(argv)

	def _create_core(self, path):
		return EditorCore(path, tokenizers=create_tokenizer_registry())

	def _run_renderer(self, name, core):
		try:
			self.renderers.create(name, core).run()
		except (curses.error, RuntimeError) as error:
			print(f"Unable to start {name} renderer: {error}", file=self.stderr)
			return 1
		return 0


def run_editor(argv=None, renderers=None, stderr=None):
	return EditorLauncher(renderers=renderers, stderr=stderr).run(argv)
