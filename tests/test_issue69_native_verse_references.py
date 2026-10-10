"""Issue #69 RED-first: preserve *source* verse reference literals in native TF.

These features are evidence for a later Coptic→CenterBLC/LXX mapping, not
assertions that matching verse numbers identify the same Greek passage.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric

COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(raw: str, *, path: str = "sahidic.ruth/sahidic.ruth_TT/Ruth_02.tt"):
    return parse_tt_record(
        raw.encode("utf-8"),
        source_record_id="sahidic.ruth/sahidic.ruth:Ruth_02",
        source_path=path,
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COMMIT,
    )


RUTH = (
    '<meta corpus="sahidic.ruth" chapter="2" document_cts_urn="urn:cts:copticLit:ot.ruth.coptot_ed:2">'
    '<verse_n verse_n="1">'
    '<vid_n vid_n="urn:cts:copticLit:ot.ruth.copto_edt:2.1">'
    '<verse_vid verse_vid="Ruth 2:1">'
    '<norm_group norm_group="a">'
    '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>'
    '</norm_group>'
    '<verse_n verse_n="2">'
    '<norm_group norm_group="b">'
    '<norm xml:id="u2" new_sent="true" func="root" pos="N" lemma="b" norm="b">b</norm>'
    '</norm_group>'
    '<vid_n vid_n="urn:cts:copticLit:ot.ruth.coptot_ed:2.2">'
    '<verse_vid verse_vid="Ruth 2:2">'
    '<norm_group norm_group="c">'
    '<norm xml:id="u3" new_sent="true" func="root" pos="N" lemma="c" norm="c">c</norm>'
    '</norm_group>'
)
JONAH = (
    '<meta corpus="sahidic.jonah" chapter="2">'
    '<verse_n verse_n="1">'
    '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm></norm_group>'
    '<verse_n verse_n="2">'
    '<norm_group norm_group="b"><norm xml:id="u2" new_sent="true" func="root" norm="b">b</norm></norm_group>'
)
UNMARKED = (
    '<meta corpus="other">'
    '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm></norm_group>'
)


class VerseReferencePreservationTests(unittest.TestCase):
    def test_ruth_preserves_distinct_exact_literals_and_resets_stale_cts(self):
        document = parse(RUTH)
        self.assertEqual(
            [(w.verse_n, w.vid_n, w.verse_vid) for w in document.words],
            [
                ("1", "urn:cts:copticLit:ot.ruth.copto_edt:2.1", "Ruth 2:1"),
                ("2", None, None),
                ("2", "urn:cts:copticLit:ot.ruth.coptot_ed:2.2", "Ruth 2:2"),
            ],
        )
        self.assertEqual(len(document.words), 3)
        self.assertEqual(document.metadata["chapter"], "2")

    def test_jonah_verse_only_and_absence_are_not_conflated(self):
        document = parse(JONAH)
        self.assertEqual([w.verse_n for w in document.words], ["1", "2"])
        self.assertEqual([w.vid_n for w in document.words], [None, None])
        self.assertEqual([w.verse_vid for w in document.words], [None, None])
        unmarked = parse(UNMARKED)
        self.assertIsNone(unmarked.words[0].verse_n)

    def test_token_internal_boundary_rejected_not_mapped_to_whole_word(self):
        bad = (
            '<meta corpus="sahidic.ruth" chapter="2">'
            '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" '
            'func="root" norm="a">a<verse_n verse_n="2">b</norm></norm_group>'
        )
        with self.assertRaisesRegex(ValueError, "verse marker.*inside norm"):
            parse(bad)

    def test_native_tf_preserves_raw_reference_without_new_slot_or_section_type(self):
        document = parse(RUTH)
        graph = build_graph([document])
        self.assertEqual(len(graph.slots), 3)
        self.assertEqual(graph.section_types, ("document",))
        self.assertEqual([s.verse_n for s in graph.slots], ["1", "2", "2"])
        with TemporaryDirectory() as root:
            target = Path(root) / "tf"
            write_graph(graph, target)
            for feature in ("verse_n.tf", "vid_n.tf", "verse_vid.tf"):
                self.assertTrue((target / feature).is_file(), feature)
            api = Fabric(locations=[str(target)], silent="deep").load(
                "norm verse_n vid_n verse_vid source_record_id", silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 3)
            self.assertEqual(api.F.verse_n.v(1), "1")
            self.assertEqual(api.F.verse_n.v(2), "2")
            self.assertEqual(api.F.vid_n.v(1), "urn:cts:copticLit:ot.ruth.copto_edt:2.1")
            self.assertIsNone(api.F.vid_n.v(2))
            self.assertEqual(api.F.verse_vid.v(3), "Ruth 2:2")
            self.assertEqual(len(api.F.otype.s("document")), 1)


if __name__ == "__main__":
    unittest.main()
