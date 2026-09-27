from dataclasses import dataclass

from editor.composition.colors import register_configured_colors
from editor.config.appearance import DEFAULT_FONT_FAMILY
from editor.config.appearance import DEFAULT_FONT_SIZE
from editor.config.appearance import DEFAULT_FOREGROUND_COLOR
from editor.domain.color import Color


@dataclass(frozen=True)
class EditorAppearance:
	font_family: str
	font_size: int
	foreground_color: Color


def create_editor_appearance():
	register_configured_colors()
	return EditorAppearance(
		font_family=DEFAULT_FONT_FAMILY,
		font_size=DEFAULT_FONT_SIZE,
		foreground_color=getattr(Color, DEFAULT_FOREGROUND_COLOR),
	)
