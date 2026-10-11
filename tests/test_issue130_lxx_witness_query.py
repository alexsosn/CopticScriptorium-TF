"""RED first: Coptic↔LXX dual native TF inverse reference *candidates* (#130)."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from copticscriptorium_tf.lxx_query import find_coptic_witnesses, LxxWitnessQueryError


class Feature:
    def __init__(self, data):
        self.data = dict(data)

    def v(self, node):
        return self.data.get(node)

    def s(self, value):
        return tuple(n for n, v in self.data.items() if v == value)


def fake_coptic(*, wrong_status=None, ref=None):
    target = ref or "CenterBLC/LXX:1935:Ruth:2:1"
    ids = {10: target, 11: target, 20: target, 21: target}
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=Feature({10: "word", 11: "word", 20: "word", 21: "word"}),
            coptic_lxx_ref_id=Feature(ids),
            coptic_lxx_ref_status=Feature({
                10: "reference_candidate",
                11: wrong_status or "reference_candidate",
                20: "reference_candidate",
                21: "reference_candidate",
            }),
            source_record_id=Feature({
                10: "sahidic.ruth/sahidic.ruth:Ruth_02",
                11: "sahidic.ruth/sahidic.ruth:Ruth_02",
                20: "bohairic.ot/bohairic.ot:08_Ruth_02",
                21: "bohairic.ot/bohairic.ot:08_Ruth_02",
            }),
            source_word_ordinal=Feature({10: 1, 11: 2, 20: 8, 21: 9}),
        ),
    )


def fake_lxx(*, ref="CenterBLC/LXX:1935:Ruth:2:1", declared=2, otype="verse", node=663156):
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=Feature({663156: otype}),
            coptic_lxx_ref_id=Feature({663156: ref}),
            coptic_lxx_source_span_count=Feature({663156: declared}),
        ),
        T=SimpleNamespace(nodeFromSection=lambda address: node if address == ("Ruth", 2, 1) else None),
    )


class NativeCopticLxxInverseLookupTests(unittest.TestCase):
    def test_two_physical_witnesses_are_kept_distinct_and_sorted_by_source(self):
        result = find_coptic_witnesses(fake_coptic(), fake_lxx(), "Ruth", 2, 1)
        self.assertEqual(result.lxx_node, 663156)
        self.assertEqual(result.shared_id, "CenterBLC/LXX:1935:Ruth:2:1")
        self.assertEqual(result.declared_coptic_source_span_count, 2)
        self.assertEqual(len(result.spans), 2)
        self.assertEqual([s.source_record_id for s in result.spans], [
            "bohairic.ot/bohairic.ot:08_Ruth_02",
            "sahidic.ruth/sahidic.ruth:Ruth_02",
        ])
        self.assertEqual(result.spans[0].word_nodes, (20, 21))
        self.assertEqual(result.spans[1].source_word_ordinals, (1, 2))
        self.assertEqual(
            [s.status for s in result.spans], ["reference_candidate", "reference_candidate"]
        )

    def test_missing_verse_or_wrong_edition_lxx_feature_fails_closed(self):
        with self.assertRaisesRegex(LxxWitnessQueryError, "no LXX verse"):
            find_coptic_witnesses(fake_coptic(), fake_lxx(node=None), "Ruth", 2, 1)
        with self.assertRaisesRegex(LxxWitnessQueryError, "shared reference"):
            find_coptic_witnesses(
                fake_coptic(), fake_lxx(ref="CenterBLC/LXX:1934:Ruth:2:1"), "Ruth", 2, 1
            )
        with self.assertRaisesRegex(LxxWitnessQueryError, "not a verse"):
            find_coptic_witnesses(fake_coptic(), fake_lxx(otype="word"), "Ruth", 2, 1)

    def test_rejects_wrong_status_invalid_count_and_missing_source_weft(self):
        with self.assertRaisesRegex(LxxWitnessQueryError, "status"):
            find_coptic_witnesses(
                fake_coptic(wrong_status="ambiguous"), fake_lxx(), "Ruth", 2, 1
            )
        with self.assertRaisesRegex(LxxWitnessQueryError, "span count"):
            find_coptic_witnesses(fake_coptic(), fake_lxx(declared=-1), "Ruth", 2, 1)
        coptic = fake_coptic()
        delattr(coptic.F, "coptic_lxx_ref_id")
        with self.assertRaisesRegex(LxxWitnessQueryError, "missing Coptic.*module"):
            find_coptic_witnesses(coptic, fake_lxx(), "Ruth", 2, 1)

    def test_source_locked_bilateral_weft_has_no_optional_greek_span_count(self):
        # The current source-locked lxx_module.py emitter (including its
        # streaming full-corpus path) writes a Greek reference-ID feature,
        # but DOES NOT write the older lxx_modules.py count feature.
        # A query must still work on that provenance-validated module.
        greek = fake_lxx()
        delattr(greek.F, "coptic_lxx_source_span_count")
        result = find_coptic_witnesses(fake_coptic(), greek, "Ruth", 2, 1)
        self.assertIsNone(result.declared_coptic_source_span_count)
        self.assertEqual(len(result.spans), 2)

    def test_discontinuous_word_runs_in_one_witness_stay_distinct(self):
        c = fake_coptic()
        c.F.source_word_ordinal = Feature({10: 1, 11: 4, 20: 8, 21: 9})
        result = find_coptic_witnesses(c, fake_lxx(declared=3), "Ruth", 2, 1)
        self.assertEqual(len(result.spans), 3)
        self.assertEqual([s.source_word_ordinals for s in result.spans], [
            (8, 9), (1,), (4,)
        ])

    def test_duplicate_source_ordinal_or_nonword_candidate_rejected(self):
        c = fake_coptic()
        c.F.source_word_ordinal = Feature({10: 1, 11: 1, 20: 8, 21: 9})
        with self.assertRaisesRegex(LxxWitnessQueryError, "duplicate"):
            find_coptic_witnesses(c, fake_lxx(), "Ruth", 2, 1)
        c = fake_coptic()
        c.F.otype = Feature({10: "word", 11: "verse", 20: "word", 21: "word"})
        with self.assertRaisesRegex(LxxWitnessQueryError, "non-word"):
            find_coptic_witnesses(c, fake_lxx(), "Ruth", 2, 1)

    def test_no_coptic_candidate_despite_greek_positive_count_is_inconsistent(self):
        c = fake_coptic(ref="CenterBLC/LXX:1935:Ruth:2:2")
        with self.assertRaisesRegex(LxxWitnessQueryError, "no Coptic"):
            find_coptic_witnesses(c, fake_lxx(), "Ruth", 2, 1)

    def test_versification_candidate_keeps_label_and_never_claims_word_equivalence(self):
        c = fake_coptic()
        c.F.coptic_lxx_ref_status = Feature({
            10: "versification_candidate", 11: "versification_candidate",
            20: "reference_candidate", 21: "reference_candidate",
        })
        result = find_coptic_witnesses(c, fake_lxx(), "Ruth", 2, 1)
        self.assertEqual([s.status for s in result.spans], [
            "reference_candidate", "versification_candidate"
        ])
        self.assertIn("not", result.interpretation)


    def test_actual_native_tf_weft_inverse_index_and_physical_source(self):
        # Unlike mocked Feature.s(), this tests the inverse index implemented
        # by Text-Fabric itself on a real, generated source warp + additive
        # Coptic weft (no copied/synthetic Coptic↔Greek node identities).
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tf.fabric import Fabric
        from copticscriptorium_tf.parser import parse_tt_record
        from copticscriptorium_tf.graph import build_graph
        from copticscriptorium_tf.writer import write_graph
        from copticscriptorium_tf.lxx_modules import write_reference_modules

        raw = (
            '<meta corpus="sahidic.ruth" chapter="2">'
            '<verse_n verse_n="1">'
            '<norm_group norm_group="ab">'
            '<norm xml:id="w1" new_sent="true" func="root" norm="a">a</norm>'
            '<norm xml:id="w2" func="dep" head="#w1" norm="b">b</norm>'
            '</norm_group>'
        )
        document = parse_tt_record(
            raw.encode("utf-8"),
            source_record_id="sahidic.ruth/sahidic.ruth:Ruth_02",
            source_path="sahidic.ruth/sahidic.ruth_TT/Ruth_02.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
        )
        shared = "CenterBLC/LXX:1935:Ruth:2:1"
        with TemporaryDirectory() as tmp:
            parent = Path(tmp) / "coptic-tf"
            write_graph(build_graph((document,)), parent)
            module_root = Path(tmp) / "wefts"
            write_reference_modules(
                module_root,
                coptic_ref={1: shared, 2: shared},
                coptic_status={1: "reference_candidate", 2: "reference_candidate"},
                lxx_ref={663156: shared},
                lxx_count={663156: 1},
            )
            api = Fabric(
                locations=[str(parent), str(module_root / "coptic")], silent="deep"
            ).load(
                "source_record_id source_word_ordinal coptic_lxx_ref_id "
                "coptic_lxx_ref_status", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(tuple(api.F.coptic_lxx_ref_id.s(shared)), (1, 2))
            result = find_coptic_witnesses(api, fake_lxx(declared=1), "Ruth", 2, 1)
            self.assertEqual(len(result.spans), 1)
            self.assertEqual(result.spans[0].word_nodes, (1, 2))
            self.assertEqual(result.spans[0].source_word_ordinals, (1, 2))


if __name__ == "__main__":
    unittest.main()
