import unittest
import curses
from types import SimpleNamespace

from editor.application.core import EditorCore
from editor.composition.appearance import create_editor_appearance
from editor.composition.registries import create_tokenizer_registry
from editor.presentation.renderers.cli import TerminalRenderer
from editor.presentation.toolbar import command_items
from editor.presentation.toolbar import toolbar_summary
from editor.domain.selection import Selection
from editor.domain.text_model import TextModel


class EditorOperationTests(unittest.TestCase):
	def setUp(self):
		self.editor = EditorCore()
		self.editor.model = TextModel("one two")
		self.editor.selections = [Selection(0, 3)]

	def test_typing_replaces_selected_text_and_undo_restores_it(self):
		self.editor.replace_selections("ONE")

		self.assertEqual(self.editor.model.get_text(), "ONE two")
		self.editor.undo()
		self.assertEqual(self.editor.model.get_text(), "one two")
		self.assertEqual(self.editor.selections, [Selection(0, 3)])
		self.editor.redo()
		self.assertEqual(self.editor.model.get_text(), "ONE two")

	def test_multiple_carets_edit_in_one_operation(self):
		self.editor.selections = [Selection(0, 0), Selection(4, 4)]

		self.editor.replace_selections("X", group="typing")

		self.assertEqual(self.editor.model.get_text(), "Xone Xtwo")
		self.assertEqual(self.editor.selections, [Selection(1, 1), Selection(6, 6)])
		self.editor.undo()
		self.assertEqual(self.editor.model.get_text(), "one two")

	def test_cut_without_selection_does_not_delete(self):
		self.editor.selections = [Selection(2, 2)]
		self.editor._copy = lambda: "break"

		self.editor.cut()

		self.assertEqual(self.editor.model.get_text(), "one two")

	def test_open_and_save_file_update_document_state(self):
		from tempfile import TemporaryDirectory
		from pathlib import Path

		with TemporaryDirectory() as directory:
			path = Path(directory) / "sample.txt"
			path.write_text("first\nsecond", encoding="utf-8")
			self.assertTrue(self.editor.open_path(path))
			self.assertEqual(self.editor.model.get_text(), "first\nsecond")
			self.assertFalse(self.editor.dirty)
			self.editor.replace_selections("updated")
			self.assertTrue(self.editor.dirty)
			self.assertTrue(self.editor.save_file())
			self.assertEqual(path.read_text(encoding="utf-8"), "updatedfirst\nsecond")
			self.assertFalse(self.editor.dirty)

	def test_key_dispatch_edits_model_without_terminal(self):
		self.editor.selections = [Selection(0, 0)]
		renderer = TerminalRenderer(core=self.editor)
		renderer._handle_key("!")

		self.assertEqual(self.editor.model.get_text(), "!one two")

	def test_cli_f1_shows_token_details_at_caret(self):
		self.editor.tokenizers = create_tokenizer_registry()
		self.editor.file_path = "story.txt"
		self.editor.model = TextModel("The student reads.")
		self.editor.selections = [Selection(8, 8)]
		renderer = TerminalRenderer(core=self.editor)

		renderer._handle_key(curses.KEY_F1)

		self.assertIn("student | noun | subject", renderer._inspection_message)

	def test_tk_hover_updates_status_and_leave_clears_it(self):
		from editor.presentation.renderers.tk import TkRenderer

		renderer = TkRenderer.__new__(TkRenderer)
		renderer.core = EditorCore(tokenizers=create_tokenizer_registry())
		renderer.core.file_path = "story.txt"
		renderer.core.model = TextModel("The student reads.")
		renderer.gutter_width = 56
		renderer.padding = 12
		renderer.line_height = 20
		renderer.font = SimpleNamespace(measure=lambda text: len(text) * 8)
		renderer._font_for = lambda _formatting: renderer.font
		renderer.canvas = SimpleNamespace(canvasy=lambda value: value, canvasx=lambda value: value)
		renderer._hover_info = None
		renderer.draw = lambda: None

		renderer._on_mouse_motion(SimpleNamespace(x=56 + 4 * 8 + 4, y=12 + 5))
		self.assertIn("student | noun | subject", renderer._hover_info.description)
		renderer._on_mouse_leave(None)
		self.assertIsNone(renderer._hover_info)

	def test_selection_formatting_and_undo_redo(self):
		self.editor.model = TextModel("bold text")
		self.editor.formatting = [{} for _character in "bold text"]
		self.editor.selections = [Selection(0, 4)]

		self.assertTrue(self.editor.set_format("bold"))
		self.assertTrue(all(self.editor.format_at(index).get("bold") for index in range(4)))
		self.editor.undo()
		self.assertFalse(any(self.editor.format_at(index).get("bold") for index in range(4)))
		self.editor.redo()
		self.assertTrue(all(self.editor.format_at(index).get("bold") for index in range(4)))

		self.editor.set_format("font_size", 20)
		self.assertEqual(self.editor.format_at(1)["font_size"], 20)

	def test_terminal_format_shortcuts_apply_to_selection(self):
		self.editor.formatting = [{} for _character in self.editor.model.get_text()]
		renderer = TerminalRenderer(core=self.editor)

		renderer._handle_key(curses.KEY_F2)

		self.assertTrue(all(self.editor.format_at(index).get("bold") for index in range(3)))

	def test_toolbar_definition_drives_terminal_actions_and_header(self):
		self.editor.formatting = [{} for _character in self.editor.model.get_text()]
		renderer = TerminalRenderer(core=self.editor)

		self.assertEqual(set(renderer._toolbar_actions()), {item.id for item in command_items()})
		self.assertIn(toolbar_summary(), renderer._header(500))
		renderer._run_toolbar_action("font_increase")

		self.assertTrue(all(self.editor.format_at(index).get("font_size") == 14 for index in range(3)))

	def test_terminal_save_as_always_prompts_for_a_path(self):
		from tempfile import TemporaryDirectory
		from pathlib import Path

		with TemporaryDirectory() as directory:
			original = Path(directory) / "original.txt"
			target = Path(directory) / "copy.txt"
			self.editor.file_path = str(original)
			renderer = TerminalRenderer(core=self.editor)
			renderer._prompt = lambda _prompt: str(target)

			self.assertTrue(renderer.save_as())
			self.assertEqual(target.read_text(encoding="utf-8"), "one two")
			self.assertEqual(self.editor.file_path, str(target))

	def test_appearance_defaults_are_loaded_from_config(self):
		appearance = create_editor_appearance()
		renderer = TerminalRenderer(core=self.editor, appearance=appearance)

		self.assertEqual(appearance.font_family, "Menlo")
		self.assertEqual(appearance.font_size, 13)
		self.assertEqual(appearance.foreground_color.for_renderer("tk"), "#20231f")
		self.assertEqual(renderer.default_font_size, 13)
		self.assertEqual(renderer.default_foreground_color, "black")

	def test_tk_format_shortcut_applies_to_selection(self):
		from editor.presentation.renderers.tk import TkRenderer

		self.editor.formatting = [{} for _character in self.editor.model.get_text()]
		renderer = TkRenderer.__new__(TkRenderer)
		renderer.core = self.editor
		renderer._hover_info = None
		renderer.draw = lambda: None
		event = SimpleNamespace(state=0x4, keysym="b", char="\x02")

		renderer._on_key(event)

		self.assertTrue(all(self.editor.format_at(index).get("bold") for index in range(3)))

	def test_tk_font_size_control_formats_selection(self):
		from editor.presentation.renderers.tk import TkRenderer

		renderer = TkRenderer.__new__(TkRenderer)
		renderer.core = self.editor
		renderer.base_font_size = 13
		renderer.font_size = SimpleNamespace(get=lambda: "18", set=lambda _value: None)

		renderer._apply_font_size()

		self.assertTrue(all(self.editor.format_at(index).get("font_size") == 18 for index in range(3)))
		self.assertEqual(renderer.base_font_size, 13)

	def test_tk_font_size_control_updates_base_size_without_selection(self):
		from editor.presentation.renderers.tk import TkRenderer

		self.editor.selections = [Selection(0, 0)]
		renderer = TkRenderer.__new__(TkRenderer)
		renderer.core = self.editor
		renderer.base_font_size = 13
		renderer.font_size = SimpleNamespace(get=lambda: "18", set=lambda _value: None)
		renderer.font = SimpleNamespace(configure=lambda **_kwargs: None, metrics=lambda _key: 22)
		renderer.draw = lambda: None

		renderer._apply_font_size()

		self.assertEqual(renderer.base_font_size, 18)
		self.assertEqual(renderer.line_height, 36)
		self.assertFalse(any(self.editor.format_at(index).get("font_size") for index in range(3)))

	def test_tk_save_as_uses_chosen_path_even_when_file_already_has_path(self):
		from tempfile import TemporaryDirectory
		from pathlib import Path
		from unittest.mock import patch

		from editor.presentation.renderers.tk import TkRenderer

		with TemporaryDirectory() as directory:
			original = Path(directory) / "original.txt"
			target = Path(directory) / "copy.txt"
			self.editor.file_path = str(original)
			renderer = TkRenderer.__new__(TkRenderer)
			renderer.core = self.editor
			renderer.root = None

			with patch("editor.presentation.renderers.tk.filedialog.asksaveasfilename", return_value=str(target)):
				self.assertTrue(renderer.save_as())

			self.assertEqual(target.read_text(encoding="utf-8"), "one two")
			self.assertEqual(self.editor.file_path, str(target))


if __name__ == "__main__":
	unittest.main()
