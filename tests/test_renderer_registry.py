import unittest
from io import StringIO

from main import main
from editor.composition.launcher import run_editor
from editor.composition.registries import create_renderer_registry
from editor.application.registries.renderers import RendererRegistry


class RendererRegistryTests(unittest.TestCase):
	def test_main_injects_one_core_into_selected_renderer(self):
		created = []

		class FakeRenderer:
			def __init__(self, core):
				self.core = core

			def run(self):
				created.append(self.core)

		registry = RendererRegistry()
		registry.register("fake", lambda core, **_options: FakeRenderer(core))

		self.assertEqual(main(["--renderer", "fake"], renderers=registry), 0)
		self.assertEqual(len(created), 1)
		self.assertEqual(created[0].model.get_text(), "")

	def test_configured_registry_exposes_cli_and_tk_renderers(self):
		registry = create_renderer_registry()

		self.assertIn("cli", registry.names)
		self.assertIn("tk", registry.names)
		self.assertIn("tkinter", registry.names)

	def test_launcher_reports_renderer_startup_errors(self):
		registry = RendererRegistry()
		registry.register("broken", lambda core, **_options: BrokenRenderer())
		stderr = StringIO()

		self.assertEqual(run_editor(["--renderer", "broken"], renderers=registry, stderr=stderr), 1)
		self.assertIn("Unable to start broken renderer: nope", stderr.getvalue())


class BrokenRenderer:
	def run(self):
		raise RuntimeError("nope")


if __name__ == "__main__":
	unittest.main()
