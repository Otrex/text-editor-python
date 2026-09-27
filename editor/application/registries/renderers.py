from editor.application.registries.base import Registry


class RendererRegistry:
	def __init__(self):
		self._renderers = Registry(lambda name: str(name).lower())

	def register(self, name, factory, *aliases):
		self._renderers.register(name, factory, *aliases)
		return factory

	def create(self, name, core, **options):
		return self._renderers.require(name)(core=core, **options)

	@property
	def names(self):
		return self._renderers.names
