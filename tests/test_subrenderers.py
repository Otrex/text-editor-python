import unittest

from editor.infrastructure.subrenderers.markdown import MarkdownSubRenderer
from editor.composition.registries import create_sub_renderer_registry
from editor.application.registries.subrenderers import SubRendererRegistry


class SubRendererTests(unittest.TestCase):
	def test_markdown_subrenderer_overlays_syntax_and_keeps_base_spans(self):
		lines = ["# student", "- item with **bold** and `code`", "[label](https://example.test)", "```python", "print(1)", "```", "plain"]
		base = [[(2, 9, "noun")], [], [], [], [], [], [(0, 5, "verb")]]
		spans = MarkdownSubRenderer().render_document(lines, base)

		self.assertEqual(spans[0], [(0, 9, "markdown_heading")])
		self.assertIn((0, 1, "markdown_list"), spans[1])
		self.assertTrue(any(style == "markdown_bold" for _, _, style in spans[1]))
		self.assertTrue(any(style == "markdown_inline_code" for _, _, style in spans[1]))
		self.assertTrue(any(style == "markdown_link" for _, _, style in spans[2]))
		self.assertEqual(spans[3], [(0, 9, "markdown_fence")])
		self.assertEqual(spans[4], [(0, 8, "markdown_code")])
		self.assertEqual(spans[5], [(0, 3, "markdown_fence")])
		self.assertEqual(spans[6], base[6])

	def test_subrenderer_registry_selects_by_extension_and_leaves_other_files_alone(self):
		registry = create_sub_renderer_registry()
		lines = ["# Heading"]
		base = [[]]

		self.assertEqual(registry.render_document("note.md", lines, base)[0][0][2], "markdown_heading")
		self.assertIs(registry.render_document("note.txt", lines, base), base)

	def test_registry_invalidates_composition_after_registration(self):
		registry = SubRendererRegistry()
		lines = ["# Heading"]
		base = [[]]
		self.assertIs(registry.render_document("note.md", lines, base), base)

		registry.register(MarkdownSubRenderer())

		self.assertEqual(registry.render_document("note.md", lines, base)[0][0][2], "markdown_heading")

	def test_markdown_subrenderer_returns_preview_lines(self):
		view = MarkdownSubRenderer().render_view(
			["# Heading", "- item with **bold** and `code`", "[label](https://example.test)"],
			[[], [], []],
		)

		self.assertEqual(view.lines, ["Heading", "* item with bold and code", "label"])
		self.assertEqual(view.spans[0], [(0, 7, "markdown_heading")])
		self.assertEqual(view.spans[1], [(0, 25, "markdown_list")])


if __name__ == "__main__":
	unittest.main()
