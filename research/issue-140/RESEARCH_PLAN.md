# #140 — Edition line/page wrappers (research / plan / RED)

Parent: #118, original raw tag census: 565 Git TT blobs/2,628 physical records at CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5. Counts: ed_line_n 42,189 (7,419 openings inside norm), ed_lb_n 216 (17 inside norm), ed_page_n 1,047 (115 inside norm), ed_pg_n 283 (42 inside norm): **43,735** edition-tag openings.

Manual evidence from pinned real files:
- acts-pilate/acts.pilate_TT/pilate.1643.27-28.tt: 128 ed_line_n, 2 ed_page_n; old manuscript pb_xml_id and lb_n coexist with separate edition pagination, some line wrappers contain entity/lang/word groups.
- shenoute-crushed/shenoute.crushed_TT/shenoute.crushed.FL125-132.tt: 79 ed_lb_n, 6 ed_page_n, with note and morph inside.
- book-bartholomew/book.bartholomew_TT/book.bartholomew_part1.tt: 16 ed_pg_n; literal "0001" must not be coerced to int.
- bohairic-lausiac/bohairic.lausiac_TT/bohairic.lausiac_01.tt: 317 ed_line_n, 20 ed_page_n; independent edition and diplomatic line systems.

Source conventions: TT is SGML-like and may have crossed annotation closures; do not impose global XML tree. These values are literal edition references **not biblical verse equivalence or physical manuscript coordinates**.

Decision: Four **new native non-slot TF otypes** and one source-local independently counted `edition_annotations` occurrence track, independent of TT, SBL, lang, morph, and CoNLL-U IDs. Reuse existing source-position structure with full-word membership computed only from source-bounded completed norm slots; `edition_span` for at least one completely covered word, `edition_anchor` for partial/in-between events, always preserve source word and character offset boundaries. Preserve empty literals, leading zeros, source identity, and exact source opening ordinal. No JSON sidecars.

RED tests include crossed edition wrappers, inside-norm partial word annotation, source leading-zero value, multiple words spanning two groups, absent/orphan/unclosed errors, unchanged linguistic dependencies, source language and token/sbl counters, and real native reload. GREEN implementation should append otypes to avoid renumbering earlier nodes and share parser+graph materializer code, not copy each tag. Extra full-source pinned CI gate verifies native TF count 42,189/216/1,047/283, 2,394,354 canonical Coptic word slots, 2,628 documents, 136,860 token annotations, 110,148 lang, 2,747 SBL; inspect ZIP members too. Run independent raw-source audit and logically-independent adversarial review before merge. No corpus redistribution.

This PR is intentionally RED-first research until actual full pinned-source audit resolves zero-locus and terminal-editorial edge cases; no merge on synthetic tests alone.
