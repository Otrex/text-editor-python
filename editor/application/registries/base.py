import os


class Registry:
	def __init__(self, normalizer=None):
		self._items = {}
		self._normalizer = normalizer or (lambda key: key)

	def register(self, key, value, *aliases):
		for name in (key, *aliases):
			self._items[self._normalize(name)] = value
		return value

	def get(self, key, default=None):
		return self._items.get(self._normalize(key), default)

	def require(self, key):
		try:
			return self._items[self._normalize(key)]
		except KeyError as error:
			raise ValueError(f"Unknown registry key: {key}") from error

	@property
	def names(self):
		return tuple(sorted(self._items))

	def items(self):
		return tuple(sorted(self._items.items()))

	def _normalize(self, key):
		return self._normalizer(key)


class ExtensionRegistry(Registry):
	def __init__(self):
		super().__init__(_normalize_extension)

	def register_extensions(self, extensions, value):
		for extension in extensions:
			self.register(extension, value)
		return value

	def for_path(self, path, default=None):
		if not path:
			return default
		return self.get(os.path.splitext(os.fspath(path))[1], default)


def _normalize_extension(extension):
	extension = str(extension).lower()
	if not extension:
		return ""
	return extension if extension.startswith(".") else f".{extension}"
