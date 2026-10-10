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

    def test_nested_reference_wrappers_before_first_visible_character_attach_to_current_word(self):
        # Genuine pinned coptic-treebank Mark 7 pattern: verse_vid and vid_n
        # can open inside norm under sbl_greek before the visible characters.
        markup = (
            '<meta corpus="coptic.treebank" book="Mark" chapter="7">'
            '<verse_n verse_n="16">'
            '<norm_group norm_group="[..]">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="[..]">'
            '<sbl_greek sbl_greek="…">'
            '<verse_vid verse_vid="41N 7:16">'
            '<vid_n vid_n="urn:cts:copticLit:nt.mark.sahidica_ed:7.16">'
            '[..]</vid_n></verse_vid></sbl_greek></norm>'
            '</norm_group></verse_n>'
        )
        parsed = parse(markup)
        self.assertEqual(len(parsed.words), 1)
        self.assertEqual(parsed.words[0].verse_n, "16")
        self.assertEqual(parsed.words[0].verse_vid, "41N 7:16")
        self.assertEqual(
            parsed.words[0].vid_n,
            "urn:cts:copticLit:nt.mark.sahidica_ed:7.16",
        )

    def test_closed_source_label_scopes_do_not_leak_to_following_words(self):
        markup = (
            '<meta corpus="sahidic.ruth" chapter="2">'
            '<verse_n verse_n="1">'
            '<verse_vid verse_vid="Ruth 2:1"><vid_n vid_n="urn:cts:copticLit:ot.ruth.coptot_ed:2.1">'
            '<norm_group norm_group="a"><norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm></norm_group>'
            '</vid_n></verse_vid>'
            '<norm_group norm_group="b"><norm xml:id="u2" new_sent="true" func="root" norm="b">b</norm></norm_group>'
            '</verse_n>'
            '<norm_group norm_group="c"><norm xml:id="u3" new_sent="true" func="root" norm="c">c</norm></norm_group>'
        )
        parsed = parse(markup)
        self.assertEqual(
            [(w.verse_n, w.vid_n, w.verse_vid) for w in parsed.words],
            [
                ("1", "urn:cts:copticLit:ot.ruth.coptot_ed:2.1", "Ruth 2:1"),
                ("1", None, None),
                (None, None, None),
            ],
        )

    def test_midword_verse_boundary_is_an_exact_native_event_not_a_forged_word_span(self):
        # Seen in the full pinned helias sources: a source marker can occur
        # *after* visible characters within an already opened norm token.
        markup = (
            '<meta corpus="helias" chapter="2">'
            '<norm_group norm_group="a">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'ab<verse_n verse_n="2">cd'
            '</norm></norm_group>'
            '<norm_group norm_group="b">'
            '<norm xml:id="u2" new_sent="true" func="root" norm="x">x</norm>'
            '</norm_group>'
        )
        document = parse(markup)
        self.assertEqual(len(document.words), 2)
        # Neither side of the split norm may be silently assigned a whole-word
        # Coptic verse address. The later clean word can inherit verse 2.
        self.assertIsNone(document.words[0].verse_n)
        self.assertEqual(document.words[1].verse_n, "2")
        events = [e for e in document.layout_events if e.kind == "verse_n_marker"]
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0].value, events[0].word_ordinal, events[0].char_offset),
                         ("2", 1, 2))
        graph = build_graph([document])
        self.assertEqual(len(graph.slots), 2)
        marker_nodes = [n for n in graph.nodes if n.otype == "verse_n_marker"]
        self.assertEqual(len(marker_nodes), 1)
        self.assertEqual(marker_nodes[0].label, "2")
        self.assertEqual(marker_nodes[0].start_char, 2)
        self.assertEqual(marker_nodes[0].slots, (1,))
        with TemporaryDirectory() as root:
            target = Path(root) / "tf"
            write_graph(graph, target)
            api = Fabric(locations=[str(target)], silent="deep").load(
                "norm verse_n label start_char source_record_id", silent="deep"
            )
            self.assertTrue(api)
            markers = api.F.otype.s("verse_n_marker")
            self.assertEqual(len(markers), 1)
            self.assertEqual(api.F.label.v(markers[0]), "2")
            self.assertEqual(api.F.start_char.v(markers[0]), 2)
            self.assertEqual(tuple(api.L.d(markers[0], otype="word")), (1,))
            self.assertEqual(api.F.verse_n.v(2), "2")

    def test_midword_multiple_reference_markers_keep_distinct_native_anchors(self):
        markup = (
            '<meta chapter="7">'
            '<norm_group norm_group="a">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'ab<verse_vid verse_vid="41N 7:16">'
            '<vid_n vid_n="urn:cts:copticLit:nt.mark.sahidica_ed:7.16">cd'
            '</vid_n></verse_vid></norm></norm_group>'
        )
        document = parse(markup)
        self.assertIsNone(document.words[0].vid_n)
        self.assertIsNone(document.words[0].verse_vid)
        events = [e for e in document.layout_events if e.kind.endswith("_marker")]
        self.assertEqual(
            [(e.kind, e.value, e.word_ordinal, e.char_offset) for e in events],
            [
                ("verse_vid_marker", "41N 7:16", 1, 2),
                ("vid_n_marker", "urn:cts:copticLit:nt.mark.sahidica_ed:7.16", 1, 2),
            ],
        )

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
