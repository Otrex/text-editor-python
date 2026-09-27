import re

from editor.application.tokenization.base import TokenStyle, Tokenizer
from editor.domain.color import Color


_KEYWORDS = re.compile(r"\b(function|const|let|return)\b")


class JavaScriptTokenizer(Tokenizer):
	name = "JavaScript"
	extensions = ("js",)
	styles = (
		TokenStyle("keyword", Color.RED),
	)

	def tokenize(self, source):
		return tokenize(source)


def tokenize(source):
	return [
		[(match.start(), match.end(), "keyword") for match in _KEYWORDS.finditer(line)]
		for line in source.split("\n")
	]
