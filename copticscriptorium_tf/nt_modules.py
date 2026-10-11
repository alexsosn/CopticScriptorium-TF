"""Coptic-owned additive native TF reference wefts for Coptic SBL ↔ Greek NT.

Only this repository owns/writes either module. The pinned Greek NT parent is
read-only and no independent corpus warp is changed or redistributed.
Foreign TF node numbers are local map keys, never feature *values*.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1, sha256
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from ._atomic import publish_path_no_clobber
from .nt_reference import GREEK_NT_EDITION, REVIEWED_SOURCES, COPTIC_PIN, resolve_coptic_sbl_references
from .model import DocumentModel
from typing import Any, Sequence

SCHEMA = "1"
FEATURE_TYPES = {
    ("coptic", "coptic_nt_ref_id"): "str",
    ("coptic", "coptic_nt_ref_status"): "str",
    ("greek", "coptic_nt_ref_id"): "str",
    ("greek", "coptic_nt_source_occurrence_count"): "int",
}
VALID_STATUSES = frozenset((
    "reference_candidate", "ambiguous", "unresolved",
    "edition_unavailable", "unclassified_source",
))
PARENT_FEATURES = {
    "coptic": (
        "otype", "oslots", "source_record_id", "source_ordinal",
        "value", "sbl_verse_n", "source_sha256", "render_mode",
    ),
    "greek": ("otype", "oslots", "book", "chapter", "verse"),
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ALLOWED_BOOKS = {entry[0] for entry in REVIEWED_SOURCES.values()}


class NtModuleError(ValueError):
    """Source, target parent, native weft or provenance contract violation."""


def parent_fingerprints(tf_dir: Path, projection: str) -> dict[str, str]:
    """Hash exact parent feature bytes; modules cannot safely cross TF warps."""
    if projection not in PARENT_FEATURES:
        raise NtModuleError("unknown parent projection")
    result = {}
    for feature in PARENT_FEATURES[projection]:
        path = Path(tf_dir) / f"{feature}.tf"
        if not path.is_file() or path.is_symlink():
            raise NtModuleError(f"missing/invalid TF parent feature {feature}")
        result[feature] = sha256(path.read_bytes()).hexdigest()
    return result


def _validate_proof(proof) -> None:
    if not isinstance(proof, dict) or set(proof) != set(PARENT_FEATURES):
        raise NtModuleError("parent fingerprint projections mismatch")
    for projection, required in PARENT_FEATURES.items():
        actual = proof[projection]
        if not isinstance(actual, dict) or set(actual) != set(required):
            raise NtModuleError("incomplete parent fingerprint inventory")
        if any(not isinstance(v, str) or not _HEX.fullmatch(v) for v in actual.values()):
            raise NtModuleError("invalid parent fingerprint digest")


def _valid_node(node) -> bool:
    return isinstance(node, int) and not isinstance(node, bool) and node > 0


def _valid_ref(ref) -> bool:
    if not isinstance(ref, str) or not ref.startswith(GREEK_NT_EDITION + ":"):
        return False
    rest = ref[len(GREEK_NT_EDITION) + 1:]
    parts = rest.split(":")
    return (
        len(parts) == 3 and parts[0] in _ALLOWED_BOOKS
        and all(part.isascii() and part.isdecimal() and int(part) > 0 for part in parts[1:])
    )


def render_node_feature(
    name: str, values: dict[int, str | int], *,
    projection: str, parent_proof: dict[str, dict[str, str]],
    description: str,
) -> bytes:
    """Render one native sparse TF node feature, with immutable parent proof."""
    value_type = FEATURE_TYPES.get((projection, name))
    if value_type is None:
        raise NtModuleError("unrecognized native NT feature/projection")
    _validate_proof(parent_proof)
    if not description or any(c in description for c in "\r\n\t"):
        raise NtModuleError("invalid native TF feature description")
    lines = [
        "@node",
        f"@valueType={value_type}",
        f"@description={description}",
        f"@copticNtRefSchema={SCHEMA}",
        f"@projection={projection}",
        "@mappingStatus=verse-address-candidate-not-textual-or-word-alignment",
        f"@greekEdition={GREEK_NT_EDITION}",
    ]
    for parent, features in PARENT_FEATURES.items():
        for feature in features:
            lines.append(
                f"@{parent}Parent{feature[0].upper() + feature[1:]}Sha256="
                f"{parent_proof[parent][feature]}"
            )
    lines.append("")
    for node, value in sorted(values.items()):
        if not _valid_node(node):
            raise NtModuleError("invalid parent node identifier")
        if value_type == "int":
            if not _valid_node(value):
                raise NtModuleError("invalid source occurrence count")
        elif not isinstance(value, str) or not value or any(c in value for c in "\n\r\t"):
            raise NtModuleError("invalid scalar native TF reference/status")
        lines.append(f"{node}\t{value}")
    return ("\n".join(lines) + "\n").encode("utf-8")



def validate_native_module_parent(
    module_dir: Path, *, projection: str,
    coptic_tf_dir: Path, greek_tf_dir: Path,
) -> None:
    """Reject any module reused against another warp OR altered SBL evidence.

    Checking only otype/oslots would miss a changed source Greek annotation,
    source verse marker, source record or SBL span classification with the
    same node IDs. Match all source-critical Coptic feature hashes as well.
    """
    if projection not in PARENT_FEATURES:
        raise NtModuleError("unknown native NT module projection")
    module_dir = Path(module_dir)
    expected_names = {
        name for parent, name in FEATURE_TYPES if parent == projection
    }
    actual_names = {
        path.stem for path in module_dir.iterdir()
        if path.is_file() and path.suffix == ".tf" and not path.is_symlink()
    } if module_dir.is_dir() and not module_dir.is_symlink() else set()
    if actual_names != expected_names:
        raise NtModuleError("native NT module feature inventory mismatch")
    proof = {
        "coptic": parent_fingerprints(coptic_tf_dir, "coptic"),
        "greek": parent_fingerprints(greek_tf_dir, "greek"),
    }
    for feature in expected_names:
        path = module_dir / f"{feature}.tf"
        headers = {}
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                line = line.rstrip("\n")
                if not line:
                    break
                if line.startswith("@") and "=" in line:
                    key, value = line.split("=", 1)
                    if key in headers:
                        raise NtModuleError("duplicate module provenance metadata")
                    headers[key] = value
        if (headers.get("@copticNtRefSchema") != SCHEMA
            or headers.get("@projection") != projection
            or headers.get("@greekEdition") != GREEK_NT_EDITION):
            raise NtModuleError("native NT module schema/projection mismatch")
        for parent, features in PARENT_FEATURES.items():
            for name in features:
                key = f"@{parent}Parent{name[0].upper() + name[1:]}Sha256"
                if headers.get(key) != proof[parent][name]:
                    raise NtModuleError("native NT module parent fingerprint mismatch")

def write_nt_modules(
    destination: Path, *,
    coptic_ref: dict[int, str],
    coptic_status: dict[int, str],
    greek_ref: dict[int, str],
    greek_count: dict[int, int],
    parent_proof: dict[str, dict[str, str]],
) -> Path:
    """Publish both weft-only modules atomically, reject any preexisting target."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"NT modules already exist: {destination}")
    _validate_proof(parent_proof)
    if set(coptic_ref) - set(coptic_status):
        raise NtModuleError("Coptic candidate reference lacks a source status")
    if any(not _valid_node(node) for node in set(coptic_ref) | set(coptic_status)):
        raise NtModuleError("invalid source node ID")
    if any(status not in VALID_STATUSES for status in coptic_status.values()):
        raise NtModuleError("invalid Coptic reference status")
    if any(coptic_status[node] != "reference_candidate" for node in coptic_ref):
        raise NtModuleError("Coptic reference with noncandidate status")
    if any(status == "reference_candidate" and node not in coptic_ref
           for node, status in coptic_status.items()):
        raise NtModuleError("candidate status without Coptic reference")
    if set(greek_ref) != set(greek_count):
        raise NtModuleError("Greek reference and count keys differ")
    if any(not _valid_node(node) for node in greek_ref):
        raise NtModuleError("invalid Greek parent node ID")
    if any(not _valid_ref(ref) for ref in (*coptic_ref.values(), *greek_ref.values())):
        raise NtModuleError("invalid edition-qualified NT reference")
    if len(set(greek_ref.values())) != len(greek_ref):
        raise NtModuleError("duplicate Greek target verse address")
    if any(not _valid_node(value) for value in greek_count.values()):
        raise NtModuleError("invalid Greek source occurrence count")
    expected = Counter(coptic_ref.values())
    observed = Counter({greek_ref[node]: greek_count[node] for node in greek_ref})
    if expected != observed:
        raise NtModuleError("Greek source count/reference does not reconcile to Coptic occurrences")
    if not expected:
        raise NtModuleError("empty reference module has no source candidates")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        ("coptic", "coptic_nt_ref_id", coptic_ref,
         "Edition-qualified NT verse-address candidate for source SBL node"),
        ("coptic", "coptic_nt_ref_status", coptic_status,
         "Original source SBL NT candidate resolution status"),
        ("greek", "coptic_nt_ref_id", greek_ref,
         "Greek parent NT verse anchor for Coptic SBL address candidates"),
        ("greek", "coptic_nt_source_occurrence_count", greek_count,
         "Number of physical Coptic SBL source occurrences addressing this verse"),
    )
    with TemporaryDirectory(prefix=".coptic-nt-wefts-", dir=destination.parent) as tmp:
        stage = Path(tmp) / "native-modules"
        for parent, name, values, description in fields:
            directory = stage / parent
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{name}.tf").write_bytes(
                render_node_feature(
                    name, values, projection=parent,
                    parent_proof=parent_proof, description=description,
                )
            )
        publish_path_no_clobber(stage, destination)
    return destination


