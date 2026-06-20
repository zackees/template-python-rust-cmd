"""Test gate: `cargo test --workspace` + `pytest`.

This is one of the named entry points that legitimately *needs* the
maturin wheel built (pytest imports `template_python_rust_cmd._native`).
We invoke it via plain `uv run` (project context kept on purpose) so
maturin develop materializes the extension module before pytest runs.

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

    # `maturin develop` needs the project context, so we do NOT pass
    # --no-project here. This is the documented opt-in to the full
    # build (see [zccache#835] rule 5).
    rc = _run(
        [
            "uv",
            "run",
            "maturin",
            "develop",
            "--uv",
            "--profile",
            "dev",
        ]
    )
    if rc != 0:
        return rc

    rc = _run(["uv", "run", "pytest"])
    return rc


if __name__ == "__main__":
    raise SystemExit(run())
