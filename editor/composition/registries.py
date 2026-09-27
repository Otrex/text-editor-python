from editor.application.registries.renderers import RendererRegistry
from editor.application.registries.subrenderers import SubRendererRegistry
from editor.application.registries.tokenizers import TokenizerRegistry
from editor.composition.colors import register_configured_colors
from editor.composition.importing import import_object
from editor.config.renderers import RENDERERS
from editor.config.subrenderers import SUB_RENDERERS
from editor.config.tokenizers import TOKENIZERS


register_configured_colors()


def create_renderer_registry(entries=RENDERERS):
	registry = RendererRegistry()
	for name, factory_path, aliases in entries:
		registry.register(name, import_object(factory_path), *aliases)
	return registry


def create_tokenizer_registry(entries=TOKENIZERS):
	register_configured_colors()
	registry = TokenizerRegistry()
	for tokenizer_path in entries:
		registry.register(import_object(tokenizer_path))
	return registry


def create_sub_renderer_registry(entries=SUB_RENDERERS):
	registry = SubRendererRegistry()
	for sub_renderer_path in entries:
		sub_renderer = import_object(sub_renderer_path)
		registry.register(sub_renderer() if isinstance(sub_renderer, type) else sub_renderer)
	return registry
