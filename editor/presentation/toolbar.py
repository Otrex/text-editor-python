from dataclasses import dataclass


@dataclass(frozen=True)
class ToolbarCommand:
	id: str
	label: str
	short_label: str
	shortcut: str = ""


@dataclass(frozen=True)
class ToolbarSeparator:
	pass


TOOLBAR_ITEMS = (
	ToolbarCommand("open", "Open", "Open", "Ctrl+O"),
	ToolbarCommand("save", "Save", "Save", "Ctrl+S"),
	ToolbarCommand("save_as", "Save As", "Save As", "F6"),
	ToolbarSeparator(),
	ToolbarCommand("undo", "Undo", "Undo", "Ctrl+Z"),
	ToolbarCommand("redo", "Redo", "Redo", "Ctrl+Y"),
	ToolbarSeparator(),
	ToolbarCommand("cut", "Cut", "Cut", "Ctrl+X"),
	ToolbarCommand("copy", "Copy", "Copy", "Ctrl+C"),
	ToolbarCommand("paste", "Paste", "Paste", "Ctrl+V"),
	ToolbarSeparator(),
	ToolbarCommand("bold", "Bold", "B", "F2"),
	ToolbarCommand("italic", "Italic", "I", "F3"),
	ToolbarCommand("font_decrease", "Decrease font size", "-", "F5"),
	ToolbarCommand("font_increase", "Increase font size", "+", "F4"),
	ToolbarSeparator(),
	ToolbarCommand("inspect", "Inspect token", "Inspect", "F1"),
	ToolbarCommand("quit", "Quit", "Quit", "Ctrl+Q"),
)


def command_items(items=TOOLBAR_ITEMS):
	return tuple(item for item in items if isinstance(item, ToolbarCommand))


def toolbar_summary(items=TOOLBAR_ITEMS):
	parts = []
	group = []
	for item in items:
		if isinstance(item, ToolbarSeparator):
			if group:
				parts.append("  ".join(group))
				group = []
			continue
		label = item.short_label or item.label
		group.append(f"{item.shortcut} {label}" if item.shortcut else label)
	if group:
		parts.append("  ".join(group))
	return " | ".join(parts)
