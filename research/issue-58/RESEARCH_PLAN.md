# Issue #58 research and plan

## Research

The generated corpus already has the browser-critical Text-Fabric contract in
`otext.tf`: the only section type is `document`, its section feature is
`source_record_id`, normalized text is `text-orig-full`, and diplomatic text
is `text-diplomatic-full` when diplomatic source material exists. The web-app
layer should consume that contract rather than introduce another corpus model.

The project pins `text-fabric==13.1.0`. Review of that exact Text-Fabric tag
establishes these constraints:

- a corpus app may be configuration-only: `app/config.yaml` is sufficient and
  no `app.py` hook is required unless custom formatting logic is needed;
- the standard `tf` browser accepts a local app as `app:/path/to/app` and
  accepts local generated TF through `--locations` / `--modules`;
- `tf.app.use("app:/path/to/app", locations=..., modules=...)` exercises the
  same advanced-app configuration without starting a server;
- `tf.browser.web.setup(...)` constructs the Flask browser application and can
  be smoke-tested without opening a browser or binding a listening socket;
- with exactly one TF section type, `browseNavLevel` must be `0`;
- Coptic is not one of Text-Fabric 13.1.0's built-in `writing` codes, so the
  app must not lie by selecting another writing system;
- no custom format hook is needed because both normalized and diplomatic
  formats are already native TF formats emitted by the writer;
- custom type styles are avoided in this first app slice because the pinned
  settings validator reports unsupported type-display keys inconsistently.
  Unicode Coptic and Arabic remain ordinary source text and browser/font
  fallback is preferable to version-fragile custom Python/CSS hooks.

The local app must also stay network-independent. For an `app:` path,
`provenanceSpec.org` and `provenanceSpec.repo` therefore remain null so
Text-Fabric does not try to acquire corpus data from GitHub. Explicit
`--locations=<generated-tf> --modules=.` supplies the generated dataset.

## Planned app surface

`app/config.yaml` will:

- declare app API version 3;
- use `text-orig-full` as the default and preserve the generated
  `text-diplomatic-full` alternative;
- configure one-level physical-document navigation and a realistic
  `source_record_id` example;
- expose compact static defaults only for guaranteed `document` and `word`
  features; optional node types/features must remain usable through search
  without making sparse valid corpora fail app validation;
- default the browser to showing node IDs, node types, standard features, and
  query features so graph inspection is practical without enabling the noisy
  all-feature display;
- keep all dependency/entity/document relation edge features loaded and
  queryable instead of duplicating them into display-only scalar features.

A short `docs/web-app.md` will document the local command from a repository
checkout:

```bash
tf "app:$(pwd)/app" --locations=/path/to/output-tf --modules=.
```

The same generated directory must remain independently loadable through
`tf.fabric.Fabric`.

## TDD / verification plan

1. RED: add a focused test that requires `app/config.yaml`, generates native TF
   from a representative synthetic graph, loads it through the local advanced
   app, resolves a physical section, renders normalized/diplomatic text, exposes
   linguistic/entity/translation/relation features, executes a Text-Fabric
   search, and constructs the browser Flask app.
2. RED: add an exact-head workflow for the focused browser test.
3. Implement only the minimal config-only app and launch documentation required
   to satisfy that contract.
4. Add a bounded pinned-real-source smoke derived from the existing issue #15
   directory/ZIP regression fixture; load the freshly written native TF through
   the app, construct the standard Flask browser, serve `/query`, and execute a
   representative search.
5. Run the full repository suite plus the focused exact-head browser workflow.
6. Freeze the final head and perform a logically independent adversarial review
   grounded in the pinned Text-Fabric 13.1.0 implementation, generated TF files,
   browser startup, query behavior, and the real upstream slice.

## Non-goals

No bespoke web framework, hosted public corpus, prebuilt TF publication, Agora
artifact discovery, Context-Fabric handoff, schema changes, semantic JSON/XML
sidecars, custom Python app hooks, or upstream scholarly certification.

## Review refinement

The first GREEN pass showed that hard-coding optional entity/translation/layout
types in `typeDisplay` would make the app configuration depend on those types
being present in every converted subset. The final design therefore keeps
static type defaults to guaranteed `document` and `word` features, while the
advanced app still loads the generated optional node/edge feature inventory and
the browser exposes features used by searches. The adversarial review also
strengthened the pinned-real-source gate to construct and exercise the standard
Flask `/query` route, and requires the README to link the browser entry point.
