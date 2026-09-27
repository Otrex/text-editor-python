from editor.application.registries.base import ExtensionRegistry
from editor.application.subrendering.document import RenderedDocument


class SubRendererRegistry:
	def __init__(self):
		self._by_extension = ExtensionRegistry()
		self._cached_path = None
		self._cached_base_spans = None
		self._cached_result = None

	def register(self, sub_renderer):
		self._by_extension.register_extensions(sub_renderer.extensions, sub_renderer)
		self._cached_path = None
		self._cached_base_spans = None
		self._cached_result = None
		return sub_renderer

	def for_path(self, path):
		return self._by_extension.for_path(path)

	def render_view(self, path, lines, base_spans):
		if path == self._cached_path and base_spans is self._cached_base_spans:
			return self._cached_result
		renderer = self.for_path(path)
		result = RenderedDocument(lines, base_spans) if renderer is None else renderer.render_view(lines, base_spans)
		self._cached_path = path
		self._cached_base_spans = base_spans
		self._cached_result = result
		return result

	def render_document(self, path, lines, base_spans):
		return self.render_view(path, lines, base_spans).spans
