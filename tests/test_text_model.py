import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from editor.domain.color import Color
from editor.application.core import EditorCore
from editor.domain.position import Position
from editor.domain.selection import Selection
from editor.domain.text_model import TextModel
from editor.application.tokenization.base import TokenStyle, Tokenizer
from editor.application.tokenization.plugin import TokenizerPlugin
from editor.composition.registries import create_tokenizer_registry
from editor.application.registries.tokenizers import TokenizerRegistry
from editor.application.history import UndoHistory


class TextModelTests(unittest.TestCase):
	def test_line_access_and_position_conversions(self):
		model = TextModel("hello\nworld")

		self.assertEqual(model.line_count, 2)
		self.assertEqual(model.get_line_content(1), "world")
		self.assertEqual(model.offset_at(Position(1, 2)), 8)
		self.assertEqual(model.position_at(8), Position(1, 2))

	def test_insert_delete_and_replace(self):
		model = TextModel("hello\nworld")

		model.insert(5, " beautiful")
		self.assertEqual(model.get_text(), "hello beautiful\nworld")
		model.delete(5, 15)
		self.assertEqual(model.get_text(), "hello\nworld")
		model.replace(5, 6, " ")
		self.assertEqual(model.get_text(), "hello world")

	def test_position_conversion_clamps_to_document(self):
		model = TextModel("abc\ndef")

		self.assertEqual(model.offset_at(Position(8, 8)), 7)
		self.assertEqual(model.position_at(100), Position(1, 3))

	def test_trailing_newline_creates_empty_line(self):
		model = TextModel("a\n")

		self.assertEqual(model.line_count, 2)
		self.assertEqual(model.get_line_content(1), "")
		self.assertEqual(model.position_at(2), Position(1, 0))

	def test_selection_normalizes_reversed_endpoints(self):
		selection = Selection(8, 3)

		self.assertEqual((selection.start, selection.end), (3, 8))
		self.assertFalse(selection.is_empty)

	def test_history_groups_typing_and_restores_selections(self):
		history = UndoHistory()
		original = [Selection(1, 1), Selection(4, 4)]
		history.record("a b", original, "typing")
		history.record("xa xb", [Selection(2, 2), Selection(5, 5)], "typing")

		self.assertEqual(history.undo("xxa xxb", []), ("a b", tuple(original)))
		self.assertEqual(history.redo("a b", original), ("xxa xxb", ()))

	def test_python_tokenizer_colors_keywords_and_numbers(self):
		spans = create_tokenizer_registry().tokenize("sample.py", "def run():\n    return 42\n")

		self.assertTrue(any(style == "keyword" for _, _, style in spans[0]))
		self.assertTrue(any(style == "number" for _, _, style in spans[1]))

	def test_tokenizer_registry_selects_language_plugin_by_extension(self):
		registry = TokenizerRegistry()
		registry.register("demo", lambda source: [[(0, len(source), "demo-style")]])

		self.assertEqual(registry.tokenize("example.demo", "abc"), [[(0, 3, "demo-style")]])
		self.assertEqual(registry.tokenize("example.txt", "abc"), [[]])

	def test_tokenizer_plugin_owns_extensions_and_renderer_colors(self):
		plugin = TokenizerPlugin(
			[".demo", ".sample"],
			lambda source: [[(0, len(source), "accent")]],
			{"accent": Color(tk="#123456", terminal="cyan", export="#123456")},
			name="demo",
		)
		registry = TokenizerRegistry()
		registry.register(plugin)
		core = EditorCore(tokenizers=registry)
		core.file_path = "document.demo"
		core.model = TextModel("abc")

		self.assertIs(core.tokenizer, plugin)
		self.assertEqual(plugin.extensions, (".demo", ".sample"))
		self.assertEqual(core.token_spans, [[(0, 3, "accent")]])
		self.assertEqual(core.color_for("accent", "tk"), "#123456")
		self.assertEqual(core.color_for("accent", "cli"), "cyan")
		self.assertEqual(core.color_for("accent", "export"), "#123456")

	def test_class_tokenizer_defines_token_names_and_colors(self):
		class DemoTokenizer(Tokenizer):
			name = "Demo"
			extensions = ("demo",)
			styles = (
				TokenStyle("function", Color.RED),
				TokenStyle("variable", Color.BLUE),
			)

			def tokenize(self, source):
				return [[(0, 2, "function"), (3, len(source), "variable")]]

		registry = TokenizerRegistry()
		plugin = registry.register(DemoTokenizer)
		core = EditorCore(tokenizers=registry)
		core.file_path = "sample.demo"
		core.model = TextModel("fn value")

		self.assertIsInstance(plugin, DemoTokenizer)
		self.assertEqual(core.token_spans, [[(0, 2, "function"), (3, 8, "variable")]])
		self.assertEqual(core.color_for("function", "cli"), "red")
		self.assertEqual(core.color_for("variable", "tk"), "#286f9c")

	def test_tokenizer_without_declared_styles_has_no_palette(self):
		class BareTokenizer(Tokenizer):
			extensions = ("bare",)

			def tokenize(self, source):
				return [[(0, len(source), "keyword")]]

		plugin = TokenizerRegistry().register(BareTokenizer)

		self.assertEqual(plugin.colors, {})

	def test_token_info_uses_writing_roles_and_code_styles(self):
		core = EditorCore(tokenizers=create_tokenizer_registry())
		core.file_path = "story.txt"
		core.model = TextModel("The student reads.")
		student_offset = core.model.get_text().index("student") + 2
		writing_info = core.token_info_at(student_offset)

		self.assertEqual(writing_info.text, "student")
		self.assertEqual(writing_info.kind, "noun")
		self.assertIn("subject", writing_info.roles)
		self.assertEqual(writing_info.dependency, "nsubj")
		self.assertIn("dep: nsubj", writing_info.description)

		core.file_path = "sample.py"
		core.model = TextModel("def run():\n    return 1")
		code_info = core.token_info_at(1)
		self.assertEqual(code_info.text, "def")
		self.assertEqual(code_info.kind, "keyword")

	def test_save_as_new_extension_refreshes_tokenizer(self):
		registry = TokenizerRegistry()
		registry.register("demo", lambda source: [[(0, len(source), "demo-style")]])
		core = EditorCore(tokenizers=registry)
		core.model = TextModel("abc")
		self.assertEqual(core.token_spans, [[]])

		with TemporaryDirectory() as directory:
			path = Path(directory) / "sample.demo"
			self.assertTrue(core.save_file(path))
			self.assertEqual(core.token_spans, [[(0, 3, "demo-style")]])


if __name__ == "__main__":
	unittest.main()
