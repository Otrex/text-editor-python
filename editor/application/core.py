import os

from editor.domain.position import Position
from editor.domain.selection import Selection
from editor.domain.token_info import TokenInfo
from editor.domain.text_model import TextModel
from editor.application.registries.tokenizers import TokenizerRegistry
from editor.application.history import UndoHistory


class EditorCore:
	def __init__(self, path=None, tokenizers: TokenizerRegistry | None = None, on_change=None):
		self.model = TextModel()
		self.formatting = []
		self.selections = [Selection(0, 0)]
		self.history = UndoHistory()
		self.saved_text = ""
		self.file_path = None
		self.clipboard = ""
		self.dirty = False
		self.message = ""
		self.tokenizers = tokenizers or TokenizerRegistry()
		self._token_spans = None
		self.on_change = on_change
		if path:
			self.open_path(path)

	@property
	def token_spans(self):
		if self._token_spans is None:
			self._token_spans = self.tokenizers.tokenize(self.file_path, self.model.get_text())
		return self._token_spans

	@property
	def tokenizer(self):
		return self.tokenizers.plugin_for(self.file_path)

	def color_for(self, style, renderer):
		color = self.tokenizer.colors.get(style)
		return color.for_renderer(renderer) if color else None

	def format_at(self, offset, include_previous=False):
		self._ensure_formatting_size()
		if not self.formatting:
			return {}
		if include_previous and offset == len(self.formatting):
			offset -= 1
		return dict(self.formatting[min(max(offset, 0), len(self.formatting) - 1)])

	def set_format(self, attribute, value=None):
		self._ensure_formatting_size()
		ranges = [(selection.start, selection.end) for selection in self.selections if not selection.is_empty]
		if not ranges:
			return False
		self.history.record(
			self.model.get_text(),
			self.selections,
			metadata=self._formatting_snapshot(),
		)
		for start, end in ranges:
			if value is None and attribute in {"bold", "italic"}:
				enable = not all(self.formatting[index].get(attribute, False) for index in range(start, end))
				current = enable
			else:
				current = value
			for index in range(start, end):
				if current is None:
					self.formatting[index].pop(attribute, None)
				else:
					self.formatting[index][attribute] = current
		self._notify()
		return True

	def _formatting_snapshot(self):
		return tuple(dict(attributes) for attributes in self.formatting)

	def _ensure_formatting_size(self):
		text_length = len(self.model.get_text())
		if len(self.formatting) != text_length:
			self.formatting = [{} for _character in range(text_length)]

	def token_info_at(self, offset, include_previous=False):
		source = self.model.get_text()
		if not source:
			return None
		offset = min(max(offset, 0), len(source))
		plugin = self.tokenizer
		if plugin.inspect:
			info = plugin.inspect(source, offset) if offset < len(source) else None
			if info is None and include_previous and offset:
				info = plugin.inspect(source, offset - 1)
			if info is not None:
				return info

		for candidate in ((offset, offset - 1) if include_previous else (offset,)):
			if not 0 <= candidate < len(source):
				continue
			position = self.model.position_at(candidate)
			for start, end, style in self.token_spans[position.line]:
				if start <= position.column < end:
					line_start = self.model.offset_at(Position(position.line, 0))
					return TokenInfo(
						source[line_start + start : line_start + end],
						line_start + start,
						line_start + end,
						style,
					)
		return None

	def _mark_changed(self):
		self.dirty = self.model.get_text() != self.saved_text
		self._token_spans = None
		self._notify()

	def _notify(self):
		if self.on_change:
			self.on_change()

	def move_carets(self, direction, extend=False):
		moved = []
		for selection in self.selections:
			if not extend and not selection.is_empty:
				offset = selection.start if direction in {"LEFT", "UP", "HOME"} else selection.end
			else:
				offset = selection.active
				position = self.model.position_at(offset)
				if direction == "LEFT":
					offset = max(0, offset - 1)
				elif direction == "RIGHT":
					offset = min(len(self.model.get_text()), offset + 1)
				elif direction == "UP":
					offset = self.model.offset_at(Position(max(0, position.line - 1), position.column))
				elif direction == "DOWN":
					offset = self.model.offset_at(Position(min(self.model.line_count - 1, position.line + 1), position.column))
				elif direction == "HOME":
					offset = self.model.offset_at(Position(position.line, 0))
				elif direction == "END":
					offset = self.model.offset_at(Position(position.line, len(self.model.get_line_content(position.line))))
			moved.append(Selection(selection.anchor if extend else offset, offset))
		self.selections = moved
		self.history.break_group()
		self._notify()

	def add_vertical_caret(self, delta):
		primary = self.model.position_at(self.selections[0].active)
		line = primary.line + delta
		if not 0 <= line < self.model.line_count:
			return
		offset = self.model.offset_at(Position(line, primary.column))
		self.selections.insert(0, Selection(offset, offset))
		self.history.break_group()
		self._notify()

	def replace_selections(self, text, group=None):
		edits = [(selection.start, selection.end, text, index) for index, selection in enumerate(self.selections)]
		self.apply_edits(edits, group)

	def delete(self, direction):
		text_length = len(self.model.get_text())
		edits = []
		for index, selection in enumerate(self.selections):
			start, end = selection.start, selection.end
			if selection.is_empty:
				if direction == "backward":
					start = max(0, start - 1)
				else:
					end = min(text_length, end + 1)
			if start != end:
				edits.append((start, end, "", index))
		self.apply_edits(edits)

	def apply_edits(self, edits, group=None):
		if not edits:
			return
		self._ensure_formatting_size()
		combined = {}
		for start, end, text, index in edits:
			combined.setdefault((start, end), [text, []])[1].append(index)
		ordered = [(start, end, value[0], value[1]) for (start, end), value in combined.items()]
		ordered.sort(key=lambda edit: (edit[0], edit[1]))
		merged = []
		for start, end, text, indices in ordered:
			if merged and start < merged[-1][1]:
				merged[-1][1] = max(merged[-1][1], end)
				merged[-1][3].extend(indices)
			else:
				merged.append([start, end, text, list(indices)])

		self.history.record(self.model.get_text(), self.selections, group, self._formatting_snapshot())
		for start, end, text, _indices in reversed(merged):
			self.model.replace(start, end, text)
			self.formatting[start:end] = [{} for _character in text]

		new_selections = [None] * len(self.selections)
		shift = 0
		for start, end, text, indices in merged:
			position = start + shift + len(text)
			for index in indices:
				new_selections[index] = Selection(position, position)
			shift += len(text) - (end - start)
		self.selections = [selection for selection in new_selections if selection is not None]
		self._mark_changed()

	def select_all(self):
		self.selections = [Selection(0, len(self.model.get_text()))]
		self.history.break_group()
		self._notify()

	def copy(self):
		selected = [self.model.get_text()[selection.start : selection.end] for selection in self.selections if not selection.is_empty]
		if not selected:
			return self.clipboard
		self.clipboard = "\n".join(selected)
		return self.clipboard

	def cut(self):
		selected = [(selection.start, selection.end, "", index) for index, selection in enumerate(self.selections) if not selection.is_empty]
		if selected:
			self.copy()
			self.apply_edits(selected)
		return self.clipboard

	def paste(self, text=None):
		if text is not None:
			self.clipboard = text
		self.replace_selections(self.clipboard)

	def undo(self):
		state = self.history.undo(self.model.get_text(), self.selections, self._formatting_snapshot())
		if state is not None:
			self.model = TextModel(state[0])
			self.selections = list(state[1])
			self.formatting = list(state[2]) if len(state) > 2 else [{} for _character in state[0]]
			self._mark_changed()

	def redo(self):
		state = self.history.redo(self.model.get_text(), self.selections, self._formatting_snapshot())
		if state is not None:
			self.model = TextModel(state[0])
			self.selections = list(state[1])
			self.formatting = list(state[2]) if len(state) > 2 else [{} for _character in state[0]]
			self._mark_changed()

	def open_path(self, path):
		try:
			with open(path, "r", encoding="utf-8") as file:
				text = file.read()
		except (OSError, UnicodeError) as error:
			self.message = f"Open failed: {error}"
			return False
		self.model = TextModel(text)
		self.formatting = [{} for _character in text]
		self.file_path = os.fspath(path)
		self.selections = [Selection(0, 0)]
		self.history.clear()
		self.saved_text = text
		self.dirty = False
		self._token_spans = None
		self._notify()
		return True

	def save_file(self, path=None):
		path = path or self.file_path
		if not path:
			return False
		try:
			with open(path, "w", encoding="utf-8", newline="") as file:
				file.write(self.model.get_text())
		except OSError as error:
			self.message = f"Save failed: {error}"
			return False
		self.file_path = os.fspath(path)
		self.saved_text = self.model.get_text()
		self.dirty = False
		self._token_spans = None
		self.message = f"Saved {self.file_path}"
		self._notify()
		return True
