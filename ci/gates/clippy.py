"""`cargo clippy` gate with `-D warnings`.

Workspace-wide clippy run that treats every warning as an error. Targets
the entire crate graph (`--workspace --all-targets`) so tests and
examples are linted alongside the library / binary targets.

This is heavier than fmt (it compiles for analysis) but still cheaper
than a full release build because it shares the cargo cache with the
`build` and `test` gates. CI runs all three on the same runner so the
cache amortizes across them — see [zccache#835 rule 7](https://github.com/zackees/zccache/issues/835).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run() -> int:
    if shutil.which("cargo") is None:
        print("cargo not on PATH; cannot run clippy gate", file=sys.stderr)
        return 1
    proc = subprocess.run(
        [
            "cargo",
            "clippy",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(run())
