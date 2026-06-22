#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
from __future__ import annotations

import json
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
STAGED_BINARY_PATH = PACKAGE_BIN_DIR / CLI_TARGET_NAME

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


def _iter_cargo_inputs() -> list[Path]:
    """Files that, if newer than the staged binary, invalidate the cache."""
    patterns = (
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "crates/**/Cargo.toml",
        "crates/**/*.rs",
    )
    paths: list[Path] = []
    for pat in patterns:
        paths.extend(ROOT.glob(pat))
    return paths


def _staged_binary_is_up_to_date() -> bool:
    """True if the staged binary exists and is newer than every cargo input.

    Skips the cargo invocation entirely on no-op reinstalls (version
    bumps, lockfile churn, --reinstall-package). Even cargo's "Fresh"
    pass walks the workspace and burns wall-clock seconds; an mtime
    check is milliseconds. See FastLED/fbuild#743 and
    zackees/template-python-rust-cmd#2 (item 6).
    """
    if not STAGED_BINARY_PATH.is_file():
        return False
    staged_mtime = STAGED_BINARY_PATH.stat().st_mtime
    for path in _iter_cargo_inputs():
        try:
            if path.stat().st_mtime > staged_mtime:
                return False
        except FileNotFoundError:
            # Glob race — treat as changed and rebuild.
            return False
    return True


def _find_cli_executable_from_json(stdout: str) -> Path | None:
    """Walk cargo's structured artifact stream for the `template-cli` exec.

    cargo emits one JSON object per line; the artifact we want has
    `reason == "compiler-artifact"`, `target.name == "template-cli"`,
    and a non-null `executable` field. We keep the *last* match because
    cargo emits one artifact per crate target kind and the bin artifact
    is what we want (matches `cargo install`'s selection rule).
    """
    found: Path | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("reason") != "compiler-artifact":
            continue
        target = msg.get("target") or {}
        if target.get("name") != "template-cli":
            continue
        executable = msg.get("executable")
        if executable:
            found = Path(executable)
    return found


def _find_cli_executable_by_search() -> Path | None:
    """Fallback when cargo emits no compiler-artifact line for the binary.

    Cargo skips the `compiler-artifact` JSON line for fully-cached
    builds (everything `Fresh`), so the primary discovery path returns
    None there. Probe `target/release/` and every per-host-triple
    subdir of `target/`. See zackees/template-python-rust-cmd#2 (item 8).
    """
    target_root = _cargo_target_root()
    candidates = [target_root / "release" / CLI_TARGET_NAME]
    if target_root.is_dir():
        for child in target_root.iterdir():
            candidate = child / "release" / CLI_TARGET_NAME
            if candidate.is_file():
                candidates.append(candidate)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def build_cli_binary() -> Path:
    cmd = [
        "cargo",
        "build",
        "--release",
        "-p",
        "template-cli",
        "--message-format=json-render-diagnostics",
    ]
    # stderr passes through; stdout is captured for the artifact stream.
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=None,
        check=False,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    binary = _find_cli_executable_from_json(proc.stdout)
    if binary is None or not binary.is_file():
        binary = _find_cli_executable_by_search()
    if binary is None or not binary.is_file():
        raise SystemExit(
            "cargo build succeeded but no `template-cli` binary was found.\n"
            "Searched cargo's JSON artifact stream and "
            f"{_cargo_target_root()}/release/{CLI_TARGET_NAME} (plus per-target subdirs)."
        )
    return binary


def stage_cli_binary(binary: Path) -> Path:
    PACKAGE_BIN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, STAGED_BINARY_PATH)
    return STAGED_BINARY_PATH


def _ensure_staged_cli_binary() -> Path:
    """Stage `template-cli` into the package, skipping cargo if cached.

    Fast path: if the staged binary is newer than every cargo input, the
    file on disk already reflects the current source — return it without
    touching cargo. Slow path: build via cargo and copy.
    """
    if _staged_binary_is_up_to_date():
        print(
            f"  staged binary up-to-date ({STAGED_BINARY_PATH}); skipping cargo",
            file=sys.stderr,
        )
        return STAGED_BINARY_PATH
    return stage_cli_binary(build_cli_binary())


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
    staged = _ensure_staged_cli_binary()
    try:
        if build_python_artifacts() != 0:
            return 1
        return verify_artifacts()
    finally:
        remove_staged_binary(staged)


if __name__ == "__main__":
    raise SystemExit(main())
