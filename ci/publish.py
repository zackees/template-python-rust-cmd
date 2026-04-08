#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
_ENABLED = False


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def ensure_clean() -> int:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print("publish refuses dirty worktrees")
        return 1
    return 0


def ensure_dist() -> int:
    artifacts = list(DIST.glob("*.whl")) + list(DIST.glob("*.tar.gz"))
    if not artifacts:
        print("no artifacts found in dist/")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and publish release artifacts")
    parser.add_argument("--repository-url")
    args = parser.parse_args()

    if not _ENABLED:
        print("publishing is disabled; please manually enable _ENABLED when you are ready")
        return 1

    if ensure_clean() != 0:
        return 1
    if run(["uv", "run", "python", "ci/build_wheel.py"]) != 0:
        return 1
    if run(["uv", "run", "--with", "twine", "twine", "check", "dist/*"]) != 0:
        return 1
    if ensure_dist() != 0:
        return 1
    cmd = ["uv", "run", "--with", "twine", "twine", "upload", "--skip-existing"]
    if args.repository_url:
        cmd.extend(["--repository-url", args.repository_url])
    cmd.extend([str(path) for path in sorted(DIST.glob("*"))])
    return run(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
