import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.font import Font

from editor.application.core import EditorCore
from editor.composition.appearance import create_editor_appearance
from editor.composition.registries import create_sub_renderer_registry
from editor.composition.registries import create_tokenizer_registry
from editor.domain.position import Position
from editor.domain.selection import Selection
from editor.presentation.toolbar import TOOLBAR_ITEMS
from editor.presentation.toolbar import ToolbarSeparator


class TkRenderer:
	def __init__(self, root, path=None, core=None, sub_renderers=None, appearance=None):
		self.root = root
		self.core = core or EditorCore(path, tokenizers=create_tokenizer_registry())
		self.sub_renderers = sub_renderers or create_sub_renderer_registry()
		self.appearance = appearance or create_editor_appearance()
		self.core.on_change = self.draw
		self.drag_anchor = None
		self._hover_info = None
		self.gutter_width = 56
		self.padding = 12
		self.base_font_size = self.appearance.font_size
		self.foreground_color = self.appearance.foreground_color.for_renderer("tk")
		self.font = Font(family=self.appearance.font_family, size=self.base_font_size)
		self.line_height = 36
		self._font_cache = {}
		self._toolbar_buttons = {}
		self.root.title("Canvas Editor")
		self.root.geometry("900x600")
		self.root.minsize(500, 300)
		self._build_ui()
		self._bind_events()
		self.draw()

	def _build_ui(self):
		toolbar = ttk.Frame(self.root, padding=(8, 6))
		toolbar.pack(side="top", fill="x")
		self._build_toolbar(toolbar)

		editor = ttk.Frame(self.root)
		editor.pack(fill="both", expand=True)
		self.canvas = tk.Canvas(editor, background="#fbfbf8", highlightthickness=0, takefocus=True)
		vertical = ttk.Scrollbar(editor, orient="vertical", command=self._scroll_y)
		horizontal = ttk.Scrollbar(editor, orient="horizontal", command=self.canvas.xview)
		self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
		self.canvas.grid(row=0, column=0, sticky="nsew")
		vertical.grid(row=0, column=1, sticky="ns")
		horizontal.grid(row=1, column=0, sticky="ew")
		editor.rowconfigure(0, weight=1)
		editor.columnconfigure(0, weight=1)
		self.status = ttk.Label(self.root, anchor="w", padding=(10, 5))
		self.status.pack(side="bottom", fill="x")

		menu = tk.Menu(self.root)
		file_menu = tk.Menu(menu, tearoff=False)
		file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
		file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
		file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_as)
		file_menu.add_separator()
		file_menu.add_command(label="Quit", command=self.close)
		menu.add_cascade(label="File", menu=file_menu)
		self.root.configure(menu=menu)
		style = ttk.Style(self.root)
		style.configure("Bold.TButton", font=("TkDefaultFont", 9, "bold"))
		style.configure("Italic.TButton", font=("TkDefaultFont", 9, "italic"))

	def _build_toolbar(self, toolbar):
		actions = self._toolbar_actions()
		previous_was_separator = True
		for item in TOOLBAR_ITEMS:
			if isinstance(item, ToolbarSeparator):
				if not previous_was_separator:
					ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
					previous_was_separator = True
				continue
			if item.id == "font_decrease":
				ttk.Button(toolbar, text=item.short_label, width=3, command=actions[item.id]).pack(side="left", padx=(0, 2))
				self._build_font_size_control(toolbar)
			elif item.id == "font_increase":
				ttk.Button(toolbar, text=item.short_label, width=3, command=actions[item.id]).pack(side="left", padx=(2, 0))
			elif item.id == "quit":
				previous_was_separator = False
				continue
			else:
				style = {"bold": "Bold.TButton", "italic": "Italic.TButton"}.get(item.id)
				options = {"text": item.short_label, "command": actions[item.id]}
				if style:
					options["style"] = style
				if item.id in {"bold", "italic"}:
					options["width"] = 3
				button = ttk.Button(toolbar, **options)
				button.pack(side="left", padx=(0, 2))
				self._toolbar_buttons[item.id] = button
			previous_was_separator = False

	def _build_font_size_control(self, toolbar):
		self.font_size = tk.IntVar(value=self.base_font_size)
		font_size_control = ttk.Spinbox(toolbar, from_=8, to=24, width=3, textvariable=self.font_size, command=self._apply_font_size)
		font_size_control.pack(side="left", padx=(8, 0))
		font_size_control.bind("<Return>", lambda _event: self._apply_font_size())
		font_size_control.bind("<FocusOut>", lambda _event: self._apply_font_size())

	def _toolbar_actions(self):
		return {
			"open": self.open_file,
			"save": self.save_file,
			"save_as": self.save_as,
			"undo": self.core.undo,
			"redo": self.core.redo,
			"cut": self.cut,
			"copy": self.copy,
			"paste": self.paste,
			"bold": lambda: self.core.set_format("bold"),
			"italic": lambda: self.core.set_format("italic"),
			"font_decrease": lambda: self._adjust_font_size(-1),
			"font_increase": lambda: self._adjust_font_size(1),
			"inspect": self.inspect_token,
			"quit": self.close,
		}

	def _bind_events(self):
		self.canvas.bind("<KeyPress>", self._on_key)
		self.canvas.bind("<Button-1>", self._on_click)
		self.canvas.bind("<B1-Motion>", self._on_drag)
		self.canvas.bind("<Motion>", self._on_mouse_motion)
		self.canvas.bind("<Leave>", self._on_mouse_leave)
		self.canvas.bind("<Configure>", lambda _event: self.draw())
		self.canvas.bind("<MouseWheel>", self._on_mousewheel)
		self.canvas.bind("<Button-4>", lambda _event: self._scroll_y("scroll", -1, "units"))
		self.canvas.bind("<Button-5>", lambda _event: self._scroll_y("scroll", 1, "units"))
		self.root.bind("<Control-o>", lambda _event: self.open_file())
		self.root.bind("<Control-s>", lambda _event: self.save_file())
		self.root.bind("<F6>", lambda _event: self.save_as())
		self.root.protocol("WM_DELETE_WINDOW", self.close)
		self.canvas.focus_set()

	def draw(self):
		self.canvas.delete("all")
		lines = [self.core.model.get_line_content(row) for row in range(self.core.model.line_count)]
		longest = max((self._measure_formatted_line(row, line) for row, line in enumerate(lines)), default=0)
		width = max(self.canvas.winfo_width(), self.gutter_width + longest + self.padding * 2)
		height = max(self.canvas.winfo_height(), self.core.model.line_count * self.line_height + self.padding * 2)
		self.canvas.configure(scrollregion=(0, 0, width, height))
		first = max(0, int((self.canvas.canvasy(0) - self.padding) // self.line_height))
		last = min(self.core.model.line_count, int((self.canvas.canvasy(self.canvas.winfo_height()) - self.padding) // self.line_height) + 2)
		spans = self.sub_renderers.render_document(self.core.file_path, lines, self.core.token_spans)
		for row in range(first, last):
			line = self.core.model.get_line_content(row)
			y = self.padding + row * self.line_height
			line_start = self.core.model.offset_at(Position(row, 0))
			for selection in self.core.selections:
				start = max(selection.start, line_start)
				end = min(selection.end, line_start + len(line))
				if end > start:
					left = self.gutter_width + self._measure_formatted_line(row, line, 0, start - line_start)
					right = self.gutter_width + self._measure_formatted_line(row, line, 0, end - line_start)
					self.canvas.create_rectangle(left, y, right, y + self.line_height, fill="#c8e2dc", outline="")
			self.canvas.create_text(self.gutter_width - 12, y, text=str(row + 1), anchor="ne", font=self.font, fill="#92958e")
			self._draw_line(row, line, y, spans[row])

		if self.canvas.focus_get() == self.canvas:
			for selection in self.core.selections:
				position = self.core.model.position_at(selection.active)
				if first <= position.line < last:
					line = self.core.model.get_line_content(position.line)
					x = self.gutter_width + self._measure_formatted_line(position.line, line, 0, position.column)
					y = self.padding + position.line * self.line_height
					font = self._font_for(self.core.format_at(selection.active, include_previous=True))
					caret_height = min(self.line_height - 2, font.metrics("linespace") + 2)
					caret_top = y + 1
					self.canvas.create_line(x, caret_top, x, caret_top + caret_height, fill="#197a72", width=2)

		position = self.core.model.position_at(self.core.selections[0].active)
		selected = sum(selection.end - selection.start for selection in self.core.selections)
		message = self._hover_info.description if self._hover_info else self.core.message
		message = message or f"Ln {position.line + 1}, Col {position.column + 1}    |    {self.core.model.line_count} lines"
		if selected:
			message += f"    |    {selected} selected"
		if len(self.core.selections) > 1:
			message += f"    |    {len(self.core.selections)} carets"
		self.status.configure(text=message)
		name = self.core.file_path or "Untitled"
		self.root.title(f"{'*' if self.core.dirty else ''}{name} - Canvas Editor")

	def _draw_line(self, row, line, y, spans):
		line_start = self.core.model.offset_at(Position(row, 0))
		styles = [None] * len(line)
		for start, end, style in spans:
			for column in range(max(0, start), min(len(line), end)):
				styles[column] = style
		if not line:
			return
		start = 0
		x = self.gutter_width
		while start < len(line):
			formatting = self.core.format_at(line_start + start)
			style = styles[start]
			key = (style, tuple(sorted(formatting.items())))
			end = start + 1
			while end < len(line):
				next_formatting = self.core.format_at(line_start + end)
				if (styles[end], tuple(sorted(next_formatting.items()))) != key:
					break
				end += 1
			color = self.core.color_for(style, "tk") or self.foreground_color
			font = self._font_for(formatting)
			text = line[start:end]
			self.canvas.create_text(x, y, text=text, anchor="nw", font=font, fill=color)
			x += font.measure(text)
			start = end

	def _font_for(self, formatting):
		key = (bool(formatting.get("bold")), bool(formatting.get("italic")), int(formatting.get("font_size", self.base_font_size)))
		if key not in self._font_cache:
			self._font_cache[key] = Font(
				family=self.font.actual("family"),
				size=key[2],
				weight="bold" if key[0] else "normal",
				slant="italic" if key[1] else "roman",
			)
		return self._font_cache[key]

	def _measure_formatted_line(self, row, line, start=0, end=None):
		line_start = self.core.model.offset_at(Position(row, 0))
		end = len(line) if end is None else min(end, len(line))
		width = 0
		for column in range(start, end):
			character = line[column]
			width += self._font_for(self.core.format_at(line_start + column)).measure(character)
		return width

	def _apply_font_size(self):
		try:
			size = min(24, max(8, int(self.font_size.get())))
		except (tk.TclError, ValueError):
			return
		self.font_size.set(size)
		if not self.core.set_format("font_size", size):
			self._set_base_font_size(size)

	def _adjust_font_size(self, delta):
		current = self.core.format_at(self.core.selections[0].active, include_previous=True).get("font_size", self.base_font_size)
		size = min(24, max(8, current + delta))
		self.font_size.set(size)
		if not self.core.set_format("font_size", size):
			self._set_base_font_size(size)

	def _set_base_font_size(self, size):
		self.base_font_size = size
		self.font.configure(size=size)
		self.line_height = max(20, self.font.metrics("linespace") + 14)
		self.draw()

	def _offset_at_xy(self, event):
		y = self.canvas.canvasy(event.y) - self.padding
		row = max(0, min(self.core.model.line_count - 1, int(y // self.line_height)))
		line = self.core.model.get_line_content(row)
		x = self.canvas.canvasx(event.x) - self.gutter_width
		column = min(range(len(line) + 1), key=lambda index: abs(self._measure_formatted_line(row, line, 0, index) - x))
		return self.core.model.offset_at(Position(row, column))

	def _token_offset_under_xy(self, event):
		y = self.canvas.canvasy(event.y) - self.padding
		row = int(y // self.line_height)
		if not 0 <= row < self.core.model.line_count:
			return None
		line = self.core.model.get_line_content(row)
		x = self.canvas.canvasx(event.x) - self.gutter_width
		if x < 0:
			return None
		for column, character in enumerate(line):
			left = self._measure_formatted_line(row, line, 0, column)
			right = self._measure_formatted_line(row, line, 0, column + 1)
			if left <= x < right and not character.isspace():
				return self.core.model.offset_at(Position(row, column))
		return None

	def _on_mouse_motion(self, event):
		offset = self._token_offset_under_xy(event)
		info = self.core.token_info_at(offset) if offset is not None else None
		new_hover = (info.start, info.end, info.description) if info else None
		old_hover = (
			(self._hover_info.start, self._hover_info.end, self._hover_info.description)
			if self._hover_info
			else None
		)
		if new_hover != old_hover:
			self._hover_info = info
			self.draw()
		return "break"

	def _on_mouse_leave(self, _event):
		if self._hover_info is not None:
			self._hover_info = None
			self.draw()

		return None

	def _on_click(self, event):
		self.canvas.focus_set()
		offset = self._offset_at_xy(event)
		if event.state & 0x4:
			self.core.selections.append(Selection(offset, offset))
			self.core.history.break_group()
		elif event.state & 0x1:
			self.core.selections[0] = Selection(self.core.selections[0].anchor, offset)
			self.drag_anchor = self.core.selections[0].anchor
		else:
			self.core.selections = [Selection(offset, offset)]
			self.drag_anchor = offset
			self.core.history.break_group()
		self.draw()
		return "break"

	def _on_drag(self, event):
		if self.drag_anchor is not None:
			self.core.selections[0] = Selection(self.drag_anchor, self._offset_at_xy(event))
			self.draw()
		return "break"

	def _on_key(self, event):
		if self._hover_info is not None:
			self._hover_info = None
			self.draw()
		control = bool(event.state & (0x4 | 0x8))
		shift = bool(event.state & 0x1)
		key = event.keysym
		if control and key.lower() == "q":
			self._toolbar_actions()["quit"]()
			return "break"
		if control and key.lower() in {"b", "i"}:
			self._toolbar_actions()["bold" if key.lower() == "b" else "italic"]()
			return "break"
		if control and key in {"plus", "equal", "KP_Add"}:
			self._toolbar_actions()["font_increase"]()
			return "break"
		if control and key in {"minus", "KP_Subtract"}:
			self._toolbar_actions()["font_decrease"]()
			return "break"
		if key == "F6":
			self._toolbar_actions()["save_as"]()
			return "break"
		if control and shift and key.lower() == "s":
			self._toolbar_actions()["save_as"]()
			return "break"
		if control and key.lower() in {"s", "o", "a", "c", "x", "v", "z", "y"}:
			actions = self._toolbar_actions()
			commands = {"s": actions["save"], "o": actions["open"], "a": self.core.select_all, "c": actions["copy"], "x": actions["cut"], "v": actions["paste"], "z": actions["redo"] if shift else actions["undo"], "y": actions["redo"]}
			commands[key.lower()]()
			return "break"
		if key in {"Left", "Right", "Up", "Down", "Home", "End"}:
			self.core.move_carets(key.upper(), shift)
		elif key == "BackSpace":
			self.core.delete("backward")
		elif key == "Delete":
			self.core.delete("forward")
		elif key in {"Return", "KP_Enter"}:
			self.core.replace_selections("\n")
		elif key == "Tab":
			self.core.replace_selections("    ")
		elif event.char and event.char.isprintable() and not control:
			self.core.replace_selections(event.char, group="typing")
		return "break"

	def copy(self):
		if any(not selection.is_empty for selection in self.core.selections):
			text = self.core.copy()
			self.root.clipboard_clear()
			self.root.clipboard_append(text)

	def cut(self):
		if any(not selection.is_empty for selection in self.core.selections):
			text = self.core.cut()
			self.root.clipboard_clear()
			self.root.clipboard_append(text)

	def paste(self):
		try:
			self.core.paste(self.root.clipboard_get())
		except tk.TclError:
			pass

	def inspect_token(self):
		info = self.core.token_info_at(self.core.selections[0].active, include_previous=True)
		self._hover_info = info
		self.core.message = info.description if info else "No token at caret"
		self.draw()

	def _confirm_discard(self):
		if not self.core.dirty:
			return True
		answer = messagebox.askyesnocancel("Unsaved changes", "Save changes before continuing?", parent=self.root)
		if answer is None:
			return False
		return not answer or self.save_file()

	def open_file(self):
		if not self._confirm_discard():
			return
		path = filedialog.askopenfilename(parent=self.root)
		if path:
			self.core.open_path(path)

	def save_file(self):
		path = self.core.file_path or filedialog.asksaveasfilename(
			parent=self.root,
			defaultextension=".txt",
			filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
		)
		return self.core.save_file(path)

	def save_as(self):
		path = filedialog.asksaveasfilename(
			parent=self.root,
			defaultextension=".txt",
			filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
		)
		return self.core.save_file(path) if path else False

	def _scroll_y(self, *args):
		self.canvas.yview(*args)
		self.draw()

	def _on_mousewheel(self, event):
		self._scroll_y("scroll", -1 if event.delta > 0 else 1, "units")
		return "break"

	def close(self):
		if self._confirm_discard():
			self.root.destroy()

	def run(self):
		self.root.mainloop()


def run_tk(path=None):
	root = tk.Tk()
	TkRenderer(root, path=path).run()


def create_tk_renderer(core, **_options):
	return TkRenderer(tk.Tk(), core=core)
