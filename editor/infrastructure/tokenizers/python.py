import builtins
import io
import keyword
import tokenize as python_tokenize

from editor.application.tokenization.base import TokenStyle, Tokenizer
from editor.domain.color import Color


class PythonTokenizer(Tokenizer):
	name = "Python"
	extensions = ("py",)
	styles = (
		TokenStyle("keyword", Color.RED),
		TokenStyle("string", Color.GREEN),
		TokenStyle("number", Color.MAGENTA),
		TokenStyle("operator", Color.CYAN),
		TokenStyle("comment", Color.GRAY),
		TokenStyle("builtin", Color.RED),
	)

	def tokenize(self, source):
		return tokenize(source)


def tokenize(source):
	lines = source.split("\n")
	spans = [[] for _line in lines]
	builtin_names = set(dir(builtins))
	styles = {
		python_tokenize.STRING: "string",
		python_tokenize.NUMBER: "number",
		python_tokenize.COMMENT: "comment",
		python_tokenize.OP: "operator",
	}

	try:
		for item in python_tokenize.generate_tokens(io.StringIO(source).readline):
			style = styles.get(item.type)
			if item.type == python_tokenize.NAME:
				if keyword.iskeyword(item.string):
					style = "keyword"
				elif item.string in builtin_names:
					style = "builtin"
			if style is None:
				continue
			start_line, start_column = item.start
			end_line, end_column = item.end
			for line_number in range(start_line, end_line + 1):
				line_index = line_number - 1
				if not 0 <= line_index < len(lines):
					continue
				start = start_column if line_number == start_line else 0
				end = end_column if line_number == end_line else len(lines[line_index])
				if end > start:
					spans[line_index].append((start, end, style))
	except (IndentationError, python_tokenize.TokenError):
		pass
	return spans
