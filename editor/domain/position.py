from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
	line: int
	column: int