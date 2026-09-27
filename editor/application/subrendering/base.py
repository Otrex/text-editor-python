from editor.application.subrendering.document import RenderedDocument


class SubRenderer:
	extensions = ()

	def render_view(self, lines, base_spans):
		return RenderedDocument(lines, self.render_document(lines, base_spans))

	def render_document(self, lines, base_spans):
		return base_spans
