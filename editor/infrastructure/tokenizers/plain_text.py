from editor.application.tokenization.base import Tokenizer


class PlainTextTokenizer(Tokenizer):
	name = "Plain text"
	extensions = ("",)

	def tokenize(self, source):
		return tokenize(source)


def tokenize(source):
	return [[] for _line in source.split("\n")]
