from editor.application.tokenization.base import FunctionTokenizer, PlainTextTokenizer, Tokenizer
from editor.application.registries.base import ExtensionRegistry


class TokenizerRegistry:
	def __init__(self, fallback=None):
		self._fallback = self._coerce(fallback) if fallback is not None else PlainTextTokenizer()
		self._by_extension = ExtensionRegistry()

	def register(self, extensions, tokenizer=None, colors=None, name=None):
		plugin = self._coerce(extensions, tokenizer, colors, name)
		return self._by_extension.register_extensions(plugin.extensions, plugin)

	def plugin_for(self, path):
		return self._by_extension.for_path(path, self._fallback)

	def tokenize(self, path, source):
		return self.plugin_for(path).tokenize(source)

	def _coerce(self, candidate, tokenizer=None, colors=None, name=None):
		if isinstance(candidate, type) and issubclass(candidate, Tokenizer):
			return candidate()
		if isinstance(candidate, Tokenizer):
			return candidate
		return FunctionTokenizer(candidate, tokenizer, colors, name)
