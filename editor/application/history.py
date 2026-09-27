from time import monotonic


class UndoHistory:
	def __init__(self, grouping_interval=0.9):
		self.grouping_interval = grouping_interval
		self.undo_stack = []
		self.redo_stack = []
		self._last_group = None
		self._last_edit_time = 0

	def record(self, text, selections, group=None, metadata=None):
		now = monotonic()
		if group is None or group != self._last_group or now - self._last_edit_time > self.grouping_interval:
			self.undo_stack.append(self._state(text, selections, metadata))
		self.redo_stack.clear()
		self._last_group = group
		self._last_edit_time = now

	def undo(self, text, selections, metadata=None):
		if not self.undo_stack:
			return None
		self.redo_stack.append(self._state(text, selections, metadata))
		self._last_group = None
		return self.undo_stack.pop()

	def redo(self, text, selections, metadata=None):
		if not self.redo_stack:
			return None
		self.undo_stack.append(self._state(text, selections, metadata))
		self._last_group = None
		return self.redo_stack.pop()

	def clear(self):
		self.undo_stack.clear()
		self.redo_stack.clear()
		self._last_group = None
		self._last_edit_time = 0

	def break_group(self):
		self._last_group = None

	@staticmethod
	def _state(text, selections, metadata):
		state = (text, tuple(selections))
		return state if metadata is None else (*state, metadata)