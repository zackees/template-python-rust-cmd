"""Test gate: `cargo test --workspace` + `pytest`.

This is one of the named entry points that legitimately *needs* the
extension module built (pytest imports `template_python_rust_cmd._native`).
We sync the dev deps with `--no-install-project` and let a direct
`maturin develop` materialize the extension module before pytest runs —
deliberately NOT via the PEP 517 backend (soldr), whose compile daemon
cannot spawn on GHA macOS/Windows runners (zackees/soldr#1300). The
backend path is covered by the `backend_smoke` gate on Linux.

Reserve this opt-in to the build for named entry points — see [zccache#835
rule 5](https://github.com/zackees/zccache/issues/835). Other gates use
`./ci.sh`'s `--no-project --script` discipline so they don't pay the
maturin cost.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return proc.returncode


def run() -> int:
    if shutil.which("cargo") is None:
        print("cargo not on PATH; cannot run test gate", file=sys.stderr)
        return 1
    if shutil.which("uv") is None:
        print("uv not on PATH; cannot run test gate", file=sys.stderr)
        return 1

    rc = _run(["cargo", "test", "--workspace"])
    if rc != 0:
        return rc

    # Materialize the dev dependency group (maturin, pytest) WITHOUT
    # installing the project itself. A plain `uv run` here would sync
    # the project editable through the PEP 517 backend (soldr), and
    # soldr's compile daemon cannot spawn on GHA macOS/Windows runners
    # (zackees/soldr#1300): macOS dies with "embedded compile dispatch
    # failed after 30000ms budget: NotRunning", Windows wedges the step
    # for an hour. The extension module is instead built by the direct
    # `maturin develop` call below, which does not route through the
    # backend. The backend itself is exercised by the `backend_smoke`
    # gate on Linux, where the daemon spawns fine.
    rc = _run(["uv", "sync", "--no-install-project"])
    if rc != 0:
        return rc

    # `maturin develop` builds + installs the extension module into the
    # synced venv directly (no PEP 517 backend involved). `--no-sync`
    # keeps uv from re-syncing (and re-triggering the backend build).
    rc = _run(
        [
            "uv",
            "run",
            "--no-sync",
            "maturin",
            "develop",
            "--uv",
            "--profile",
            "dev",
        ]
    )
    if rc != 0:
        return rc

    rc = _run(["uv", "run", "--no-sync", "pytest"])
    return rc


if __name__ == "__main__":
    raise SystemExit(run())
