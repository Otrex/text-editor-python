from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
	anchor: int
	active: int

	@property
	def start(self):
		return min(self.anchor, self.active)

	@property
	def end(self):
		return max(self.anchor, self.active)

	@property
	def is_empty(self):
		return self.anchor == self.active