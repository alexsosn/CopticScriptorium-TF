# Issue #84 — close source-byte identity gap in legacy Coptic↔LXX module API

## Research
A logically independent review of streaming PR #83 (review 5480529018) identified that source revision labels and identical record/word ordinals do **not** prove the supplied Coptic TT `DocumentModel` objects generated the TF parent. The streaming API now fail-closes on per-record SHA-256 parity against the generated parent `document` feature `source_sha256`. The old `materialize_lxx_reference_modules` lacks the same guard, although its pilot remains documented as a supported API. Both APIs derive candidate reference identities from source verse literals and write native weft-only TF features bound to parent node IDs.

Reviewed evidence: actual pinned Coptic corpus 2,628 records, 2,394,354 word slots; actual pinned CenterBLC/LXX 1935 (Greek commit `f32a98eddf7eb239aa73ab863d70381e416d5076`). `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` includes duplicated witnesses and alternate annotations. False joins can occur if two TT models share source_record_id and token count but differ in source bytes.

## Plan / RED → implementation → test → independent review
1. RED-first regression test: change only `DocumentModel.source_sha256` for a valid same-ID/same-size model and assert legacy API rejects and leaves no output. Separate missing/unloaded `F.source_sha256` failure. Ensure both tests would fail on old API.
2. Introduce one shared validation helper (source hash + exact parent document node identity) rather than maintaining divergent checks in streaming/legacy. The caller must explicitly load `source_sha256` in Text-Fabric.
3. Validate each legacy input source record against the corresponding actual parent `document` node *before* writing modules; bind the source SHA to parent identity, not just the Git revision string or abstract normalized token count. Fail closed on false doc identity, non-unique containing document and absent hash.
4. Preserve byte-for-byte legitimate pilot output and native-Coptic/Greek TF reload. Update real pilot, unit tests, docs. For streaming API, avoid a change to source data partition/count contracts; actual full CI must rerun on exact head if code changes are shared.
5. Independent adversarial review exact head grounded in source models, actual pinned Coptic/LXX CI logs, output fingerprints, and atomic failure. Do not claim certified textual equivalence; #75/#70 remain open.

## Risk
This branch is intentionally stacked on #83 until the independently reviewed source-verified streaming API is merged. It does not introduce new corpora or redistribute content.
