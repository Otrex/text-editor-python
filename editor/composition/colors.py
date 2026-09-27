from editor.config.colors import COLOR_DEFINITIONS
from editor.domain.color import Color


def register_configured_colors(definitions=COLOR_DEFINITIONS):
	for name, tk_value, terminal_value in definitions:
		setattr(Color, name, Color(tk=tk_value, terminal=terminal_value))
	return Color
