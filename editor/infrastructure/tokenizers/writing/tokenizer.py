from editor.application.tokenization.base import TokenStyle, Tokenizer
from editor.domain.color import Color
from editor.infrastructure.tokenizers.writing.writing_analyzer import WritingAnalyzer


DEFAULT_WRITING_ANALYZER = WritingAnalyzer()


class WritingTokenizer(Tokenizer):
	name = "English writing"
	extensions = ("txt", "md")
	styles = (
		TokenStyle("noun", Color.CYAN),
		TokenStyle("proper_noun", Color.TEAL),
		TokenStyle("pronoun", Color.MAGENTA),
		TokenStyle("verb", Color.RED),
		TokenStyle("auxiliary", Color.ORANGE),
		TokenStyle("adjective", Color.GREEN),
		TokenStyle("adverb", Color.YELLOW),
		TokenStyle("determiner", Color.GRAY),
		TokenStyle("preposition", Color.SLATE),
		TokenStyle("conjunction", Color.ORANGE),
		TokenStyle("subject", Color.BLUE),
		TokenStyle("direct_object", Color.GREEN),
		TokenStyle("indirect_object", Color.CYAN),
		TokenStyle("object_of_preposition", Color.VIOLET),
		TokenStyle("subject_complement", Color.AMBER),
		TokenStyle("punctuation", Color.GRAY),
		TokenStyle("markdown_heading", Color.BLUE),
		TokenStyle("markdown_fence", Color.MAGENTA),
		TokenStyle("markdown_code", Color.GREEN),
		TokenStyle("markdown_inline_code", Color.GREEN),
		TokenStyle("markdown_link", Color.TEAL),
		TokenStyle("markdown_link_marker", Color.SLATE),
		TokenStyle("markdown_emphasis_marker", Color.AMBER),
		TokenStyle("markdown_bold", Color.RED),
		TokenStyle("markdown_italic", Color.VIOLET),
		TokenStyle("markdown_quote", Color.VIOLET),
		TokenStyle("markdown_list", Color.CYAN),
		TokenStyle("markdown_rule", Color.GRAY),
	)

	def tokenize(self, source):
		return tokenize(source)

	def inspect(self, source, offset):
		return inspect(source, offset)


def analyze(source):
	return DEFAULT_WRITING_ANALYZER.analyze(source)


def tokenize(source):
	return DEFAULT_WRITING_ANALYZER.spans_by_line(source)


def inspect(source, offset):
	return DEFAULT_WRITING_ANALYZER.token_at(source, offset)
