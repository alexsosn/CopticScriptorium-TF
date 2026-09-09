# Issue #1 — licensing findings

Pinned upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`.

The corpus-wide source census establishes that generated Text-Fabric data cannot safely be published under one repository-wide blanket data license.

## Measured boundary

The pinned TT census contains 2,628 source records and 17 distinct literal non-empty `license` strings plus three records with no `license` attribute. Literal strings include:

- CC-BY 4.0 in several syntactic/HTML variants;
- CC-BY-SA 3.0 and 4.0 variants;
- 11 CC BY-NC-SA 4.0 records;
- 307 Sahidica/J. Warren Wells academic-use records across two literal formulations;
- public-domain text combined with CC-BY 4.0 annotations/files;
- malformed or internally inconsistent HTML/link labels that must remain preserved as source evidence.

Raw TT values frequently contain HTML links while `meta.json` commonly stores a normalized label. String inequality between those serializations is therefore evidence requiring normalization/classification, not by itself a substantive license conflict.

## Missing-license identities

The three TT records with no `license` field are all in `book.bartholomew`:

1. `book-bartholomew/book.bartholomew_TT/book.bartholomew_part1.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:3-11`;
2. `book-bartholomew/book.bartholomew_TT/book.bartholomew_part2.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:12-19`;
3. `book-bartholomew/book.bartholomew_TT/book.bartholomew_part3.tt` — `urn:cts:copticLit:misc.blbartholomew.budge_ed:20-25`.

These are explicit unresolved redistribution cases. Their identities are also recorded in the machine-generated `missing_metadata_records` ledger and have been handed to follow-up #8.

## Downstream contract

1. Converter code licensing and generated-data licensing are separate concerns.
2. Every generated document/dataset must retain the literal upstream license/provenance evidence used to make distribution decisions.
3. Release packaging must be able to include/exclude records by reviewed redistribution policy rather than assuming all records share one compatible license.
4. Missing/unknown licenses are fail-closed for publication until explicitly resolved; they are not silently inherited from a corpus default.
5. Attribution, share-alike, non-commercial, academic-use and custom terms must survive into a machine-readable release manifest.
6. Normalized license families may be added only as derived fields with the literal source value preserved.
7. The converter may process unresolved records locally for validation where source access permits it; publication remains a separate gate.

Issue #8 owns license-family normalization, redistribution compatibility, filtering and release-manifest policy. Issue #1 only establishes the measured source boundary and fail-closed requirement.