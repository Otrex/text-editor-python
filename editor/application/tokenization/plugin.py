from editor.application.tokenization.base import FunctionTokenizer


class TokenizerPlugin(FunctionTokenizer):
	def __init__(self, extensions, tokenize, colors=None, name=None, inspect=None):
		super().__init__(extensions, tokenize, colors, name, inspect)
