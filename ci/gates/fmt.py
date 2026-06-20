"""`cargo fmt --check` gate.

Runs `cargo fmt --all -- --check` against the Rust workspace. Does NOT
write changes; failing is the signal to run `cargo fmt --all` locally.

This gate is fast (no compilation, no target/ writes), so it runs before
the heavier clippy / build gates in `ci.py::GATE_ORDER`. Crucially the
process is invoked through plain `cargo` — the caller (`./ci.sh`) has
already protected itself from a maturin rebuild via `--no-project
--script` on the dispatcher, so adding `uv run` here would be pure cost.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run() -> int:
    if shutil.which("cargo") is None:
        print("cargo not on PATH; cannot run fmt gate", file=sys.stderr)
        return 1
    proc = subprocess.run(
        ["cargo", "fmt", "--all", "--", "--check"],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(run())
