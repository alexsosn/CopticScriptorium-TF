# Issue #43 research and plan

## Research

The package is built by Hatchling and currently has no `[project.scripts]` entry in
`pyproject.toml`. The documented direct-user path therefore requires knowledge of
the internal module name:

```bash
python -m copticscriptorium_tf.converter ...
```

The existing `issue17-agora` workflow already runs on a clean Ubuntu runner and uses
PEP 517 `python -m pip install .`, which builds and installs the project wheel before
the real Agora host smoke. This is a suitable clean-install seam; a separate packaging
framework is unnecessary.

A console-script entry point may target `copticscriptorium_tf.converter:main`.
Generated console wrappers pass the returned integer to the process exit path, so the
existing `main(argv=None) -> int` contract is already appropriate.

To ensure a smoke does not accidentally import the checkout because the current
working directory is the repository, invoke the installed command from
`$RUNNER_TEMP`.

## Plan

1. RED metadata test: require
   `project.scripts.copticscriptorium-tf = copticscriptorium_tf.converter:main`.
2. Add the minimal PEP 621 console script declaration; do not change converter CLI
   semantics.
3. Extend the existing clean-install Agora workflow after its synthetic source fixture
   is prepared:
   - run `copticscriptorium-tf --help` from `$RUNNER_TEMP`;
   - run one direct synthetic conversion from `$RUNNER_TEMP`;
   - verify mandatory TF files and operational summary.
4. Make the installed command the README primary direct-conversion form while retaining
   `python -m ...` as an equivalent fallback.
5. Run exact-head CI and perform a logically independent adversarial review before
   readiness/merge.

## Non-goals

No argument redesign, subcommands, PyPI publication, or new runtime dependency.
