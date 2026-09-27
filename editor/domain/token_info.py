from dataclasses import dataclass


@dataclass(frozen=True)
class TokenInfo:
	text: str
	start: int
	end: int
	kind: str
	roles: tuple[str, ...] = ()
	dependency: str = ""

	@property
	def description(self):
		labels = [self.kind.replace("_", " ")]
		labels.extend(role.replace("_", " ") for role in self.roles)
		if self.dependency:
			labels.append(f"dep: {self.dependency}")
		return f"{self.text} | {' | '.join(labels)}"