# Git blob object IDs from the exact source checked at
# alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700.
# The verified historical tf/2022 warp is currently the pinned parent;
# a future generated MorphGNT source-base is a *distinct* parent profile.
GREEK_PARENT_PIN = "4dd0207bda66133fdfa9740ff0aae7de61228700"
GREEK_PARENT_GIT_BLOBS = {
    "otype": "02b15163b5a1367ee2fabf3c15651ddc146e36c8",
    "oslots": "b29ec118530423342a1662a942728aedbdbedcc3",
    "book": "cd3efffe843883e542b4e17671efd0981dc0fb2a",
    "chapter": "0ab7eabe75f78733aa4dbd35cf9aae0149226b5d",
    "verse": "b7c3a21f6675c4b783a26c0fef9f19db98a9f3d8",
}


def validate_greek_release(tf_dir: Path, api: Any) -> None:
    """Reject a lookalike Greek TF whose warp/sections differ from the pin."""
    if api.F.otype.maxSlot != 137554 or len(api.F.otype.s("verse")) != 7927:
        raise NtModuleError("Greek parent word/verse inventory mismatch")
    for feature, expected_blob in GREEK_PARENT_GIT_BLOBS.items():
        path = Path(tf_dir) / f"{feature}.tf"
        if not path.is_file() or path.is_symlink():
            raise NtModuleError(f"missing pinned Greek parent {feature}.tf")
        data = path.read_bytes()
        actual = sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        if actual != expected_blob:
            raise NtModuleError(f"wrong pinned Greek parent feature {feature}.tf")


