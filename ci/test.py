from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    steps = [
        ["uv", "run", "maturin", "develop", "--uv", "--profile", "dev"],
        ["cargo", "test", "--workspace"],
        ["uv", "run", "pytest"],
    ]
    for cmd in steps:
        if run(cmd) != 0:
            return 1
    return 0
