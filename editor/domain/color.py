from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, init=False)
class Color:
	"""A semantic color with values for each renderer backend."""

	values: dict[str, Any] = field(default_factory=dict)

	def __init__(self, tk=None, terminal=None, **values):
		implementations = dict(values)
		if tk is not None:
			implementations["tk"] = tk
		if terminal is not None:
			implementations["terminal"] = terminal
		object.__setattr__(self, "values", implementations)

	def for_renderer(self, renderer):
		key = {"cli": "terminal", "curses": "terminal"}.get(renderer, renderer)
		return self.values.get(key)
