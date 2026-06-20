"""`cargo check --workspace` gate.

The cheapest gate that proves the Rust workspace still compiles. We use
`check` instead of `build` because the downstream `test` gate already
does a real build, so paying for two builds is wasted work.

**Fatal in `./ci.sh all`.** If this gate fails, every later gate
(`test`, `action_surface`, anything that touches the compiled binaries)
will produce noise instead of signal. `ci.py` sees `build` in
`FATAL_GATES` and halts the run, reporting only the build failure in
the final summary. See [zccache#835 rule 7](https://github.com/zackees/zccache/issues/835).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run() -> int:
    if shutil.which("cargo") is None:
        print("cargo not on PATH; cannot run build gate", file=sys.stderr)
        return 1
    proc = subprocess.run(
        ["cargo", "check", "--workspace", "--all-targets"],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(run())
