# Product goals — CopticScriptorium-TF

## Users and purpose

Coptic linguists, biblical scholars and digital philologists should be able to convert permitted Coptic Scriptorium TT sources to native Text-Fabric, browse documents, search Coptic forms/lemmas/POS, inspect entities and dependencies and follow available translations and carefully sourced Coptic–Greek references.

## Representative research journeys

1. Install the converter, supply an allowed source revision, convert the real corpus and load the resulting TF without a repository checkout at reading time.
2. Find a document by its physical source identity and distinguish it from potentially shared scholarly identifiers.
3. Search actual Unicode Coptic forms, lemma and part of speech in TF and the local browser, then follow a result back to the document.
4. Inspect TT syntax/entity relations and optional CoNLL-U annotations without replacing or conflating source layers.
5. Query available translations or Coptic–LXX candidate links while displaying absence, ambiguity and parent-version constraints explicitly.

## Minimum usable release

A fresh researcher using public README/Agora instructions can convert supported TT input, load the result, navigate a passage and run representative real queries. Check source conservation and the complete first-user journey independently, including errors and resource limits. An upstream source upgrade must be separately evaluated, not silently substituted.

## Boundaries and immediate focus

The converter owns Coptic semantic mapping; Agora owns orchestration, and source TT/CoNLL-U remain upstream material. Avoid another browser or conversion framework when native TF can serve the task. Complete the actual autonomous first-user acceptance gate (issue #177) and review supported upstream version migration (issue #214); do not postpone a usable release for unsupported conjectural cross-language alignments.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
