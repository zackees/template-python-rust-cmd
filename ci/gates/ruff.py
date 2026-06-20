"""Python lint + format check via ruff.

Runs `ruff check` and `ruff format --check` over the Python tree (src,
tests, ci). Failing format is fixable with `ruff format`; failing lint
points at a real issue (unused imports, shadowed names, etc.).

Invoked via `uv run --no-project --with ruff` so we get a hermetic ruff
without triggering the maturin build the surrounding pyproject.toml
otherwise demands. `--with ruff` provisions the dep at script-time even
when the script itself has no PEP 723 deps declared for it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ["src", "tests", "ci", "ci.py"]


def _run(args: list[str]) -> int:
    if shutil.which("uv") is None:
        print("uv not on PATH; cannot run ruff gate", file=sys.stderr)
        return 1
    cmd = ["uv", "run", "--no-project", "--with", "ruff>=0.8", "ruff", *args]
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return proc.returncode


def run() -> int:
    rc1 = _run(["check", *TARGETS])
    rc2 = _run(["format", "--check", *TARGETS])
    return rc1 or rc2


if __name__ == "__main__":
    raise SystemExit(run())
