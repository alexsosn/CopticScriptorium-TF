"""Adversarial positional lexical controls: source and Greek word ORDER matters."""
import unittest

from tests.live_issue205_psalm_verse2_guard import ordered_lexical_controls


class OrderedPsalmEvidenceTests(unittest.TestCase):
    def test_psalm_three_source2_and_greek4_must_start_with_corresponding_two_words(self):
        c = ("ⲛⲑⲟⲕ", "ⲇⲉ", "ⲡ", "ϭⲟⲓⲥ")
        g2 = ("Κύριε", "τί", "ἐπληθύνθησαν")
        g4 = ("σὺ", "δέ", "κύριε")
        expected = {
            "source2_exact_ordered_prefix": True,
            "greek_comparison_ordered_phrase": True,
            "same_number_greek_lacks_discriminating_motifs": True,
        }
        self.assertEqual(ordered_lexical_controls(3, c, g2, g4), expected)
        self.assertFalse(ordered_lexical_controls(
            3, ("ⲇⲉ", "ⲛⲑⲟⲕ", "ⲡ", "ϭⲟⲓⲥ"), g2, g4
        )["source2_exact_ordered_prefix"])
        self.assertFalse(ordered_lexical_controls(
            3, c, g2, ("κύριε", "σὺ", "δέ")
        )["greek_comparison_ordered_phrase"])

    def test_psalm_seventeen_same_words_reversed_are_not_positive_evidence(self):
        c = ("ⲡⲁ", "ⲣⲉϥϯ", "ⲉϩⲣⲏⲓ", "ⲉϫⲱ", "ⲓ")
        g2 = ("καὶ", "εἶπεν", "ἀγαπήσω", "σε")
        g3 = ("κύριος", "στερέωμά", "μου", "ὑπερασπιστής", "μου", "καὶ", "κέρας")
        self.assertTrue(all(ordered_lexical_controls(17, c, g2, g3).values()))
        self.assertFalse(ordered_lexical_controls(
            17, ("ⲣⲉϥϯ", "ⲡⲁ", "ⲉϩⲣⲏⲓ", "ⲉϫⲱ", "ⲓ"), g2, g3
        )["source2_exact_ordered_prefix"])
        self.assertFalse(ordered_lexical_controls(
            17, c, g2, ("κύριος", "μου", "ὑπερασπιστής", "καὶ", "κέρας")
        )["greek_comparison_ordered_phrase"])

    def test_psalm_fifty_one_source2_and_greek4_phrases_are_contiguous(self):
        c = ("ⲙ", "ⲫ", "ⲣⲏϯ", "ⲛ", "ⲟⲩ", "ⲑⲟⲕ", "ϣⲉⲃϣⲱⲃ")
        g2 = ("ἐν", "τῷ", "ἐλθεῖν", "Δωηκ")
        g4 = ("ἀδικίαν", "ἐλογίσατο", "ὡσεὶ", "ξυρὸν", "ἠκονημένον")
        self.assertTrue(all(ordered_lexical_controls(51, c, g2, g4).values()))
        self.assertFalse(ordered_lexical_controls(
            51, ("ⲙ", "ⲣⲏϯ", "ⲫ", "ⲛ", "ⲟⲩ"), g2, g4
        )["source2_exact_ordered_prefix"])
        self.assertFalse(ordered_lexical_controls(
            51, c, g2, ("ἀδικίαν", "ἐλογίσατο", "ξυρὸν", "ὡσεὶ")
        )["greek_comparison_ordered_phrase"])

    def test_punctuation_tokens_have_position_and_are_not_missing_words(self):
        c = ("ⲛⲑⲟⲕ", "ⲇⲉ", ".", "ⲡ", "ϭⲟⲓⲥ")
        g2 = ("Κύριε", "τί", "ἐπληθύνθησαν", ".")
        g4 = ("σὺ", "δέ", ",", "κύριε")
        self.assertTrue(all(ordered_lexical_controls(3, c, g2, g4).values()))
        self.assertFalse(ordered_lexical_controls(
            3, ("ⲛⲑⲟⲕ", ".", "ⲇⲉ", "ⲡ", "ϭⲟⲓⲥ"), g2, g4,
        )["source2_exact_ordered_prefix"])
        self.assertFalse(ordered_lexical_controls(
            3, c, g2, ("σὺ", ".", "δέ", "κύριε"),
        )["greek_comparison_ordered_phrase"])

    def test_curated_words_in_same_number_greek_invalidates_negative_control(self):
        c = ("ⲛⲑⲟⲕ", "ⲇⲉ", "ϭⲟⲓⲥ")
        g4 = ("σὺ", "δέ", "κύριε")
        self.assertFalse(ordered_lexical_controls(
            3, c, ("κύριε", "σὺ"), g4
        )["same_number_greek_lacks_discriminating_motifs"])


if __name__ == "__main__":
    unittest.main()
