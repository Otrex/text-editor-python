import re

from editor.application.subrendering.base import SubRenderer
from editor.application.subrendering.document import RenderedDocument


class MarkdownSubRenderer(SubRenderer):
	"""Overlay Markdown syntax styles while leaving document ownership to the host renderer."""

	extensions = (".md", ".markdown", ".mdown")
	_heading = re.compile(r"^ {0,3}(#{1,6})(?=\s|$)")
	_setext = re.compile(r"^ {0,3}(?:=+|-+)\s*$")
	_fence = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
	_rule = re.compile(r"^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
	_list = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)])(?=\s)")
	_quote = re.compile(r"^ {0,3}(?:> ?)+")
	_inline_code = re.compile(r"(`+)(.+?)\1")
	_link = re.compile(r"!?\[([^\]]+)\]\(([^)]+)\)")
	_bold = re.compile(r"(?<!\*)\*\*(?=\S)(.+?)(?<=\S)\*\*(?!\*)|(?<!_)__(?=\S)(.+?)(?<=\S)__(?!_)")
	_italic = re.compile(r"(?<!\*)\*(?!\*)(?=\S)(.+?)(?<=\S)\*(?!\*)|(?<!_)_(?!_)(?=\S)(.+?)(?<=\S)_(?!_)")

	def render_view(self, lines, base_spans):
		preview_lines = []
		preview_spans = []
		fence = None
		for line in lines:
			match = self._fence.match(line)
			if match:
				marker = match.group(1)
				if fence is None:
					fence = (marker[0], len(marker))
					language = match.group(2).strip()
					preview = f"Code block{f' ({language})' if language else ''}"
				elif marker[0] == fence[0] and len(marker) >= fence[1] and not match.group(2).strip():
					fence = None
					preview = ""
				else:
					preview = line
				style = "markdown_fence"
			elif fence is not None:
				preview = line
				style = "markdown_code"
			else:
				preview, style = self._preview_line(line)
			preview_lines.append(preview)
			preview_spans.append([(0, len(preview), style)] if preview and style else [])
		return RenderedDocument(preview_lines, preview_spans)

	def render_document(self, lines, base_spans):
		composed = []
		fence = None
		for line, base in zip(lines, base_spans):
			overlays = []
			match = self._fence.match(line)
			if match:
				marker = match.group(1)
				if fence is None:
					fence = (marker[0], len(marker))
				elif marker[0] == fence[0] and len(marker) >= fence[1] and not match.group(2).strip():
					fence = None
				overlays.append((0, len(line), "markdown_fence"))
			elif fence is not None:
				overlays.append((0, len(line), "markdown_code"))
			else:
				heading = self._heading.match(line)
				if heading:
					overlays.append((0, len(line), "markdown_heading"))
				elif self._setext.match(line):
					overlays.append((0, len(line), "markdown_heading"))
				quote = self._quote.match(line)
				if quote:
					overlays.append((0, quote.end(), "markdown_quote"))
				list_marker = self._list.match(line)
				if list_marker:
					overlays.append((list_marker.start(), list_marker.end(), "markdown_list"))
				if self._rule.match(line):
					overlays.append((0, len(line), "markdown_rule"))
				for match in self._inline_code.finditer(line):
					overlays.append((match.start(), match.end(), "markdown_inline_code"))
				for match in self._link.finditer(line):
					label_start, label_end = match.span(1)
					destination_start, destination_end = match.span(2)
					overlays.extend(
						[
							(match.start(), label_start, "markdown_link_marker"),
							(label_end, destination_start, "markdown_link_marker"),
							(destination_start, destination_end, "markdown_link"),
							(destination_end, match.end(), "markdown_link_marker"),
						]
					)
				for pattern in (self._bold, self._italic):
					for match in pattern.finditer(line):
						style = "markdown_bold" if pattern is self._bold else "markdown_italic"
						content = next(group for group in (1, 2) if match.group(group) is not None)
						content_start, content_end = match.span(content)
						overlays.extend(
							[
								(match.start(), content_start, "markdown_emphasis_marker"),
								(content_start, content_end, style),
								(content_end, match.end(), "markdown_emphasis_marker"),
							]
						)
			composed.append(_overlay_styles(line, base, overlays))
		return composed

	def _preview_line(self, line):
		if not line:
			return line, None
		if self._rule.match(line):
			return "----------------", "markdown_rule"
		heading = self._heading.match(line)
		if heading:
			return line[heading.end() :].strip(), "markdown_heading"
		if self._setext.match(line):
			return "", "markdown_heading"
		quote = self._quote.match(line)
		if quote:
			return self._strip_inline(line[quote.end() :].strip()), "markdown_quote"
		list_marker = self._list.match(line)
		if list_marker:
			return f"* {self._strip_inline(line[list_marker.end() :].strip())}", "markdown_list"
		return self._strip_inline(line), None

	def _strip_inline(self, line):
		line = self._link.sub(lambda match: match.group(1), line)
		line = self._inline_code.sub(lambda match: match.group(2), line)
		line = self._bold.sub(lambda match: next(group for group in match.groups() if group is not None), line)
		line = self._italic.sub(lambda match: next(group for group in match.groups() if group is not None), line)
		return line


def _overlay_styles(line, base, overlays):
	styles = [None] * len(line)
	for start, end, style in base:
		for column in range(max(0, start), min(len(line), end)):
			styles[column] = style
	for start, end, style in overlays:
		for column in range(max(0, start), min(len(line), end)):
			styles[column] = style

	spans = []
	start = 0
	while start < len(styles):
		style = styles[start]
		end = start + 1
		while end < len(styles) and styles[end] == style:
			end += 1
		if style is not None:
			spans.append((start, end, style))
		start = end
	return spans
