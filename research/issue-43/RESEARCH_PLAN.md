# Issue #43 research and plan

## Research

The wheel is built by Hatchling from `copticscriptorium_tf`, and the reviewed CLI
entry function already exists as `copticscriptorium_tf.converter:main`. The package
metadata currently has no `[project.scripts]`, so installing the wheel exposes no
converter executable; users must know the internal module path.

PEP 621 console scripts are the narrow packaging seam here: mapping
`copticscriptorium-tf` directly to the existing `main` preserves one parser and one
implementation rather than introducing a wrapper CLI. The module invocation remains
valid because `converter.py` retains its `__main__` guard.

## Plan

1. RED: assert project metadata declares the exact console entry point and add a
   clean-wheel smoke that installs the built wheel, invokes
   `copticscriptorium-tf --help`, and exercises a fail-closed converter contract.
2. Add only the PEP 621 script mapping; no wrapper or runtime dependency.
3. Make the installed command the README primary path and retain the module form as
   an explicit equivalent fallback.
4. Run exact-head CI, including clean wheel installation.
5. Freeze the head and perform a logically independent adversarial review for
   packaging portability, exit-code parity, accidental duplicate CLI logic, and
   backwards compatibility before merge.

## Non-goals

No CLI argument redesign, subcommands, PyPI publication, or dependency changes.
