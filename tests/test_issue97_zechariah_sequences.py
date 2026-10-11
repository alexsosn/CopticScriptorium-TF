"""RED-first independent Coptic Zechariah sequence and translation audit gates."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from tests.live_issue97_zechariah_sequences import (
    classify_cts, translation_tokens, normalized_tokens, compare_token_sequences,
    motif_score,
)


class ZechariahSourceSequenceContracts(unittest.TestCase):
    def test_only_exact_edition_qualified_zechariah_source(self):
        self.assertEqual(classify_cts("urn:cts:copticLit:ot.zach.bohairic_ed:01"), ("bohairic", 1))
        self.assertEqual(classify_cts("urn:cts:copticLit:ot.zech.coptot:2"), ("sahidic", 2))
        for bad in (
            "urn:cts:copticLit:ot.zech.bohairic_ed:2",
            "urn:cts:copticLit:ot.zach.coptot:2",
            "urn:cts:copticLit:nt.zach.bohairic_ed:2",
            "urn:cts:copticLit:ot.zach.bohairic_ed:2.1",
            "urn:cts:copticLit:ot.zach.bohairic_ed:2stuff",
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(classify_cts(bad))

    def test_translation_annotation_must_be_wholly_inside_the_same_verse(self):
        rows = [
            SimpleNamespace(text="A long test translation of the whole first verse",
                            word_ordinals=(1, 2, 3)),
            SimpleNamespace(text="Spans a verse boundary therefore unsuitable evidence",
                            word_ordinals=(3, 4)),
            SimpleNamespace(text="Other verse annotation is not evidence of this verse",
                            word_ordinals=(4, 5)),
        ]
        observed = translation_tokens((1, 2, 3), rows)
        self.assertEqual(observed, normalized_tokens(rows[0].text))
        self.assertEqual(translation_tokens((6, 7), rows), ())

    def test_identical_english_sequences_are_measurably_more_similar_than_unrelated(self):
        a = normalized_tokens("The prophet stood among the four horns before him")
        b = normalized_tokens("The prophet stood among the four horns before him")
        c = normalized_tokens("There were ships sailing over the wide eastern sea")
        perfect = compare_token_sequences(a, b)
        unrelated = compare_token_sequences(a, c)
        self.assertEqual(perfect["sequence_ratio"], 1.0)
        self.assertEqual(perfect["bigram_jaccard"], 1.0)
        self.assertLess(unrelated["bigram_jaccard"], perfect["bigram_jaccard"])
        self.assertIsNone(compare_token_sequences(("and", "i"), b))

    def test_missing_english_data_never_becomes_a_zero_similarity_diagnostic(self):
        self.assertIsNone(compare_token_sequences((), normalized_tokens("Several available words in another verse")))

    def test_semantic_content_anchor_distinguishes_two_recurrent_introductory_phrases(self):
        horns = normalized_tokens("And I lifted up mine eyes and beheld four horns")
        cord = normalized_tokens("And I lifted up mine eyes and behold a man holding a measuring line")
        self.assertEqual(motif_score(horns, 1), 1.0)
        self.assertEqual(motif_score(horns, 5), 0.0)
        self.assertEqual(motif_score(cord, 5), 1.0)
        self.assertEqual(motif_score(cord, 1), 0.0)
        self.assertIsNone(motif_score((), 1))
        with self.assertRaises(ValueError):
            motif_score(horns, 999)


if __name__ == "__main__":
    unittest.main()
