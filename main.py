from editor.composition.launcher import run_editor


def main(argv=None, renderers=None):
	return run_editor(argv, renderers=renderers)


if __name__ == "__main__":
	raise SystemExit(main())
