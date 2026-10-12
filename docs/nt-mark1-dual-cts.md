# Mark 1 source-backed dual CTS verse addresses

**Scope:** Coptic-owned original SBL reference annotations; not Greek/Coptic word or textual alignment. This document records results of the independently pinned Mark1 pilot from [issue #117](https://github.com/alexsosn/CopticScriptorium-TF/issues/117).

## Two physically distinct original witnesses

The original source records are `sahidica.mark/sahidica.mark:Mark_01` and `coptic-treebank/coptic.treebank:Mark_01`, both at `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. Their full Git blob identities **differ**; they must remain separately counted even though the reviewed verse/SBL annotation values match. Greek parent: unmodified read-only `alexsosn/sblgnt@4dd0207bda66133fdfa9740ff0aae7de61228700`, actual native Text-Fabric 7,927 `verse` nodes.

The selected Mark 1 source records have **no editorial `verse_vid` layer**, but many of their original Coptic word spans contain both `verse_n` and a syntactically full `vid_n` CTS verse identifier. Those are *two original source metadata fields*, not independently authored Greek textual traditions. A candidate requires an exact positive verse number, full matching CTS work/chapter/verse, exact document CTS, reviewed source family/physical record/Greek attribution, and an actual Greek parent `verse` node with exact reverse-section identity. No Greek word/token IDs are ever written to the Coptic TF.

| Physical source | Candidates | Ambiguous | Greek target verses |
| --- | ---: | ---: | ---: |
| Canonical Mark 1 | 66 | 15 | 39 |
| Independent treebank Mark 1 | 66 | 15 | 39 |
| **Physical occurrences** | **132** | **30** | **39 unique addresses** |

Ten original `sbl_greek` values in each physical record resemble *editorial reference codes*, not Greek readings. Those and five other insufficient/inconsistent annotations remain **ambiguous** in each physical witness. This rule is expressly prohibited for Mark 10, Mark 11, 1 Corinthians 10 and all other chapters with just a single uncorroborated Coptic verse number.

## Complete pinned corpus acceptance

Before this batch, 2,747 source SBL annotations had status **2,362 candidate / 376 ambiguous / 8 unresolved / 1 edition-unavailable**. The measured source rule changes only the first two categories:

| Status | New full-source expectation |
| --- | ---: |
| `reference_candidate` | 2,494 |
| `ambiguous` | 244 |
| `unresolved` | 8 |
| `edition_unavailable` | 1 |
| **Total** | **2,747** |

The Coptic-origin bilateral native TF module target inventory rises from 944 to **983 unique Greek NT verse address nodes**, while Greek source-occurrence counts sum to 2,494. These counts must pass the complete 2,628-record source audit and the **full 2,394,354 Coptic word-slot TF conversion, native source conservation, weft projection and independent reloader** before this rule may be merged. Source-free CI audit output identifies accepted ordinals and the corresponding edition-qualified verse addresses; copyrighted Greek/Coptic text and generated corpora remain unredistributed.

No mapped Coptic word is asserted to correspond to a particular Greek token, and historical 2010 SBL source provenance does not prove reading identity with pinned MorphGNT 6.12.
