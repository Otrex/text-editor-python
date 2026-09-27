from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedDocument:
	lines: list[str]
	spans: list[list[tuple[int, int, str]]]
