"""Conservative, provenance-preserving classification of biblical TT metadata.

Candidate means only that the source family/CTS namespace suggests a biblical
collection, never that a LXX reference address is verified or aligned.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Mapping

CandidateStatus = Literal["ot_candidate", "nt_candidate", "conflicting", "undetermined"]

# Versioned set of corpus-family *hints*, not a guessed Greek book crosswalk.
# The full pinned-source census collects unrecognized families separately.
OT_FAMILIES = frozenset({
    "sahidic.ot", "bohairic.ot", "sahidic.ruth", "sahidic.jonah",
    "bohairic-jonah", "bohairic-habakkuk",
})
NT_FAMILIES = frozenset({
    "sahidica.nt", "bohairic.nt", "sahidica.mark", "bohairic.mark",
    "sahidica.1corinthians", "bohairic.1corinthians",
})

# Only an exact CopticLit CTS work prefix supplies the biblical OT/NT scope.
CTS_BIBLE_RE = re.compile(
    r"^urn:cts:copticLit:(ot|nt)\.([A-Za-z0-9_-]+)\.([^:]+):(.+)$"
)


@dataclass(frozen=True, slots=True)
class SourceBiblicalEvidence:
    status: CandidateStatus
    family: str
    family_scope: str | None
    cts_scope: str | None
    cts_work: str | None
    book_literal: str
    chapter_literal: str
    document_cts_urn: str
    evidence: tuple[str, ...]


def classify_biblical_record(
    family: str, metadata: Mapping[str, str]
) -> SourceBiblicalEvidence:
    family_scope = (
        "ot" if family in OT_FAMILIES
        else "nt" if family in NT_FAMILIES
        else None
    )
    urn = metadata.get("document_cts_urn", "").strip()
    match = CTS_BIBLE_RE.fullmatch(urn)
    cts_scope = match.group(1) if match else None
    cts_work = match.group(2) if match else None
    evidence = tuple(
        x for x in (
            f"family:{family_scope}" if family_scope else "",
            f"cts:{cts_scope}" if cts_scope else "",
        ) if x
    )
    if family_scope and cts_scope and family_scope != cts_scope:
        status: CandidateStatus = "conflicting"
    elif family_scope == "ot" or cts_scope == "ot":
        status = "ot_candidate"
    elif family_scope == "nt" or cts_scope == "nt":
        status = "nt_candidate"
    else:
        status = "undetermined"
    return SourceBiblicalEvidence(
        status=status,
        family=family,
        family_scope=family_scope,
        cts_scope=cts_scope,
        cts_work=cts_work,
        book_literal=metadata.get("book", ""),
        chapter_literal=metadata.get("chapter", ""),
        document_cts_urn=urn,
        evidence=evidence,
    )
