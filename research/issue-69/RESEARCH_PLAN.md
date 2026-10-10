# Issue #69 — Source-faithful Coptic biblical verse markers

## Research / actual source evidence (2026-10-10)
- DSS precedent: ETCBC/dss/alignment aligns to BHSA in two stages: first a calculated book/chapter/verse key, then text/morphology-based word matching. The DSS `parallels/tf/sim.tf` is a *different* intra-DSS line-similarity module, not a DSS↔BHSA edge. Coptic/LXX cannot reuse the Hebrew consonantal matcher.
- Target LXX: CATSS-TF already validates `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076` (release v1.0.1, TF 1935), with native book/chapter/verse and subverse nodes. CATSS-TF uses additive shared-ID TF modules, avoiding cross-warp node ID confusion.
- Real pinned Coptic source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`:
  - Sahidic Ruth `Ruth_02.tt`: 23 `verse_n`, 23 `vid_n`, 23 `verse_vid`; e.g. `Ruth 2:1` and CTS `urn:cts:copticLit:ot.ruth.copto_edt:2.1`.
  - Sahidic Jonah `Jonah_02.tt`: 11 `verse_n`, 0 `vid_n`, 0 `verse_vid`.
  - Bohairic Habakkuk `bohairic.Habakkuk_02.tt`: 20 `verse_n`, no CTS/verse_vid.
  - Source records have `meta chapter`; often incomplete book metadata, recoverable via dataset/record identity with explicit coverage mapping later.
  - The source says verse numbering may differ from Septuagint. Never silently map `verse_n` to LXX node identity.
  - All three samples have markers **outside** word `norm` tags. Full upstream census of inside-word occurrences needed before claiming uniformity.
- Current parser silently ignores these markup tags. Current TF has document-only sections; first step should not alter its slot/node hierarchy.

## Plan and gates
1. RED tests reproduce three real tag layouts with fixtures; require parser preserve raw marker values on each affected word, explicit reset of CTS/video when a new `verse_n` begins, and distinguish absent markers. Preserve existing non-biblical documents.
2. The parser checks source marker position: if an active `norm` has already begun, reject a verse marker rather than forging an all-word location for a token-internal boundary. Actual source census/repair is a separate research gate if this shape appears.
3. Extend `Word` and `GraphSlot` with three **optional** native literals `verse_n`, `vid_n`, `verse_vid` (defaults None so existing construction and tests remain backward-compatible). Project three scalar **word** features through the native TF writer. No JSON, no semantic blobs, no synthetic slots/nodes and no imported Greek coordinates.
4. Validate synthetic parser→graph→TF reload and existing regression suite on exact PR head. Check original sections and slot counts unchanged. Prefer real pinned Ruth direct-TT via CI fixture audit if feasible.
5. Independent adversarial review grounded in actual source tag order, reset behavior, fail-closed midword handling, generated features and absence of invalid LXX-equivalence claims; merge only green.
6. Separate #70 will convert verified source literal references to LXX mappings with Greek parent checking, versification exceptions and native per-parent TF modules.

## Acceptance
- [ ] TDD parser coverage and native TF reload
- [ ] Verified full-corpus regression / no unsupported source marker
- [ ] Exact-head CI green
- [ ] Independent adversarial review and merge
