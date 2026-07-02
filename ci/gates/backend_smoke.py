"""PEP 517 backend smoke: `uv build --wheel` through the soldr backend.

The `[build-system]` in pyproject.toml routes wheel builds through the
soldr backend (which drives `maturin pep517` under a rustc-caching
wrapper). The `test` gate deliberately avoids that path (see its
docstring), so without this gate the backend swap would ship untested.

This gate builds one wheel via the real backend — exactly what a
downstream `pip install template-python-rust-cmd` (sdist) or
`uv build` does.

Linux-only: soldr's compile daemon cannot spawn on GHA macOS/Windows
runners (zackees/soldr#1300) — macOS fails with "embedded compile
dispatch failed after 30000ms budget: NotRunning" and Windows wedges
the step for ~an hour. On those platforms the gate skips (returns 0)
rather than burning an hour to report a known-upstream condition.
Re-enable everywhere once soldr#1300 is fixed and the pin in
pyproject.toml is bumped past the fixed release.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run() -> int:
    if sys.platform != "linux":
        print(
            "backend_smoke: skipped on non-Linux (soldr compile daemon "
            "cannot spawn on GHA macOS/Windows runners — "
            "zackees/soldr#1300). The backend path is exercised on the "
            "Linux lanes."
        )
        return 0
    if shutil.which("uv") is None:
        print("uv not on PATH; cannot run backend_smoke gate", file=sys.stderr)
        return 1
    proc = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", "dist/backend-smoke"],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(run())
