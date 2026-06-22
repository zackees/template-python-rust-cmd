#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
from __future__ import annotations

import os
import shutil
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_BIN_DIR = ROOT / "src" / "template_python_rust_cmd" / "_bin"
CLI_TARGET_NAME = (
    "template-cli.exe" if platform.system() == "Windows" else "template-cli"
)

# Pin cargo's target directory to a stable home-dir path so PEP 517
# isolated builds reuse cargo's incremental fingerprint cache across
# invocations. Without this, a `pip install .` (or `uv build`) that
# copies the source tree to a temp dir throws `<temp>/target/` away
# after each install — every install runs cargo cold (25-30s).
#
# Deliberately separate from `<repo>/target/` so iteration on
# bare `cargo check` / `cargo build` doesn't churn the wheel-build
# cache and vice versa. See FastLED/fbuild#743 and
# zackees/template-python-rust-cmd#2 (item 4).
WHEEL_BUILD_TARGET_DIR = (
    Path.home() / ".template-python-rust-cmd" / "cargo-target" / "wheel-build"
)
os.environ.setdefault("CARGO_TARGET_DIR", str(WHEEL_BUILD_TARGET_DIR))


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _cargo_target_root() -> Path:
    """Return cargo's effective target root, respecting CARGO_TARGET_DIR."""
    target_dir = os.environ.get("CARGO_TARGET_DIR")
    if target_dir:
        return Path(target_dir)
    return ROOT / "target"


def build_cli_binary() -> Path:
    if run(["cargo", "build", "--release", "-p", "template-cli"]) != 0:
        raise SystemExit(1)
    binary = _cargo_target_root() / "release" / CLI_TARGET_NAME
    if not binary.exists():
        raise SystemExit(f"expected native CLI binary at {binary}")
    return binary


def stage_cli_binary(binary: Path) -> Path:
    PACKAGE_BIN_DIR.mkdir(parents=True, exist_ok=True)
    staged = PACKAGE_BIN_DIR / CLI_TARGET_NAME
    shutil.copy2(binary, staged)
    return staged


def remove_staged_binary(staged: Path) -> None:
    if staged.exists():
        staged.unlink()


def build_python_artifacts() -> int:
    cmd = ["uv", "run"]
    if platform.system() == "Linux":
        cmd.extend(["--with", "ziglang"])
    cmd.extend(
        [
            "maturin",
            "build",
            "--release",
            "--sdist",
            "--interpreter",
            sys.executable,
            "--out",
            str(ROOT / "dist"),
        ]
    )
    return run(cmd)


def verify_artifacts() -> int:
    dist_dir = ROOT / "dist"
    wheels = sorted(dist_dir.glob("template_python_rust_cmd-*.whl"))
    sdists = sorted(dist_dir.glob("template_python_rust_cmd-*.tar.gz"))
    if not wheels:
        print("expected at least one wheel in dist/")
        return 1
    if not sdists:
        print("expected an sdist in dist/")
        return 1

    expected_binary_suffix = (
        "template-cli.exe" if platform.system() == "Windows" else "template-cli"
    )
    expected_entries = [
        "template_python_rust_cmd/_native",
        f"template_python_rust_cmd/_bin/{expected_binary_suffix}",
    ]
    with zipfile.ZipFile(wheels[-1]) as archive:
        names = archive.namelist()
    for entry in expected_entries:
        if not any(name.startswith(entry) for name in names):
            print(f"wheel is missing expected entry: {entry}")
            return 1
    return 0


def main() -> int:
    staged = stage_cli_binary(build_cli_binary())
    try:
        if build_python_artifacts() != 0:
            return 1
        return verify_artifacts()
    finally:
        remove_staged_binary(staged)


if __name__ == "__main__":
    raise SystemExit(main())
