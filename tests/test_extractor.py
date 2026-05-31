import unittest

from panoptibot.text.extractor import (
    caps_ratio,
    classify_archetype,
    extract_terms,
    punctuation_density,
)


class ClassifyArchetypeTest(unittest.TestCase):
    def test_art_post_short_text(self) -> None:
        self.assertEqual(classify_archetype("nice", has_attachment=True), "art_post")

    def test_art_post_no_text(self) -> None:
        self.assertEqual(classify_archetype("", has_attachment=True), "art_post")

    def test_art_commentary_long_text(self) -> None:
        self.assertEqual(
            classify_archetype("x" * 61, has_attachment=True), "art_commentary"
        )

    def test_discussion_long_no_attachment(self) -> None:
        self.assertEqual(
            classify_archetype("x" * 201, has_attachment=False), "discussion"
        )

    def test_question_ends_with_questionmark(self) -> None:
        self.assertEqual(
            classify_archetype("Did you see this?", has_attachment=False), "question"
        )

    def test_question_starts_with_question_word(self) -> None:
        self.assertEqual(
            classify_archetype("what do you think", has_attachment=False), "question"
        )

    def test_reaction_short(self) -> None:
        self.assertEqual(classify_archetype("lmao yes", has_attachment=False), "reaction")

    def test_reaction_empty(self) -> None:
        self.assertEqual(classify_archetype("", has_attachment=False), "reaction")


class CapsRatioTest(unittest.TestCase):
    def test_all_lower(self) -> None:
        self.assertAlmostEqual(caps_ratio("hello"), 0.0)

    def test_all_upper(self) -> None:
        self.assertAlmostEqual(caps_ratio("HELLO"), 1.0)

    def test_mixed(self) -> None:
        self.assertAlmostEqual(caps_ratio("Hello"), 0.2)

    def test_empty(self) -> None:
        self.assertEqual(caps_ratio(""), 0.0)

    def test_no_alpha(self) -> None:
        self.assertEqual(caps_ratio("123 !?"), 0.0)


class PunctuationDensityTest(unittest.TestCase):
    def test_no_punctuation(self) -> None:
        self.assertAlmostEqual(punctuation_density("hello"), 0.0)

    def test_all_punctuation(self) -> None:
        self.assertAlmostEqual(punctuation_density("!!!"), 1.0)

    def test_mixed(self) -> None:
        density = punctuation_density("hi!")
        self.assertAlmostEqual(density, 1 / 3, places=4)

    def test_empty(self) -> None:
        self.assertEqual(punctuation_density(""), 0.0)


class ExtractTermsTest(unittest.TestCase):
    def test_basic_tokens(self) -> None:
        terms = extract_terms("limbus company fan")
        self.assertIn("limbus", terms)
        self.assertIn("company", terms)
        self.assertIn("fan", terms)

    def test_stop_words_filtered(self) -> None:
        terms = extract_terms("the and for that")
        self.assertEqual(terms, [])

    def test_short_tokens_excluded(self) -> None:
        terms = extract_terms("hi ok go")
        self.assertEqual(terms, [])

    def test_discord_markup_stripped(self) -> None:
        terms = extract_terms("<@12345> hello ishmael")
        self.assertNotIn("<@12345>", terms)
        self.assertIn("hello", terms)
        self.assertIn("ishmael", terms)

    def test_url_stripped(self) -> None:
        terms = extract_terms("check https://example.com/art ishmael")
        self.assertNotIn("https", terms)
        self.assertIn("ishmael", terms)

    def test_bigrams_produced(self) -> None:
        terms = extract_terms("ishmael ryoshu")
        self.assertIn("ishmael_ryoshu", terms)

    def test_uppercase_normalized(self) -> None:
        terms = extract_terms("ISHMAEL RYOSHU")
        self.assertIn("ishmael", terms)
        self.assertIn("ryoshu", terms)


if __name__ == "__main__":
    unittest.main()
