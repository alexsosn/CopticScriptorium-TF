# Issue #97 — examine *edition-specific* Bohairic Zechariah numbering

## Evidence gate from merged #96

Immutable source `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`; Greek `CenterBLC/LXX@f32a98eddf7eb239aa73ab863d70381e416d5076`, Rahlfs/CenterBLC TF 1935. Real source audit #96 job 114350301131 completed after exact-head CI and independent skeptical review. It found 26 Zechariah physical records: 12 Sahidic `ot.zech.coptot` and 14 Bohairic `ot.zach.bohairic_ed`; 352 candidate reference addresses and exactly 4 unresolved `Bohairic Zech 1:18..21`. Sahidic chapter1 ends at 1:17 and starts chapter2 at 2:1; Bohairic chapter1 continues 1:18..21 then its chapter2 starts at 2:1.

Actual LXX Greek 2:1 begins `καὶ ἦρα τοὺς ὀφθαλμούς`. Bohairic 1:18 begins `ⲟⲩⲟϩ ⲁ ⲓ` (lexical opening consistent with “and I ...” but not conclusive). Bohairic2:1 begins `ⲟⲩⲟϩ ⲁ ⲓ`, suggesting a second offset for later verses. **Do not assume matching same-numbered addresses (positive in the baseline) are equivalent**, since a single Coptic source work can use an MT-style chapter boundary.

## RED→diagnostic→review
1. Write RED pure tests to prohibit global Zechariah shifts. Only `corpus=bohairic.ot` plus exact `urn:cts:copticLit:ot.zach.bohairic_ed:<chapter>` may emit a _diagnostic_ shifted-address hypothesis; chapter1 verses18–21 → Greek2:1–4; chapter2 verses1–6 → Greek2:5–10. Other works and Sahidic `ot.zech.coptot` return None; chapter mismatch and unsupported tails return None.
2. Extend existing pinned #95 diagnostic **only**, not the production resolver or native TF modules. For each source verse show bounded English translation head (if source translation annotations exist; do not assume correct alignment), short Coptic normalized head, exact Greek direct address and edition-qualified hypothetical Greek target with Greek head words. Retain explicit `hypothesis_not_verified` status.
3. Run the exact two Coptic ZIPs + pinned LXX real CI with the existing workflow, update tests to require the new negative-control contract. Do not publish source content files, generated text, or JSON sidecars.
4. Independent skeptical exact-head review of **actual** source words and translation evidence. Only if evidence is adequate propose a separate production **versioned crosswalk**, preserving source identity, 1:N ability and negative Sahidic control. Absent evidence keep #70/#75/#92/#97 open.
