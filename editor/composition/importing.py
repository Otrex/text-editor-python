from importlib import import_module


def import_object(path):
	module_name, object_name = path.rsplit(".", 1)
	return getattr(import_module(module_name), object_name)
