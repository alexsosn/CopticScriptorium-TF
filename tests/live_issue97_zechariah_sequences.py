"""Independent real Zechariah edition/translation-sequence diagnostic (#97).

Computes bounded comparisons in memory from immutable source bytes. No
mapping change, no source export, no claim of textual equivalence. The two
Coptic translations may have different editorial provenance and coverage.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Sequence
from zipfile import ZipFile
import json
import re
import sys

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
OT_ZIPS = (
    "sahidic.ot/sahidic.ot_TT.zip",
    "bohairic.ot/bohairic.ot_TT.zip",
)
# Explicit matching of work, edition AND chapter; no regex substring of a name.
CTS_WORK = re.compile(r"^urn:cts:copticLit:ot\.(zach\.bohairic_ed|zech\.coptot):(\d+)$")
WORDS = re.compile(r"[^\W_]+", flags=re.UNICODE)


def classify_cts(cts: str | None) -> tuple[str, int] | None:
    match = CTS_WORK.fullmatch(cts or "")
    if match is None:
        return None
    chapter = int(match[2])
    if chapter < 1:
        return None
    return ("bohairic" if match[1] == "zach.bohairic_ed" else "sahidic", chapter)


def normalized_tokens(text: str) -> tuple[str, ...]:
    return tuple(x.casefold() for x in WORDS.findall(text))


def translation_tokens(ordinals: tuple[int, ...], translations: Sequence) -> tuple[str, ...]:
    """Only use entire verse-local translation spans; reject cross-verse snippets.

    Note: source English translations may be misaligned to Coptic; this is
    *diagnostic evidence*, never certification.
    """
    verse_words = set(ordinals)
    if not verse_words:
        return ()
    accepted = []
    for entry in translations:
        locus = set(entry.word_ordinals)
        if locus and locus <= verse_words:
            accepted.append((min(locus), entry.ordinal if hasattr(entry, "ordinal") else 0, entry.text))
    return normalized_tokens(" ".join(t for _start, _ordinal, t in sorted(accepted)))


def compare_token_sequences(left: tuple[str, ...], right: tuple[str, ...]) -> dict[str, float] | None:
    if min(len(left), len(right)) < 6:
        return None
    a = set(zip(left, left[1:]))
    b = set(zip(right, right[1:]))
    union = a | b
    return {
        "bigram_jaccard": round(len(a & b) / len(union), 3) if union else 0.0,
        "sequence_ratio": round(SequenceMatcher(None, left, right, autojunk=False).ratio(), 3),
    }


@dataclass(frozen=True)
class VerseEvidence:
    witness: str
    chapter: int
    verse: int
    source_record_id: str
    coptic_words: tuple[str, ...]
    english_words: tuple[str, ...]
    english_source: str
    greek_node: int | None


def _load_verses(root: Path, greek_api) -> tuple[dict[tuple[str, int, int], VerseEvidence], Counter]:
    evidence: dict[tuple[str, int, int], VerseEvidence] = {}
    counts: Counter = Counter()
    for rel in OT_ZIPS:
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing pinned Coptic OT archive: {rel}")
        corpus = rel.split("/", 1)[0]
        dataset = Path(rel).name.removesuffix("_TT.zip")
        with ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir() or not member.filename.endswith(".tt"):
                    continue
                raw = archive.read(member)
                if not raw.startswith(b"<meta "):
                    continue
                match = re.search(rb'\bdocument_cts_urn="([^"]+)"', raw.split(b">", 1)[0])
                qualified = classify_cts(match[1].decode("utf-8") if match else None)
                if qualified is None:
                    continue
                witness, chapter = qualified
                # Zechariah boundary, not arbitrary source works or book chapters.
                if chapter not in (1, 2):
                    continue
                record = Path(member.filename).stem
                document = parse_tt_record(
                    raw,
                    source_record_id=f"{corpus}/{dataset}:{record}",
                    source_path=f"{rel}!{member.filename}",
                    upstream_repository="CopticScriptorium/corpora",
                    upstream_commit=COPTIC_PIN,
                    packaging="archive",
                )
                if document.metadata.get("chapter") is None or int(document.metadata["chapter"]) != chapter:
                    raise ValueError(f"chapter metadata contradicts exact edition CTS: {document.source_record_id}")
                counts[f"{witness}_source_documents"] += 1
                for ref in resolve_coptic_lxx_references(
                    document, lookup=lambda b,c,v: greek_api.T.nodeFromSection((b,c,v))
                ):
                    if not ref.source_verse_n or not ref.source_verse_n.isascii() or not ref.source_verse_n.isdecimal():
                        counts["unpositioned_verse_spans"] += 1
                        continue
                    verse = int(ref.source_verse_n)
                    if not (15 <= verse <= 21 if chapter == 1 else 1 <= verse <= 10):
                        continue
                    key = (witness, chapter, verse)
                    if key in evidence:
                        raise ValueError(f"duplicate verse in exact CTS edition: {key}")
                    word_ids = ref.source_word_ordinals
                    eng = translation_tokens(word_ids, document.translations)
                    words = tuple((document.words[w - 1].norm or "") for w in word_ids)
                    evidence[key] = VerseEvidence(
                        witness=witness, chapter=chapter, verse=verse,
                        source_record_id=document.source_record_id,
                        coptic_words=words,
                        english_words=eng,
                        english_source=document.metadata.get("translation") or "",
                        greek_node=ref.lxx_node,
                    )
                    counts[f"{witness}_verses"] += 1
    return evidence, counts


def _pair(
    verses: dict[tuple[str, int, int], VerseEvidence],
    left: tuple[str, int, int],
    right: tuple[str, int, int],
    *,
    hypothesis: str,
) -> dict[str, object]:
    x = verses.get(left)
    y = verses.get(right)
    if not x or not y:
        return {"hypothesis": hypothesis, "left": list(left), "right": list(right), "present": False}
    return {
        "hypothesis": hypothesis,
        "left": list(left),
        "right": list(right),
        "present": True,
        "left_coptic_words": len(x.coptic_words),
        "right_coptic_words": len(y.coptic_words),
        "left_english_words": len(x.english_words),
        "right_english_words": len(y.english_words),
        "english_comparison": compare_token_sequences(x.english_words, y.english_words),
        # Safe exactly one-witness Coptic dialect comparison; do not equate
        # it with Greek/Coptic textual equivalence.
        "coptic_comparison": compare_token_sequences(
            normalized_tokens(" ".join(x.coptic_words)),
            normalized_tokens(" ".join(y.coptic_words)),
        ) if x.witness == y.witness else None,
    }


def run(coptic_root: Path, greek_root: Path) -> None:
    verify_lxx_parent_feature_blobs(greek_root)
    api = Fabric(locations=[str(greek_root)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if not api or api.F.otype.maxSlot != 623693 or len(api.F.otype.s("verse")) != 30371:
        raise ValueError("mismatched pinned Greek Text-Fabric parent")
    verses, counts = _load_verses(coptic_root, api)
    required = [("bohairic", 1, v) for v in range(18, 22)]
    required += [("bohairic", 2, v) for v in range(1, 7)]
    required += [("sahidic", 2, v) for v in (1, 2)]
    if any(k not in verses for k in required):
        raise ValueError(f"missing real Coptic boundary evidence: {[x for x in required if x not in verses]}")

    pairs: list[dict[str, object]] = []
    for verse in range(18, 22):
        pairs.append(_pair(verses, ("bohairic",1,verse), ("sahidic",2,verse-17),
                           hypothesis="Boh 1:18..21 ~ Sah/LXX 2:1..4"))
    for verse in range(1, 7):
        pairs.append(_pair(verses, ("bohairic",2,verse), ("sahidic",2,verse+4),
                           hypothesis="Boh 2:1..6 ~ Sah/LXX 2:5..10"))
        pairs.append(_pair(verses, ("bohairic",2,verse), ("sahidic",2,verse),
                           hypothesis="Boh 2:v ~ Sah/LXX 2:v (competing same-number candidate)"))
    for verse in range(1, 5):
        pairs.append(_pair(verses, ("bohairic",1,verse+17), ("bohairic",2,verse),
                           hypothesis="Boh chapter-tail vs chapter-head internal duplication control"))
    summary = {
        "coptic_pin": COPTIC_PIN,
        "lxx_pin": LXX_PIN,
        "edition_cts_strict": True,
        "counts": dict(sorted(counts.items())),
        "greek_verse_exists": {
            f"Zech 2:{verse}": bool(api.T.nodeFromSection(("Zech",2,verse)))
            for verse in range(1,11)
        },
        "verse_evidence": [
            {"edition": k[0], "chapter": k[1], "verse": k[2],
             "source": v.source_record_id,
             "english_words": len(v.english_words),
             "coptic_words": len(v.coptic_words),
             "translation_source": v.english_source[:85],
             "greek_same_reference_found": bool(v.greek_node)}
            for k, v in sorted(verses.items())
        ],
        "comparisons": pairs,
        "status": "diagnostic only, no Greek/Coptic passage equivalence certified",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print("PASS pinned exact CTS Zechariah real-sequence diagnostic; no crosswalk published")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue97_zechariah_sequences.py COPTIC_ROOT LXX_TF")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
