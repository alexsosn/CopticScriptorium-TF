# Issue #62 research and plan

## Research

The current browser app from #58 is deliberately configuration-only and lives at
`app/config.yaml`. The standard checkout command works because Text-Fabric
13.1.0 accepts a local app path plus local data locations:

```bash
tf "app:/path/to/app" --locations=/path/to/generated-tf --modules=.
```

However the project wheel currently declares only
`packages = ["copticscriptorium_tf"]`, so top-level `app/` is not part of the
installed package. An installed-wheel user therefore needs a repository checkout
only to locate browser presentation configuration.

Text-Fabric 13.1.0 exposes its browser startup as
`tf.browser.start.main(cargs)`. Reusing that function preserves the standard
port, browser-opening, `-noweb`, tool, and server behavior rather than
reimplementing Flask or Werkzeug.

Hatchling's wheel `force-include` can map the existing canonical top-level
`app/` directory into a package-relative wheel path. This avoids maintaining a
second copy of `config.yaml`. The installed launcher can find that resource via
`importlib.resources`; when executed directly from a source checkout before a
wheel build, it may fall back to the repository's top-level `app/` directory.

Python 3.12 is already the minimum project version, so
`importlib.resources.as_file()` can safely materialize a package resource
directory for the lifetime of the blocking browser process when needed.

A non-blocking `--check` mode is useful for clean-wheel CI: it should construct
the ordinary Text-Fabric Flask application through `tf.browser.web.setup()`
without binding a port or launching a browser. Normal execution must delegate to
`tf.browser.start.main()`.

## Plan

1. RED: require a new installed `copticscriptorium-tf-web` console entry point,
   package-visible corpus app resource, and source-checkout fallback.
2. RED: define argument construction for a generated TF directory and a
   non-blocking `--check` path that uses the standard TF browser setup.
3. RED: extend the clean-wheel CI gate to install the built wheel into an
   isolated venv, change out of the repository checkout, generate a tiny valid
   TF corpus with the already installed converter, and run
   `copticscriptorium-tf-web <tf-dir> --check`.
4. Implement a thin `copticscriptorium_tf.web_app` launcher. It must not contain
   custom server routes, app semantics, or corpus schema logic.
5. Use Hatch wheel `force-include` to map canonical `app/` into
   `copticscriptorium_tf/tf_app` inside the wheel.
6. Update `docs/web-app.md` and README so the installed launcher is the default
   path; keep the raw `tf app:...` command as a checkout/development fallback.
7. Verify ordinary converter command and bare `tf.fabric.Fabric` behavior are
   unchanged.
8. Run focused source tests, clean-wheel smoke, repository-wide exact-head CI,
   then perform a logically independent adversarial review.

## Failure boundaries

- missing/non-directory TF destination fails before starting the browser;
- missing packaged/source app configuration fails with an actionable error;
- `--check` returns failure when standard TF browser setup cannot construct an
  app;
- extra TF browser arguments are passed through unchanged after the TF
  directory;
- normal mode does not fork another custom server layer.

## Non-goals

No custom web framework, no generated-corpus sidecars, no prebuilt TF data in the
wheel, no Agora managed-artifact discovery/composition, and no attempt to package
the full researcher documentation/cookbook as a Python API.


## Review refinement

The first GREEN clean-wheel pass proved package-resource discovery and browser
setup outside a checkout, but its generated fixture exposed only the normalized
text format. The final wheel gate therefore uses an orig/norm-group fixture so
the installed launcher path is exercised with both native `text-orig-full`
and `text-diplomatic-full` formats. The same gate resolves the physical
`source_record_id` section through bare Text-Fabric after launcher setup and
asserts that the generated artifact contains only native `.tf` files.
