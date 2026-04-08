from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    checks = [
        ["cargo", "fmt", "--all", "--check"],
        ["cargo", "clippy", "--workspace", "--all-targets", "--", "-D", "warnings"],
        ["uv", "run", "ruff", "check", "src", "tests", "ci"],
    ]
    for cmd in checks:
        if run(cmd) != 0:
            return 1
    return 0
