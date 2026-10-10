"""Native weft-only TF modules for Coptic↔LXX *verse-address candidates*.

Never infer Greek↔Coptic word correspondence or textual equivalence.
The modules annotate existing parent nodes with a stable shared reference ID;
TF integer node IDs are NOT transferable between corpus warps.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Sequence

from ._atomic import publish_path_no_clobber
from .lxx_reference import resolve_coptic_lxx_references
from .model import DocumentModel

COPTIC_UPSTREAM = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_UPSTREAM = "f32a98eddf7eb239aa73ab863d70381e416d5076"
LXX_VERSION = "1935"
LXX_MAX_SLOT = 623693
LXX_MAX_NODE = 685732
LXX_VERSES = 30371
MODULE_SCHEMA = "1"
# CATSS-TF v0.1 LXX parent profile: compare actual Git-blob hashes of the
# parent files, not only a user-supplied release label or node counts.
LXX_FINGERPRINTS = {
    "otype": "2e6480116dfda09f20e8de7c5b9feefa76322a96",
    "oslots": "e95696a6a49f1149f8f6e850f7dfb40a26509931",
    "book": "0bfae94bb312cb7ecd33b102babb9400c554d8be",
    "chapter": "ec64b6bf72a6282e9da5064ca2e895171190208e",
    "verse": "ff8766352d7aff530c6eec4f66366adcc691740e",
    "subverse": "cecfaf2d1ddc4fd1e93958abd674a7e60e676ae5",
    "word": "f88e525991c3d09beac713a91ef8ed41e6308a03",
    "orig_order": "0d0339af8a512a0a59232fbccb309fc229da6ddd",
}
FEATURE_SPECS = {
    ("coptic", "coptic_lxx_ref_id"): "str",
    ("coptic", "coptic_lxx_ref_status"): "str",
    ("lxx", "coptic_lxx_ref_id"): "str",
    ("lxx", "coptic_lxx_source_span_count"): "int",
}


class LxxModuleError(ValueError):
    """An input, reference, trust, or schema contract failed closed."""


def git_blob_sha(path: Path) -> str:
    """Git's exact 'blob' object hash, not the raw-file SHA-1."""
    payload = Path(path).read_bytes()
    return sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def validate_lxx_release(tf_dir: Path, api: Any) -> None:
    """Reject a wrong parent despite matching book/chapter/verse strings."""
    for name, expected in LXX_FINGERPRINTS.items():
        path = Path(tf_dir) / f"{name}.tf"
        if not path.is_file() or path.is_symlink():
            raise LxxModuleError(f"missing/invalid pinned LXX feature {name}.tf")
        actual = git_blob_sha(path)
        if actual != expected:
            raise LxxModuleError(
                f"CenterBLC/LXX fingerprint mismatch {name}.tf: {actual} != {expected}"
            )
    if (
        api.F.otype.maxSlot != LXX_MAX_SLOT
        or api.F.otype.maxNode != LXX_MAX_NODE
        or len(api.F.otype.s("verse")) != LXX_VERSES
    ):
        raise LxxModuleError("LXX node/verse counts do not match exact pinned profile")