def project_nt_modules(
    documents: Sequence[DocumentModel], *,
    coptic_api: Any, greek_api: Any,
    coptic_tf_dir: Path, greek_tf_dir: Path, destination: Path,
) -> dict[str, int]:
    """Project verified original SBL occurrence nodes into *both own warps*.

    All code and output are controlled by the Coptic project. Parent corpora
    are read-only inputs. A Greek word cannot be inferred from a Coptic span.
    """
    validate_greek_release(greek_tf_dir, greek_api)
    seen_records: set[str] = set()
    source_nodes: dict[tuple[str, str, int], int] = {}
    for kind in ("sbl_greek", "sbl_apparatus"):
        for node in coptic_api.F.otype.s(kind):
            record = coptic_api.F.source_record_id.v(node)
            ordinal = coptic_api.F.source_ordinal.v(node)
            if not isinstance(record, str) or not _valid_node(ordinal):
                raise NtModuleError("native Coptic SBL node missing source identity")
            key = record, kind, ordinal
            if key in source_nodes:
                raise NtModuleError("duplicate native Coptic source SBL annotation")
            source_nodes[key] = node

    source_status: dict[int, str] = {}
    source_ref: dict[int, str] = {}
    greek_ref: dict[int, str] = {}
    greek_count: Counter[int] = Counter()
    status_counts: Counter[str] = Counter()
    matched: set[tuple[str, str, int]] = set()

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        try:
            node = greek_api.T.nodeFromSection((book, chapter, verse))
        except (KeyError, ValueError):
            return None
        if node is None:
            return None
        if greek_api.F.otype.v(node) != "verse":
            raise NtModuleError("Greek target section is not a verse")
        if greek_api.T.sectionFromNode(node) != (book, chapter, verse):
            raise NtModuleError("Greek target reverse section mismatch")
        return node

    for document in documents:
        record = document.source_record_id
        if record in seen_records:
            raise NtModuleError("duplicate physical Coptic source record")
        seen_records.add(record)
        if document.upstream_repository != "CopticScriptorium/corpora" or document.upstream_commit != COPTIC_PIN:
            raise NtModuleError("wrong pinned source revision")
        parent = coptic_api.T.nodeFromSection((record,))
        if parent is None or coptic_api.F.otype.v(parent) != "document":
            raise NtModuleError("missing exact native Coptic source document")
        if coptic_api.F.source_sha256.v(parent) != document.source_sha256:
            raise NtModuleError("native Coptic parent source-byte SHA differs")
        words = tuple(coptic_api.L.d(parent, otype="word"))
        if len(words) != len(document.words):
            raise NtModuleError("native Coptic word count mismatch")
        for position, node in enumerate(words, start=1):
            if (coptic_api.F.source_record_id.v(node) != record
                or coptic_api.F.source_word_ordinal.v(node) != position
                or coptic_api.F.norm.v(node) != document.words[position-1].norm):
                raise NtModuleError("Coptic source word locality mismatch")

        for source_annotation, ref in zip(
            document.sbl_annotations,
            resolve_coptic_sbl_references(document, lookup=lookup),
            strict=True,
        ):
            key = record, source_annotation.kind, source_annotation.ordinal
            node = source_nodes.get(key)
            if node is None:
                raise NtModuleError("native Coptic source annotation absent")
            if key in matched:
                raise NtModuleError("duplicate Coptic source occurrence")
            matched.add(key)
            if (ref.source_record_id, ref.source_kind, ref.source_ordinal) != key:
                raise NtModuleError("resolver/source SBL occurrence mismatch")
            if (coptic_api.F.value.v(node) != source_annotation.value
                or coptic_api.F.sbl_verse_n.v(node) != source_annotation.source_verse_n):
                raise NtModuleError("native Coptic annotation source value differs")
            if source_annotation.word_ordinals:
                expected_slots = tuple(words[k-1] for k in source_annotation.word_ordinals)
                expected_mode = "sbl_span"
            else:
                ordinal = (source_annotation.start_word_ordinal
                           if source_annotation.start_word_ordinal is not None
                           else min(len(words), source_annotation.start_after_word_ordinal + 1))
                if ordinal < 1 or ordinal > len(words):
                    raise NtModuleError("invalid source SBL single-word anchor")
                expected_slots = (words[ordinal-1],)
                expected_mode = "sbl_anchor"
            if (tuple(coptic_api.L.d(node, otype="word")) != expected_slots
                or coptic_api.F.render_mode.v(node) != expected_mode):
                raise NtModuleError("native Coptic source SBL span/anchor mismatch")
            source_status[node] = ref.status
            status_counts[ref.status] += 1
            if ref.status == "reference_candidate":
                if ref.target_node is None or ref.shared_id is None:
                    raise NtModuleError("candidate without Greek target evidence")
                source_ref[node] = ref.shared_id
                old = greek_ref.setdefault(ref.target_node, ref.shared_id)
                if old != ref.shared_id:
                    raise NtModuleError("two Greek references claim same node")
                greek_count[ref.target_node] += 1
            elif ref.shared_id is not None or ref.target_node is not None:
                raise NtModuleError("unresolved Coptic source has forged Greek target")

    if matched != set(source_nodes):
        raise NtModuleError("unpaired native Coptic SBL annotation nodes")
    write_nt_modules(
        destination, coptic_ref=source_ref, coptic_status=source_status,
        greek_ref=greek_ref, greek_count=dict(greek_count),
        parent_proof={
            "coptic": parent_fingerprints(coptic_tf_dir, "coptic"),
            "greek": parent_fingerprints(greek_tf_dir, "greek"),
        },
    )
    return {
        **dict(status_counts),
        "coptic_annotated_sbl_nodes": len(source_status),
        "coptic_candidate_sbl_nodes": len(source_ref),
        "greek_target_verse_nodes": len(greek_ref),
    }
