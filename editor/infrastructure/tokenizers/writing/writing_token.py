from dataclasses import dataclass


@dataclass(frozen=True)
class WritingToken:
	text: str
	start: int
	end: int
	pos: str
	roles: tuple[str, ...] = ()
	dependency: str = ""

	@property
	def style(self):
		for role in ("subject", "direct_object", "indirect_object", "object_of_preposition", "subject_complement"):
			if role in self.roles:
				return role
		return self.pos