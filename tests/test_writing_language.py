import unittest

from spacy.tokens import Doc

from editor.composition.registries import create_tokenizer_registry
from editor.infrastructure.tokenizers.writing import analyze as writing_tokens
from editor.infrastructure.tokenizers.writing.writing_analyzer import WritingAnalyzer


class WritingLanguageTests(unittest.TestCase):
	def token(self, tokens, text):
		return next(token for token in tokens if token.text == text)

	def test_identifies_parts_of_speech_and_basic_sentence_roles(self):
		tokens = writing_tokens("The curious student gave her teacher a thoughtful letter.")

		self.assertEqual(self.token(tokens, "curious").pos, "adjective")
		self.assertEqual(self.token(tokens, "gave").pos, "verb")
		self.assertIn("subject", self.token(tokens, "student").roles)
		self.assertIn("indirect_object", self.token(tokens, "teacher").roles)
		self.assertIn("direct_object", self.token(tokens, "letter").roles)

	def test_analyzer_uses_spacy_doc_with_dependency_labels(self):
		analyzer = WritingAnalyzer()
		doc = analyzer.parse("A student reads a book.")

		self.assertIsInstance(doc, Doc)
		self.assertEqual(next(token for token in doc if token.text == "student").dep_, "nsubj")
		self.assertEqual(self.token(analyzer.analyze("A student reads a book."), "book").roles, ("direct_object",))

	def test_identifies_subject_complement_and_prepositional_object(self):
		tokens = writing_tokens("The dog is happy near the house.")

		self.assertIn("subject", self.token(tokens, "dog").roles)
		self.assertIn("subject_complement", self.token(tokens, "happy").roles)
		self.assertIn("object_of_preposition", self.token(tokens, "house").roles)

	def test_configured_registry_applies_writing_styles_to_text_and_markdown(self):
		registry = create_tokenizer_registry()
		for path in ("story.txt", "story.md"):
			spans = registry.tokenize(path, "Birds fly.")
			self.assertIn((0, 5, "subject"), spans[0])
			self.assertIn((6, 9, "verb"), spans[0])

	def test_custom_pos_detector_can_extend_unknown_words(self):
		analyzer = WritingAnalyzer()
		analyzer.register_pos_detector(
			lambda token, _index, _tokens: "invented_pos" if token.text == "glorp" else None,
		)

		self.assertEqual(self.token(analyzer.analyze("glorp"), "glorp").pos, "invented_pos")

	def test_custom_role_detector_adds_an_annotation(self):
		analyzer = WritingAnalyzer()
		analyzer.register_role_detector(lambda tokens: {0: "custom_role"} if tokens else {})

		self.assertIn("custom_role", analyzer.analyze("The student reads.")[0].roles)

	def test_handles_object_pronoun_and_sentence_initial_name(self):
		her_tokens = writing_tokens("I saw her.")
		mia_tokens = writing_tokens("Mia walked to school.")

		self.assertEqual(self.token(her_tokens, "her").pos, "pronoun")
		self.assertIn("direct_object", self.token(her_tokens, "her").roles)
		self.assertEqual(self.token(mia_tokens, "Mia").pos, "proper_noun")
		self.assertIn("subject", self.token(mia_tokens, "Mia").roles)
		self.assertIn("object_of_preposition", self.token(mia_tokens, "school").roles)

	def test_known_noun_precedes_adjective_suffix_rules(self):
		token = self.token(writing_tokens("An animal slept."), "animal")

		self.assertEqual(token.pos, "noun")
		self.assertIn("subject", token.roles)


if __name__ == "__main__":
	unittest.main()
