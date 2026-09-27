from dataclasses import dataclass

from editor.domain.color import Color
from editor.domain.token_info import TokenInfo


def normalize_extension(extension):
	extension = extension.lower()
	if not extension:
		return ""
	return extension if extension.startswith(".") else f".{extension}"


@dataclass(frozen=True)
class TokenStyle:
	name: str
	color: Color


class Tokenizer:
	name = "Tokenizer"
	extensions = ()
	styles = ()

	def __init__(self):
		self.extensions = tuple(normalize_extension(extension) for extension in self.extensions)
		self.colors = {style.name: style.color for style in self.styles}

	def tokenize(self, source):
		raise NotImplementedError

	def inspect(self, source, offset) -> TokenInfo | None:
		return None


class PlainTextTokenizer(Tokenizer):
	name = "Plain text"
	extensions = ("",)

	def tokenize(self, source):
		return [[] for _line in source.split("\n")]


class FunctionTokenizer(Tokenizer):
	def __init__(self, extensions, tokenize, colors=None, name=None, inspect=None):
		self.name = name or getattr(tokenize, "__name__", "tokenizer")
		self.extensions = tuple(normalize_extension(extension) for extension in ([extensions] if isinstance(extensions, str) else extensions))
		self._tokenize = tokenize
		self._inspect = inspect
		self.colors = dict(colors or {})

	def tokenize(self, source):
		return self._tokenize(source)

	def inspect(self, source, offset):
		if self._inspect is None:
			return None
		return self._inspect(source, offset)
