import curses
import shutil
import subprocess
import sys

from editor.application.core import EditorCore
from editor.composition.appearance import create_editor_appearance
from editor.composition.registries import create_sub_renderer_registry
from editor.composition.registries import create_tokenizer_registry
from editor.domain.position import Position
from editor.presentation.toolbar import toolbar_summary


class TerminalRenderer:
	def __init__(self, path=None, core=None, sub_renderers=None, appearance=None):
		self.core = core or EditorCore(path, tokenizers=create_tokenizer_registry())
		self.sub_renderers = sub_renderers or create_sub_renderer_registry()
		self.appearance = appearance or create_editor_appearance()
		self.default_font_size = self.appearance.font_size
		self.default_foreground_color = self.appearance.foreground_color.for_renderer("cli")
		self.running = True
		self.screen = None
		self.top_line = 0
		self.left_column = 0
		self._color_pairs = {}
		self._inspection_message = ""
		self._display_spans = self.token_spans
		self._toolbar_text = toolbar_summary()

	def __getattr__(self, name):
		return getattr(self.core, name)

	def run(self):
		curses.wrapper(self._run)

	def _run(self, screen):
		self.screen = screen
		curses.raw()
		curses.noecho()
		screen.keypad(True)
		screen.timeout(-1)
		self._init_colors()
		while self.running:
			self._draw()
			key = self._read_key()
			self._handle_key(key)

	def _init_colors(self):
		if not curses.has_colors():
			return
		curses.start_color()
		try:
			curses.use_default_colors()
		except curses.error:
			pass
		foregrounds = {
			"black": curses.COLOR_BLACK,
			"red": curses.COLOR_RED,
			"green": curses.COLOR_GREEN,
			"yellow": curses.COLOR_YELLOW,
			"blue": curses.COLOR_BLUE,
			"magenta": curses.COLOR_MAGENTA,
			"cyan": curses.COLOR_CYAN,
			"white": curses.COLOR_WHITE,
		}
		for pair, (name, foreground) in enumerate(foregrounds.items(), start=1):
			try:
				curses.init_pair(pair, foreground, -1)
				self._color_pairs[name] = pair
			except curses.error:
				pass

	def _draw(self):
		screen = self.screen
		if screen is None:
			return
		screen.erase()
		height, width = screen.getmaxyx()
		if height < 4 or width < 12:
			self._safe_addstr(0, 0, "Terminal too small; resize to continue")
			screen.refresh()
			return

		gutter = max(4, len(str(self.model.line_count))) + 2
		text_width = max(1, width - gutter)
		view_height = height - 2
		self._keep_caret_visible(view_height, text_width)
		self._safe_addstr(0, 0, self._header(width), curses.A_BOLD)
		lines = [self.model.get_line_content(row) for row in range(self.model.line_count)]
		self._display_spans = self.sub_renderers.render_document(self.file_path, lines, self.token_spans)
		for screen_row in range(view_height):
			line_number = self.top_line + screen_row
			if line_number >= self.model.line_count:
				break
			self._draw_line(screen_row + 1, line_number, gutter, text_width)

		self._draw_carets(gutter, view_height, text_width)
		self._safe_addstr(height - 1, 0, self._footer(width), curses.A_REVERSE)
		try:
			curses.curs_set(1)
			position = self.model.position_at(self.selections[0].active)
			cursor_y = 1 + position.line - self.top_line
			cursor_x = gutter + self._visual_column(self.model.get_line_content(position.line), position.column) - self.left_column
			if 1 <= cursor_y < height - 1 and gutter <= cursor_x < width:
				screen.move(cursor_y, cursor_x)
		except curses.error:
			pass
		screen.refresh()

	def _header(self, width):
		name = self.file_path or "Untitled"
		marker = " *" if self.dirty else ""
		text = f" {name}{marker}  |  {self._toolbar_text} "
		return text[:width].ljust(width)

	def _toolbar_actions(self):
		return {
			"open": self._open_prompt,
			"save": self.save_file,
			"save_as": self.save_as,
			"undo": self.core.undo,
			"redo": self.core.redo,
			"cut": self._cut_to_clipboard,
			"copy": self._copy_to_clipboard,
			"paste": self._paste_from_clipboard,
			"bold": lambda: self.core.set_format("bold"),
			"italic": lambda: self.core.set_format("italic"),
			"font_decrease": lambda: self._adjust_font_size(-1),
			"font_increase": lambda: self._adjust_font_size(1),
			"inspect": self.inspect_token,
			"quit": self._close,
		}

	def _run_toolbar_action(self, action_id):
		self._toolbar_actions()[action_id]()

	def _footer(self, width):
		position = self.model.position_at(self.selections[0].active)
		selected = sum(selection.end - selection.start for selection in self.selections)
		message = self._inspection_message or self.message or f"Ln {position.line + 1}, Col {position.column + 1}  |  {self.model.line_count} lines"
		formatting = self.core.format_at(self.selections[0].active, include_previous=True)
		format_markers = "".join(marker for key, marker in (("bold", "B"), ("italic", "I")) if formatting.get(key))
		message += f"  |  {format_markers or 'Regular'} {formatting.get('font_size', self.default_font_size)}pt"
		if selected:
			message += f"  |  {selected} selected"
		if len(self.selections) > 1:
			message += f"  |  {len(self.selections)} carets"
		return f" {message} "[:width].ljust(width)

	def _draw_line(self, screen_row, line_number, gutter, text_width):
		line = self.model.get_line_content(line_number)
		line_start = self.model.offset_at(Position(line_number, 0))
		self._safe_addstr(screen_row, 0, f"{line_number + 1:>{gutter - 1}} ", curses.A_DIM)
		visual_column = 0
		for column, character in enumerate(line):
			display = "    " if character == "\t" else character
			span = self._color_at(line_number, column)
			attribute = self._color_attribute(span)
			formatting = self.core.format_at(line_start + column)
			if formatting.get("bold") or formatting.get("font_size", self.default_font_size) > self.default_font_size:
				attribute |= curses.A_BOLD
			if formatting.get("italic"):
				attribute |= getattr(curses, "A_ITALIC", curses.A_UNDERLINE)
			if formatting.get("font_size", self.default_font_size) < self.default_font_size:
				attribute |= curses.A_DIM
			if any(selection.start <= line_start + column < selection.end for selection in self.selections):
				attribute |= curses.A_REVERSE
			if visual_column + len(display) > self.left_column:
				visible = display[max(0, self.left_column - visual_column) :]
				x = gutter + max(0, visual_column - self.left_column)
				if x < gutter + text_width:
					self._safe_addstr(screen_row, x, visible[: gutter + text_width - x], attribute)
			visual_column += len(display)
		if line_number < self.model.line_count - 1:
			newline_offset = line_start + len(line)
			if any(selection.start <= newline_offset < selection.end for selection in self.selections):
				x = gutter + visual_column - self.left_column
				if gutter <= x < gutter + text_width:
					self._safe_addstr(screen_row, x, " ", curses.A_REVERSE)

	def _draw_carets(self, gutter, view_height, text_width):
		for selection in self.selections[1:]:
			position = self.model.position_at(selection.active)
			screen_y = position.line - self.top_line + 1
			line = self.model.get_line_content(position.line)
			screen_x = gutter + self._visual_column(line, position.column) - self.left_column
			if 1 <= screen_y <= view_height and gutter <= screen_x < gutter + text_width:
				self._safe_addstr(screen_y, screen_x, " ", curses.A_REVERSE)

	def _color_at(self, line_number, column):
		for start, end, color in self._display_spans[line_number]:
			if start <= column < end:
				return color
		return None

	def _color_attribute(self, style):
		color_name = self.core.color_for(style, "cli") or self.default_foreground_color
		pair = self._color_pairs.get(color_name)
		return curses.color_pair(pair) if pair and curses.has_colors() else curses.A_NORMAL

	def _safe_addstr(self, row, column, text, attribute=curses.A_NORMAL):
		if not text:
			return
		try:
			self.screen.addstr(row, column, text, attribute)
		except curses.error:
			pass

	def _keep_caret_visible(self, view_height, text_width):
		position = self.model.position_at(self.selections[0].active)
		if position.line < self.top_line:
			self.top_line = position.line
		elif position.line >= self.top_line + view_height:
			self.top_line = position.line - view_height + 1
		visual_column = self._visual_column(self.model.get_line_content(position.line), position.column)
		if visual_column < self.left_column:
			self.left_column = visual_column
		elif visual_column >= self.left_column + text_width:
			self.left_column = visual_column - text_width + 1

	@staticmethod
	def _visual_column(line, column):
		return len(line[:column].expandtabs(4))

	def _read_key(self):
		key = self.screen.get_wch()
		if key != "\x1b":
			return key
		self.screen.timeout(35)
		try:
			first = self.screen.get_wch()
			if first != "[":
				return ("ALT", first) if isinstance(first, str) else "ESC"
			sequence = ""
			while len(sequence) < 16:
				part = self.screen.get_wch()
				if not isinstance(part, str):
					break
				sequence += part
				if part.isalpha() or part == "~":
					break
			return self._decode_escape_sequence(sequence)
		except curses.error:
			return "ESC"
		finally:
			self.screen.timeout(-1)

	@staticmethod
	def _decode_escape_sequence(sequence):
		final = sequence[-1:] if sequence else ""
		key = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT", "H": "HOME", "F": "END"}.get(final)
		if key is None:
			return "UNKNOWN"
		modifier = 1
		if ";" in sequence:
			try:
				modifier = int(sequence.split(";")[-1][:-1])
			except ValueError:
				modifier = 1
		if modifier == 2:
			return ("SHIFT", key)
		if modifier in {3, 4, 7, 8}:
			return ("ALT", key)
		return key

	def _handle_key(self, key):
		self._inspection_message = ""
		if key in {"\x11", ("CTRL", "Q")}:
			self._run_toolbar_action("quit")
			return
		if key in {"\x13", ("CTRL", "S")}:
			self._run_toolbar_action("save")
		elif key in {"\x0f", ("CTRL", "O")}:
			self._run_toolbar_action("open")
		elif key in {"\x01", ("CTRL", "A")}:
			self.core.select_all()
		elif key in {"\x03", ("CTRL", "C")}:
			self._run_toolbar_action("copy")
		elif key in {"\x18", ("CTRL", "X")}:
			self._run_toolbar_action("cut")
		elif key in {"\x16", ("CTRL", "V")}:
			self._run_toolbar_action("paste")
		elif key in {"\x1a", ("CTRL", "Z")}:
			self._run_toolbar_action("undo")
		elif key in {"\x19", ("CTRL", "Y")}:
			self._run_toolbar_action("redo")
		elif key == curses.KEY_F1:
			self._run_toolbar_action("inspect")
		elif key == curses.KEY_F2:
			self._run_toolbar_action("bold")
		elif key == curses.KEY_F3:
			self._run_toolbar_action("italic")
		elif key == curses.KEY_F4:
			self._run_toolbar_action("font_increase")
		elif key == curses.KEY_F5:
			self._run_toolbar_action("font_decrease")
		elif key == curses.KEY_F6:
			self._run_toolbar_action("save_as")
		elif key in {("ALT", "UP"), ("ALT", "DOWN")}:
			self.core.add_vertical_caret(-1 if key[1] == "UP" else 1)
		elif key in {"LEFT", "RIGHT", "UP", "DOWN", "HOME", "END"}:
			self.core.move_carets(key, False)
		elif isinstance(key, tuple) and key[0] == "SHIFT" and key[1] in {"LEFT", "RIGHT", "UP", "DOWN", "HOME", "END"}:
			self.core.move_carets(key[1], True)
		elif key in {curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN, curses.KEY_HOME, curses.KEY_END}:
			mapping = {
				curses.KEY_LEFT: "LEFT",
				curses.KEY_RIGHT: "RIGHT",
				curses.KEY_UP: "UP",
				curses.KEY_DOWN: "DOWN",
				curses.KEY_HOME: "HOME",
				curses.KEY_END: "END",
			}
			self.core.move_carets(mapping[key], False)
		elif key in {curses.KEY_BACKSPACE, "\x08", "\x7f"}:
			self.core.delete("backward")
		elif key == curses.KEY_DC:
			self.core.delete("forward")
		elif key in {"\n", "\r", curses.KEY_ENTER}:
			self.core.replace_selections("\n")
		elif key == "\t":
			self.core.replace_selections("    ")
		elif isinstance(key, str) and len(key) == 1 and key.isprintable():
			self.core.replace_selections(key, group="typing")

	def _adjust_font_size(self, delta):
		current = self.core.format_at(self.selections[0].active, include_previous=True).get("font_size", self.default_font_size)
		self.core.set_format("font_size", min(24, max(8, current + delta)))

	def inspect_token(self):
		info = self.core.token_info_at(self.selections[0].active, include_previous=True)
		self._inspection_message = info.description if info else "No token at caret"

	def _copy_to_clipboard(self):
		if any(not selection.is_empty for selection in self.selections):
			self._clipboard_write(self.core.copy())

	def _cut_to_clipboard(self):
		if any(not selection.is_empty for selection in self.selections):
			self._clipboard_write(self.core.cut())

	def _paste_from_clipboard(self):
		self.core.paste(self._clipboard_read())

	def _clipboard_write(self, text):
		if sys.platform == "darwin" and shutil.which("pbcopy"):
			command = ["pbcopy"]
		elif shutil.which("wl-copy"):
			command = ["wl-copy"]
		elif shutil.which("xclip"):
			command = ["xclip", "-selection", "clipboard"]
		else:
			return
		try:
			subprocess.run(command, input=text, text=True, check=True, timeout=1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		except (OSError, subprocess.SubprocessError):
			pass

	def _clipboard_read(self):
		if sys.platform == "darwin" and shutil.which("pbpaste"):
			command = ["pbpaste"]
		elif shutil.which("wl-paste"):
			command = ["wl-paste", "--no-newline"]
		elif shutil.which("xclip"):
			command = ["xclip", "-selection", "clipboard", "-o"]
		else:
			return self.clipboard
		try:
			result = subprocess.run(command, text=True, check=True, timeout=1, capture_output=True)
			return result.stdout
		except (OSError, subprocess.SubprocessError):
			return self.clipboard

	def _open_prompt(self):
		if not self._confirm_discard():
			return
		path = self._prompt("Open file: ")
		if path:
			self.core.open_path(path)

	def save_file(self):
		path = self.file_path or self._prompt("Save as: ")
		return self.core.save_file(path)

	def save_as(self):
		path = self._prompt("Save as: ")
		return self.core.save_file(path) if path else False

	def _confirm_discard(self):
		if not self.dirty:
			return True
		answer = self._prompt("Save changes? [y/N/c] ").strip().lower()
		if answer == "c":
			return False
		if answer == "y":
			return self.save_file()
		return True

	def _prompt(self, prompt):
		if self.screen is None:
			return ""
		height, width = self.screen.getmaxyx()
		try:
			curses.echo()
			curses.curs_set(1)
			self.screen.move(height - 1, 0)
			self.screen.clrtoeol()
			self.screen.addstr(height - 1, 0, prompt[: max(0, width - 1)])
			self.screen.refresh()
			value = self.screen.getstr(height - 1, min(len(prompt), width - 1), max(1, width - len(prompt) - 1))
			return value.decode("utf-8", errors="replace")
		except curses.error:
			return ""
		finally:
			curses.noecho()

	def _close(self):
		if self._confirm_discard():
			self.running = False


TerminalEditor = TerminalRenderer


def create_terminal_renderer(core, **_options):
	return TerminalRenderer(core=core)


def main(argv=None):
	args = sys.argv[1:] if argv is None else argv
	if len(args) > 1:
		print("Usage: python main.py [file]", file=sys.stderr)
		return 2
	try:
		TerminalEditor(args[0] if args else None).run()
	except curses.error as error:
		print(f"Unable to start terminal editor: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
