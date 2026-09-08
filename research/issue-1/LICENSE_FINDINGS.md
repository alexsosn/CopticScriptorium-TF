# Issue #1 — licensing findings

Pinned upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`.

The source-format census establishes that generated Text-Fabric data cannot be published under one repository-wide blanket data license.

## Measured/observed boundary

- Upstream documents carry per-document license metadata in TT and normalized license metadata in `meta.json`.
- The upstream README documents CC-BY 3.0/4.0 as common licenses, plus corpus-specific exceptions such as Sahidica New Testament terms and share-alike material.
- The corpus-wide TT census also contains CC BY-NC-SA 4.0 records.
- Three TT records at the pinned revision do not carry a `license` attribute and therefore require explicit resolution before redistribution.
- Raw TT `license` values are often HTML links, while `meta.json` commonly stores a normalized label. This serialization difference must not be treated as a substantive license conflict.

## Contract for downstream work

1. Converter code licensing and generated-data licensing are separate concerns.
2. Every generated document/dataset must retain the literal upstream license/provenance evidence used to make distribution decisions.
3. Release packaging must be able to include/exclude records by reviewed redistribution policy rather than assuming all records share one compatible license.
4. Missing/unknown licenses are fail-closed for publication until explicitly resolved; they are not silently inherited from a corpus default.
5. Attribution/share-alike/non-commercial/custom terms must survive into a machine-readable release manifest.
6. The converter may still process restricted or unresolved documents locally for validation if the source terms permit access; publication policy is a separate gate.

Implementation and legal-policy mechanics belong in a dedicated follow-up ticket derived from this research, not in issue #1's source-authority parser work.
