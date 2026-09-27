from bisect import bisect_right
import sys

import spacy
from spacy.tokens import Doc

from editor.domain.token_info import TokenInfo
from editor.infrastructure.tokenizers.writing.writing_token import WritingToken


_POS_STYLES = {
	"NOUN": "noun",
	"PROPN": "proper_noun",
	"PRON": "pronoun",
	"VERB": "verb",
	"AUX": "auxiliary",
	"ADJ": "adjective",
	"ADV": "adverb",
	"DET": "determiner",
	"ADP": "preposition",
	"CCONJ": "conjunction",
	"SCONJ": "conjunction",
	"NUM": "number",
	"PUNCT": "punctuation",
	"PART": "particle",
	"INTJ": "interjection",
	"SYM": "symbol",
}
_SUBJECT_DEPS = {"nsubj", "nsubjpass", "csubj", "csubjpass"}
_DIRECT_OBJECT_DEPS = {"dobj", "obj"}
_INDIRECT_OBJECT_DEPS = {"dative", "iobj"}
_COMPLEMENT_DEPS = {"attr", "acomp", "oprd"}


class WritingAnalyzer:
	"""Convert spaCy English Doc annotations into editor tokens and style spans."""

	def __init__(self, model_name="en_core_web_sm", nlp=None):
		self.model_name = model_name
		self._nlp = nlp
		self._pos_detectors = []
		self._role_detectors = []
		self._cached_source = None
		self._cached_tokens = ()

	@property
	def nlp(self):
		if self._nlp is None:
			try:
				self._nlp = spacy.load(self.model_name)
			except OSError as error:
				raise RuntimeError(
					f"spaCy model {self.model_name!r} is missing; install it with "
					f"'{sys.executable} -m spacy download {self.model_name}'"
				) from error
		return self._nlp

	def parse(self, source: str) -> Doc:
		return self.nlp(source)

	def register_pos_detector(self, detector, first=False):
		if first:
			self._pos_detectors.insert(0, detector)
		else:
			self._pos_detectors.append(detector)
		self._cached_source = None

	def register_role_detector(self, detector):
		self._role_detectors.append(detector)
		self._cached_source = None

	def analyze(self, source):
		if source == self._cached_source:
			return list(self._cached_tokens)
		doc = self.parse(source)
		tokens = [
			WritingToken(
				text=token.text,
				start=token.idx,
				end=token.idx + len(token.text),
				pos=_POS_STYLES.get(token.pos_, "unknown"),
				dependency=token.dep_,
			)
			for token in doc
		]
		for index, token in enumerate(tokens):
			for detector in self._pos_detectors:
				style = detector(token, index, tokens)
				if style and style != "unknown":
					tokens[index] = WritingToken(token.text, token.start, token.end, style, token.roles, token.dependency)
					break

		roles = [set() for _token in tokens]
		for token in doc:
			if token.dep_ in _SUBJECT_DEPS:
				roles[token.i].add("subject")
			elif token.dep_ in _DIRECT_OBJECT_DEPS:
				roles[token.i].add("direct_object")
			elif token.dep_ in _INDIRECT_OBJECT_DEPS:
				roles[token.i].add("indirect_object")
			elif token.dep_ in _COMPLEMENT_DEPS:
				roles[token.i].add("subject_complement")
			if token.dep_ == "pobj" or (token.dep_ == "obl" and token.head.pos_ == "ADP"):
				roles[token.i].add("object_of_preposition")

		for sentence in doc.sents:
			start = sentence.start
			sentence_tokens = tokens[sentence.start : sentence.end]
			for detector in self._role_detectors:
				for local_index, detected_roles in detector(sentence_tokens).items():
					if 0 <= local_index < len(sentence_tokens):
						if isinstance(detected_roles, str):
							detected_roles = (detected_roles,)
						roles[start + local_index].update(detected_roles)

		self._cached_tokens = tuple(
			WritingToken(token.text, token.start, token.end, token.pos, tuple(sorted(roles[index])), token.dependency)
			for index, token in enumerate(tokens)
		)
		self._cached_source = source
		return list(self._cached_tokens)

	def token_at(self, source, offset):
		for token in self.analyze(source):
			if token.start <= offset < token.end:
				return TokenInfo(token.text, token.start, token.end, token.pos, token.roles, token.dependency)
		return None

	def spans_by_line(self, source):
		line_starts = [0]
		line_starts.extend(index + 1 for index, character in enumerate(source) if character == "\n")
		spans = [[] for _line in line_starts]
		for token in self.analyze(source):
			line_index = bisect_right(line_starts, token.start) - 1
			line_end = source.find("\n", line_starts[line_index])
			if line_end == -1 or token.end <= line_end:
				spans[line_index].append((token.start - line_starts[line_index], token.end - line_starts[line_index], token.style))
		return spans