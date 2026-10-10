"""Bilateral additive native TF reference-candidate modules for Coptic ↔ LXX.

The shared reference is a candidate address, not a claim of textual or lexical
equivalence. Parent node numbers stay local to their respective TF warp.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

from .lxx_reference import resolve_coptic_lxx_references
from .model import DocumentModel

LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"

# Corresponding pinned source-blob identities from CATSS-TF's CenterBLC
# v1.0.1 LXX profile. Never trust a count-compatible wrong Greek edition.
LXX_FEATURE_GIT_BLOBS = {
    "otype": "2e6480116dfda09f20e8de7c5b9feefa76322a96",
    "oslots": "e95696a6a49f1149f8f6e850f7dfb40a26509931",
    "book": "0bfae94bb312cb7ecd33b102babb9400c554d8be",
    "chapter": "ec64b6bf72a6282e9da5064ca2e895171190208e",
    "verse": "ff8766352d7aff530c6eec4f66366adcc691740e",
    "subverse": "cecfaf2d1ddc4fd1e93958abd674a7e60e676ae5",
}


@dataclass(frozen=True, slots=True)
class LxxModuleSummary:
    coptic_candidate_words: int
    lxx_candidate_verses: int
    coptic_status_words: int
    source_documents: int


def verify_lxx_parent_feature_blobs(directory: Path) -> None:
    """Require exact mapping-critical CenterBLC/LXX v1.0.1 TF file bytes."""
    for feature, expected in sorted(LXX_FEATURE_GIT_BLOBS.items()):
        path = directory / f"{feature}.tf"
        if not path.is_file():
            raise ValueError(f"missing pinned LXX feature file {path.name}")
        payload = path.read_bytes()
        actual = sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
        if actual != expected:
            raise ValueError(
                f"pinned LXX feature {feature} Git blob mismatch: expected {expected}, got {actual}"
            )


def fingerprint_coptic_parent(directory: Path) -> str:
    """Fingerprint the generated Coptic warp and source-word identity features.

    The upstream Coptic source Git revision is NOT a commit of the generated
    Text-Fabric parent. Publish this fingerprint so a consumer can verify the
    actual compatible parent data, rather than trusting a mislabelled commit.
    """
    digest = sha256()
    required = (
        "otype", "oslots", "source_record_id", "source_word_ordinal",
        "source_sha256",
    )
    # A module's Coptic correspondence depends on source verse semantics,
    # not merely unchanged word node IDs. Include all source reference
    # literals and precisely positioned marker-event features when present.
    optional = (
        "verse_n", "vid_n", "verse_vid", "value", "event_ordinal",
        "start_word_ordinal", "start_char", "start_after_word_ordinal",
        "end_word_ordinal", "end_char", "end_after_word_ordinal",
    )
    for feature in (*required, *optional):
        path = directory / f"{feature}.tf"
        if not path.is_file():
            if feature in required:
                raise ValueError(f"missing generated Coptic parent TF feature {feature}")
            digest.update(f"{feature}\\0missing\\0".encode("ascii"))
            continue
        payload = path.read_bytes()
        digest.update(f"{feature}\\0{len(payload)}\\0".encode("ascii"))
        digest.update(payload)
    return digest.hexdigest()


def verify_coptic_module_parent(module_directory: Path, parent_directory: Path) -> None:
    """Fail closed when a native Coptic reference module has the wrong warp.

    Text-Fabric feature overlays use the existing parent node numbering. A
    source-Git revision alone does not identify the generated TF parent warp.
    """
    module_directory = Path(module_directory)
    modules = sorted(path for path in module_directory.glob("*.tf") if path.is_file())
    if not modules:
        raise ValueError("missing Coptic native reference module TF features")
    actual = fingerprint_coptic_parent(Path(parent_directory))
    expected: str | None = None
    for feature in modules:
        headers: dict[str, str] = {}
        with feature.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    break
                if line.startswith("@") and "=" in line:
                    key, value = line.rstrip("\n").split("=", 1)
                    headers[key] = value
        if headers.get("@parentRepo") != "CopticScriptorium-TF/generated":
            raise ValueError(f"invalid Coptic module parent identity in {feature.name}")
        observed = headers.get("@parentFingerprintSha256")
        if not observed or len(observed) != 64:
            raise ValueError(f"missing Coptic module parent fingerprint in {feature.name}")
        if expected is None:
            expected = observed
        elif observed != expected:
            raise ValueError("conflicting Coptic module parent fingerprints")
    if expected != actual:
        raise ValueError("Coptic module parent fingerprint mismatch")


def _write_feature(
    directory: Path, feature: str, data: dict[int, str], *,
    parent_repo: str, parent_commit: str | None,
    parent_fingerprint: str | None = None,
) -> None:
    if not feature.startswith("coptic_lxx_"):
        raise ValueError("cross-corpus feature must be in coptic_lxx namespace")
    if not data:
        return
    headers = [
        "@node",
        "@valueType=str",
        "@description=Source-evidenced Coptic/LXX reference candidates; not verified textual equivalence",
        "@writtenBy=CopticScriptorium-TF",
        "@referencePolicy=reference_candidate_unverified_versification",
        "@copticSourceCommit=" + COPTIC_PIN,
        "@lxxReleaseCommit=" + LXX_PIN,
        "@parentRepo=" + parent_repo,
    ]
    if parent_commit:
        headers.append("@parentCommit=" + parent_commit)
    if parent_fingerprint:
        headers.append("@parentFingerprintSha256=" + parent_fingerprint)
    headers.append("")
    for node, value in sorted(data.items()):
        if not isinstance(node, int) or isinstance(node, bool) or node <= 0:
            raise ValueError("native TF module node identifiers must be positive ints")
        if not isinstance(value, str) or not value:
            raise ValueError("native TF module feature values must be nonempty strings")
        escaped = value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
        headers.append(f"{node}\t{escaped}")
    (directory / f"{feature}.tf").write_text(
        "\n".join(headers) + "\n", encoding="utf-8"
    )


def materialize_lxx_reference_modules(
    *,
    documents: Iterable[DocumentModel],
    coptic_api: object,
    lxx_api: object,
    output_root: Path,
    lxx_parent_commit: str,
    coptic_source_commit: str,
    coptic_parent_tf: Path | None = None,
    lxx_parent_tf: Path | None = None,
    verify_parent_feature_hashes: bool = True,
) -> LxxModuleSummary:
    """Materialize native Coptic-word and LXX-verse reference ID modules.

    The caller provides fully loaded TF APIs for the generated Coptic parent
    warp and actual pinned CenterBLC/LXX parent. No foreign node IDs are
    written into the Coptic module or vice versa.
    """
    if lxx_parent_commit != LXX_PIN:
        raise ValueError("pinned LXX parent commit mismatch")
    if coptic_source_commit != COPTIC_PIN:
        raise ValueError("pinned Coptic source revision mismatch")
    if verify_parent_feature_hashes:
        if lxx_parent_tf is None:
            raise ValueError("missing pinned LXX TF path for Git blob verification")
        verify_lxx_parent_feature_blobs(lxx_parent_tf)

    if coptic_parent_tf is None:
        raise ValueError("missing generated Coptic parent TF path")
    coptic_parent_fingerprint = fingerprint_coptic_parent(Path(coptic_parent_tf))

    if coptic_api is None or lxx_api is None:
        raise ValueError("both parent TF APIs must be loaded")
    lxx_otype = lxx_api.F.otype
    if (
        lxx_otype.maxSlot != 623693 or lxx_otype.maxNode != 685732
        or len(lxx_otype.s("verse")) != 30371
    ):
        raise ValueError("pinned LXX parent node profile mismatch")

    all_coptic_words = tuple(coptic_api.F.otype.s("word"))
    indexed: dict[tuple[str, int], int] = {}
    for node in all_coptic_words:
        key = (
            coptic_api.F.source_record_id.v(node),
            coptic_api.F.source_word_ordinal.v(node),
        )
        if key in indexed:
            raise ValueError(f"duplicate Coptic TF source word identity: {key}")
        indexed[key] = node

    source_docs = tuple(documents)
    if not source_docs or len({d.source_record_id for d in source_docs}) != len(source_docs):
        raise ValueError("need unique nonempty Coptic documents")
    if any(d.upstream_commit != COPTIC_PIN for d in source_docs):
        raise ValueError("source documents do not carry the pinned Coptic revision")

    source_values: dict[str, dict[int, str]] = {
        "coptic_lxx_ref_id": {},
        "coptic_lxx_ref_status": {},
        "coptic_lxx_ref_evidence": {},
        "coptic_lxx_ref_reason": {},
    }
    target_ids: dict[int, str] = {}
    seen_coptic: set[int] = set()

    def lxx_lookup(book: str, chapter: int, verse: int) -> int | None:
        node = lxx_api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        if lxx_otype.v(node) != "verse":
            raise ValueError("Greek parent verse address resolved to non-verse node")
        return node

    for doc in source_docs:
        for mapping in resolve_coptic_lxx_references(doc, lookup=lxx_lookup):
            if mapping.lxx_node is not None:
                assert mapping.shared_id is not None
                old = target_ids.setdefault(mapping.lxx_node, mapping.shared_id)
                if old != mapping.shared_id:
                    raise ValueError("conflicting shared IDs for one Greek verse")
            for ordinal in mapping.source_word_ordinals:
                word_node = indexed.get((doc.source_record_id, ordinal))
                if word_node is None:
                    raise ValueError(
                        f"missing Coptic parent TF word: {(doc.source_record_id, ordinal)}"
                    )
                if word_node in seen_coptic:
                    raise ValueError(f"Coptic word assigned to multiple mappings: {word_node}")
                seen_coptic.add(word_node)
                source_values["coptic_lxx_ref_status"][word_node] = mapping.status
                source_values["coptic_lxx_ref_evidence"][word_node] = mapping.evidence
                source_values["coptic_lxx_ref_reason"][word_node] = mapping.reason
                if mapping.shared_id is not None:
                    source_values["coptic_lxx_ref_id"][word_node] = mapping.shared_id

    expected_coptic_words = sum(len(d.words) for d in source_docs)
    if len(seen_coptic) != expected_coptic_words:
        raise ValueError(
            f"incomplete source-word projection: {len(seen_coptic)} / {expected_coptic_words}"
        )

    output_root = Path(output_root)
    if output_root.exists():
        raise ValueError(f"destination already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".coptic-lxx-", dir=output_root.parent) as staging:
        root = Path(staging) / "payload"
        coptic_module = root / "coptic"
        lxx_module = root / "lxx"
        coptic_module.mkdir(parents=True)
        lxx_module.mkdir(parents=True)
        for feature, values in source_values.items():
            _write_feature(
                coptic_module, feature, values,
                parent_repo="CopticScriptorium-TF/generated",
                parent_commit=None, parent_fingerprint=coptic_parent_fingerprint,
            )
        _write_feature(
            lxx_module, "coptic_lxx_ref_id", target_ids,
            parent_repo="CenterBLC/LXX", parent_commit=LXX_PIN,
        )
        root.rename(output_root)

    return LxxModuleSummary(
        coptic_candidate_words=len(source_values["coptic_lxx_ref_id"]),
        lxx_candidate_verses=len(target_ids),
        coptic_status_words=len(source_values["coptic_lxx_ref_status"]),
        source_documents=len(source_docs),
    )