def render_node_feature(
    name: str,
    values: dict[int, str | int],
    *,
    value_type: str,
    projection: str,
    description: str,
) -> bytes:
    """Render a native TF node feature, without creating another warp."""
    expected = FEATURE_SPECS.get((projection, name))
    if expected is None or value_type != expected:
        raise LxxModuleError(f"unrecognized node feature/projection: {projection}/{name}")
    if not description or any(char in description for char in "\r\n\t"):
        raise LxxModuleError("feature description must be one non-empty plain line")
    lines = [
        "@node",
        f"@valueType={value_type}",
        f"@description={description}",
        f"@copticLxxRefSchema={MODULE_SCHEMA}",
        f"@projection={projection}",
        f"@copticUpstreamCommit={COPTIC_UPSTREAM}",
        f"@lxxParentCommit={LXX_UPSTREAM}",
        f"@lxxParentVersion={LXX_VERSION}",
        "@mappingStatus=reference-address-candidate-not-textual-equivalence",
        "",
    ]
    for node, value in sorted(values.items()):
        if not isinstance(node, int) or isinstance(node, bool) or node < 1:
            raise LxxModuleError(f"invalid parent node identifier {node!r}")
        if projection == "lxx" and node > LXX_MAX_NODE:
            raise LxxModuleError(f"Greek parent node {node} exceeds pinned warp")
        if value_type == "int":
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise LxxModuleError(f"invalid positive-count feature value {value!r}")
        elif not isinstance(value, str) or not value or any(c in value for c in "\n\r\t"):
            raise LxxModuleError(f"invalid scalar TF value for {name}/{node}")
        lines.append(f"{node}\t{value}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_reference_modules(
    destination: Path,
    *,
    coptic_ref: dict[int, str],
    coptic_status: dict[int, str],
    lxx_ref: dict[int, str],
    lxx_count: dict[int, int],
) -> Path:
    """Atomically publish both additive modules, never overwrite any output."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"reference module bundle exists: {destination}")
    if set(coptic_ref) - set(coptic_status):
        raise LxxModuleError("source word reference lacks a candidate status")
    for node, status in coptic_status.items():
        if status not in {
            "reference_candidate", "unresolved", "ambiguous", "unclassified_corpus"
        }:
            raise LxxModuleError(f"unsupported Coptic reference status {node}/{status}")
    if set(lxx_ref) != set(lxx_count):
        raise LxxModuleError("Greek reference/count node keysets differ")
    if set(lxx_ref.values()) != set(coptic_ref.values()):
        raise LxxModuleError("Greek references differ from Coptic candidate references")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".coptic-lxx-modules-", dir=destination.parent) as tmp:
        stage = Path(tmp) / "module-bundle"
        (stage / "coptic").mkdir(parents=True)
        (stage / "lxx").mkdir()
        feature_files = (
            ("coptic", "coptic_lxx_ref_id", coptic_ref,
             "Coptic word to edition-qualified Greek verse-address candidate"),
            ("coptic", "coptic_lxx_ref_status", coptic_status,
             "Coptic source reference status not textual equivalence"),
            ("lxx", "coptic_lxx_ref_id", lxx_ref,
             "Greek parent verse anchor for Coptic source address candidates"),
            ("lxx", "coptic_lxx_source_span_count", lxx_count,
             "Number of candidate Coptic source word spans at this verse address"),
        )
        for projection, name, data, description in feature_files:
            encoded = render_node_feature(
                name, data, value_type=FEATURE_SPECS[(projection, name)],
                projection=projection, description=description,
            )
            (stage / projection / f"{name}.tf").write_bytes(encoded)
        publish_path_no_clobber(stage, destination)
    return destination


def project_reference_modules(
    documents: Sequence[DocumentModel],
    *,
    coptic_api: Any,
    lxx_api: Any,
    lxx_tf_dir: Path,
    destination: Path,
) -> dict[str, int]:
    """Validate parent node identities; project strictly to their own warps.

    Caller supplies an existing Coptic Text-Fabric corpus containing the exact
    physical TT records and a freshly loaded pinned CenterBLC/LXX parent.
    """
    validate_lxx_release(lxx_tf_dir, lxx_api)
    refs_coptic: dict[int, str] = {}
    statuses: dict[int, str] = {}
    refs_lxx: dict[int, str] = {}
    counts_lxx: Counter[int] = Counter()
    summary: Counter[str] = Counter()
    seen_records: set[str] = set()

    def greek_verse(book: str, chapter: int, verse: int) -> int | None:
        node = lxx_api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        if lxx_api.F.otype.v(node) != "verse":
            raise LxxModuleError(f"Greek target {book} {chapter}:{verse} is not a verse node")
        return node

    for document in documents:
        if document.source_record_id in seen_records:
            raise LxxModuleError(f"duplicate physical source document {document.source_record_id}")
        seen_records.add(document.source_record_id)
        if document.upstream_repository != "CopticScriptorium/corpora" or document.upstream_commit != COPTIC_UPSTREAM:
            raise LxxModuleError("Coptic source does not match pinned upstream identity")

        parent = coptic_api.T.nodeFromSection((document.source_record_id,))
        if parent is None or coptic_api.F.otype.v(parent) != "document":
            raise LxxModuleError(f"Coptic parent is missing real source record {document.source_record_id}")
        if coptic_api.F.source_sha256.v(parent) != document.source_sha256:
            raise LxxModuleError(f"Coptic parent has different source bytes: {document.source_record_id}")
        parent_words = tuple(coptic_api.L.d(parent, otype="word"))
        if len(parent_words) != len(document.words):
            raise LxxModuleError(f"Coptic parent word count differs: {document.source_record_id}")
        local_to_node: dict[int, int] = {}
        for word, node in zip(document.words, parent_words):
            if (
                coptic_api.F.source_record_id.v(node) != document.source_record_id
                or coptic_api.F.source_word_ordinal.v(node) != word.ordinal
                or coptic_api.F.norm.v(node) != word.norm
            ):
                raise LxxModuleError(f"Coptic source word identity mismatch {document.source_record_id}:{word.ordinal}")
            local_to_node[word.ordinal] = node

        for ref in resolve_coptic_lxx_references(document, lookup=greek_verse):
            summary[ref.status] += 1
            for word_ordinal in ref.source_word_ordinals:
                node = local_to_node[word_ordinal]
                if node in statuses:
                    raise LxxModuleError(f"one Coptic word belongs to multiple source reference spans: {node}")
                statuses[node] = ref.status
                if ref.status == "reference_candidate":
                    assert ref.shared_id is not None and ref.lxx_node is not None
                    refs_coptic[node] = ref.shared_id
            if ref.status == "reference_candidate":
                assert ref.shared_id is not None and ref.lxx_node is not None
                old = refs_lxx.setdefault(ref.lxx_node, ref.shared_id)
                if old != ref.shared_id:
                    raise LxxModuleError(f"Greek verse node collision: {ref.lxx_node}")
                counts_lxx[ref.lxx_node] += 1

    if not refs_coptic or not refs_lxx:
        raise LxxModuleError("no resolved verse-address candidates; refuse empty module")
    write_reference_modules(
        destination,
        coptic_ref=refs_coptic, coptic_status=statuses,
        lxx_ref=refs_lxx, lxx_count=dict(counts_lxx),
    )
    return {
        **dict(summary),
        "candidate_coptic_word_nodes": len(refs_coptic),
        "candidate_lxx_verse_nodes": len(refs_lxx),
        "coptic_annotated_word_nodes": len(statuses),
    }
