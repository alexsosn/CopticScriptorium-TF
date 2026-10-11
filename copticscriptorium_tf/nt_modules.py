"""Coptic-owned additive native TF reference wefts for Coptic SBL ↔ Greek NT.

Only this repository owns/writes either module. The pinned Greek NT parent is
read-only and no independent corpus warp is changed or redistributed.
Foreign TF node numbers are local map keys, never feature *values*.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from ._atomic import publish_path_no_clobber
from .nt_reference import GREEK_NT_EDITION, REVIEWED_SOURCES

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
    "coptic": ("otype", "oslots"),
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
