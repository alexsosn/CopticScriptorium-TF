"""Installed launcher for the standard Coptic Scriptorium Text-Fabric browser."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
import sys
from typing import Iterator, Sequence

from tf.browser.start import main as start_browser
from tf.browser.web import setup as setup_browser


_REQUIRED_TF_FILES = ("otype.tf", "oslots.tf", "otext.tf")


@contextmanager
def app_directory() -> Iterator[Path]:
    """Yield the corpus-app directory from a wheel or a source checkout."""
    packaged = files("copticscriptorium_tf").joinpath("tf_app")
    if packaged.joinpath("config.yaml").is_file():
        with as_file(packaged) as materialized:
            yield Path(materialized)
        return

    # Development/source-checkout fallback. The wheel does not depend on this
    # path: Hatch force-includes the canonical top-level app into tf_app.
    source_root = Path(__file__).resolve().parents[1]
    source = source_root / "app"
    if (source_root / "pyproject.toml").is_file() and (source / "config.yaml").is_file():
        yield source
        return

    raise FileNotFoundError(
        "CopticScriptorium-TF corpus app configuration is not installed"
    )


def browser_arguments(
    app_dir: Path,
    tf_dir: Path,
    extra: Sequence[str] = (),
) -> tuple[str, ...]:
    """Construct arguments for Text-Fabric 13.1.0's standard browser entry point."""
    return (
        f"app:{app_dir.resolve()}",
        f"--locations={tf_dir.resolve()}",
        "--modules=.",
        *tuple(extra),
    )


def _validate_tf_directory(path: Path) -> str | None:
    if not path.is_dir():
        return f"generated Text-Fabric directory does not exist: {path}"
    missing = [name for name in _REQUIRED_TF_FILES if not (path / name).is_file()]
    if missing:
        return (
            f"not a generated Text-Fabric directory: {path}; "
            f"missing {', '.join(missing)}"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    """Launch the standard TF browser using the wheel-packaged corpus app."""
    parser = argparse.ArgumentParser(
        prog="copticscriptorium-tf-web",
        description=(
            "Open generated CopticScriptorium-TF data in the standard "
            "Text-Fabric browser."
        ),
        epilog=(
            "Additional Text-Fabric browser flags such as -noweb, --chrome, "
            "--tool=ner, and debug are passed through unchanged."
        ),
    )
    parser.add_argument("tf_dir", type=Path, help="generated native TF directory")
    parser.add_argument(
        "--check",
        action="store_true",
        help="construct the standard browser app and exit without serving it",
    )
    args, extra = parser.parse_known_args(argv)

    tf_dir = args.tf_dir.resolve()
    problem = _validate_tf_directory(tf_dir)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    try:
        with app_directory() as app_dir:
            browser_args = browser_arguments(app_dir, tf_dir, extra)
            if args.check:
                webapp = setup_browser(False, *browser_args)
                if webapp is None:
                    print("Text-Fabric browser setup failed", file=sys.stderr)
                    return 1
                return 0

            start_browser(browser_args)
            return 0
    except (FileNotFoundError, OSError) as exc:
        print(f"Text-Fabric browser launch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
