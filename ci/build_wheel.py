#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Build the template-python-rust-cmd wheel and sdist.

Flow:
  1. Build `template-cli` via cargo (release profile by default).
  2. Build the maturin wheel + sdist (PyO3 `_native` extension only).
  3. Inject the cargo-built `template-cli[.exe]` into the wheel's
     `<name>-<ver>.data/scripts/` directory and update RECORD.
  4. Verify the wheel contains both deliverables.

Environment:
  BUILD_PROFILE=dev   Build cargo + maturin with the dev profile
                      instead of release. Combined with the
                      `[profile.dev.package."*"] opt-level = 3` workspace
                      override and the rust-lld linker
                      (.cargo/config.toml), this is the fast local
                      iteration path. CI / release wheels stay on
                      `--release` (the default) because the env var is
                      unset there. See
                      zackees/template-python-rust-cmd#2 (item 9).
  CARGO_TARGET_DIR    Honored normally; if unset, defaults to
                      `~/.template-python-rust-cmd/cargo-target/wheel-build`
                      so isolated builds keep their incremental cache.

Why post-process instead of letting maturin handle the binary?
  Maturin doesn't ship raw binaries via the wheel scripts mechanism;
  it ships `data/` content but treats it as install-time data, not as
  Scripts/bin entries. We could go through `[project.scripts]`, but
  that generates a pip console-script `.exe` whose `os.execv` is
  emulated on Windows as `CreateProcess` + parent-exit — the shim
  returns to cmd.exe before the child binary finishes flushing stdout,
  so the next shell prompt races ahead of the output. Shipping the
  binary as a raw wheel script bypasses the Python launcher entirely.
  See fbuild#747 / zackees/template-python-rust-cmd#2 (items 1 + 10).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
PACKAGE_NAME = "template_python_rust_cmd"
CLI_TARGET_NAME = (
    "template-cli.exe" if platform.system() == "Windows" else "template-cli"
)

# Pin cargo's target directory to a stable home-dir path so PEP 517
# isolated builds reuse cargo's incremental fingerprint cache across
# invocations. See zackees/template-python-rust-cmd#2 (item 4).
WHEEL_BUILD_TARGET_DIR = (
    Path.home() / ".template-python-rust-cmd" / "cargo-target" / "wheel-build"
)
os.environ.setdefault("CARGO_TARGET_DIR", str(WHEEL_BUILD_TARGET_DIR))


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _cargo_target_root() -> Path:
    target_dir = os.environ.get("CARGO_TARGET_DIR")
    return Path(target_dir) if target_dir else ROOT / "target"


def _use_release_profile() -> bool:
    """True when this build should produce a release-optimized binary.

    Default is `True` — CI / release wheels are the dominant path through
    this script and they must ship optimized binaries. Set
    `BUILD_PROFILE=dev` (any case) to opt into a dev-profile build for
    fast local iteration. Combined with `[profile.dev.package."*"]
    opt-level = 3` in Cargo.toml and `rust-lld` linker in
    `.cargo/config.toml`, this is the biggest unlock for the
    Rust-edit → wheel round trip. Mirrors fbuild's
    `FBUILD_BUILD_RELEASE=1` opt-in (but inverted: release is the
    default here, dev is the opt-in). See
    zackees/template-python-rust-cmd#2 (item 9).
    """
    return os.environ.get("BUILD_PROFILE", "").lower() not in ("dev", "debug")


def _profile_subdir() -> str:
    return "release" if _use_release_profile() else "debug"


def _iter_cargo_inputs() -> list[Path]:
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


# `cargo_cache_path` is None until the first `build_cli_binary()` /
# mtime-skip resolves the cargo-built binary's location. The wheel
# injection step needs the same path; passing it through the call chain
# keeps `main()` straightforward.
def _cargo_cache_path() -> Path:
    return _cargo_target_root() / _profile_subdir() / CLI_TARGET_NAME


def _staged_cache_is_up_to_date(cache_path: Path) -> bool:
    """True if the cached cargo output is newer than every cargo input."""
    if not cache_path.is_file():
        return False
    cache_mtime = cache_path.stat().st_mtime
    for path in _iter_cargo_inputs():
        try:
            if path.stat().st_mtime > cache_mtime:
                return False
        except FileNotFoundError:
            return False
    return True


def _find_cli_executable_from_json(stdout: str) -> Path | None:
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
    profile = _profile_subdir()
    target_root = _cargo_target_root()
    candidates = [target_root / profile / CLI_TARGET_NAME]
    if target_root.is_dir():
        for child in target_root.iterdir():
            candidate = child / profile / CLI_TARGET_NAME
            if candidate.is_file():
                candidates.append(candidate)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def build_cli_binary() -> Path:
    """Build `template-cli` via cargo and return its on-disk path.

    Fast path: if the cached cargo output is newer than every cargo
    input, return it directly without invoking cargo.
    """
    cache_path = _cargo_cache_path()
    if _staged_cache_is_up_to_date(cache_path):
        print(
            f"  cargo cache up-to-date ({cache_path}); skipping cargo build",
            file=sys.stderr,
        )
        return cache_path

    cmd = [
        "cargo",
        "build",
        "-p",
        "template-cli",
        "--message-format=json-render-diagnostics",
    ]
    if _use_release_profile():
        cmd.insert(2, "--release")
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
            f"{_cargo_target_root()}/{_profile_subdir()}/{CLI_TARGET_NAME} "
            "(plus per-target subdirs)."
        )
    return binary


def build_python_artifacts() -> int:
    cmd = ["uv", "run"]
    if platform.system() == "Linux":
        cmd.extend(["--with", "ziglang"])
    cmd.extend(
        [
            "maturin",
            "build",
            "--sdist",
            "--interpreter",
            sys.executable,
            "--out",
            str(DIST_DIR),
        ]
    )
    if _use_release_profile():
        cmd.insert(cmd.index("--sdist"), "--release")
    return run(cmd)


def _latest_wheel() -> Path:
    wheels = sorted(DIST_DIR.glob(f"{PACKAGE_NAME}-*.whl"))
    if not wheels:
        raise SystemExit("no wheel found in dist/")
    return wheels[-1]


def _wheel_distribution_stem(wheel_path: Path) -> str:
    """Return `<name>-<ver>` from a wheel filename.

    A wheel filename is `{distribution}-{version}(-{build tag})?-{python
    tag}-{abi tag}-{platform tag}.whl` (PEP 427). The leading
    `<name>-<ver>` is what `<...>.data/` and `<...>.dist-info/`
    directories are prefixed with inside the archive.
    """
    parts = wheel_path.stem.split("-")
    return f"{parts[0]}-{parts[1]}"


def _record_row(arcname: str, data: bytes) -> str:
    """Build a RECORD CSV row matching the wheel spec.

    RECORD is `<arcname>,sha256=<urlsafe-b64 of sha256>,<size>` per
    https://peps.python.org/pep-0376/#record. RECORD's own row uses
    empty hash + size fields.
    """
    digest = hashlib.sha256(data).digest()
    h = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{arcname},sha256={h},{len(data)}"


def inject_cli_into_wheel(binary: Path) -> Path:
    """Rewrite the wheel: add the CLI at `<name>-<ver>.data/scripts/`.

    Files in `<name>-<ver>.data/scripts/` are pip's canonical "raw
    script" install location — pip drops them straight into the venv's
    `Scripts/` (Windows) or `bin/` (POSIX) directory verbatim. `.exe`
    files are NOT wrapped (pip only wraps shebang-style text scripts).
    This is the same mechanism `cargo-dist` and maturin's "bin" mode
    use to ship native binaries via PyPI without a Python shim.
    """
    wheel_path = _latest_wheel()
    stem = _wheel_distribution_stem(wheel_path)
    script_arcname = f"{stem}.data/scripts/{CLI_TARGET_NAME}"
    record_arcname = f"{stem}.dist-info/RECORD"

    binary_bytes = binary.read_bytes()

    # Read every existing entry into memory. Wheels are small enough
    # that loading the whole thing is fine (maturin emits ~MB-sized
    # wheels for projects this size).
    with zipfile.ZipFile(wheel_path, "r") as wf:
        entries: dict[str, bytes] = {name: wf.read(name) for name in wf.namelist()}

    if record_arcname not in entries:
        raise SystemExit(
            f"wheel has no {record_arcname}; cannot inject CLI script"
        )

    # Append a RECORD row for the new script. RECORD's own row keeps
    # empty hash + size per spec — we preserve that.
    record_text = entries[record_arcname].decode("utf-8")
    new_row = _record_row(script_arcname, binary_bytes) + "\n"
    record_text = record_text.rstrip("\n") + "\n" + new_row
    entries[record_arcname] = record_text.encode("utf-8")
    entries[script_arcname] = binary_bytes

    # Rewrite the wheel from scratch so deflated sizes and central-dir
    # offsets get rebuilt cleanly (in-place append leaves stale entries
    # if the same name was already present).
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as wf:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name)
            # Stamp Unix executable bit (0o755) on the script so POSIX
            # pip installs land it +x. create_system=3 = Unix.
            if name == script_arcname:
                info.create_system = 3
                info.external_attr = (0o755 << 16)
            wf.writestr(info, data)
    return wheel_path


def verify_artifacts() -> int:
    """Confirm the wheel ships both deliverables: PyO3 + raw CLI script."""
    wheels = sorted(DIST_DIR.glob(f"{PACKAGE_NAME}-*.whl"))
    sdists = sorted(DIST_DIR.glob(f"{PACKAGE_NAME}-*.tar.gz"))
    if not wheels:
        print("expected at least one wheel in dist/")
        return 1
    if not sdists:
        print("expected an sdist in dist/")
        return 1

    stem = _wheel_distribution_stem(wheels[-1])
    expected_entries = [
        f"{PACKAGE_NAME}/_native",  # PyO3 extension (filename varies by abi)
        f"{stem}.data/scripts/{CLI_TARGET_NAME}",  # raw CLI script
    ]
    with zipfile.ZipFile(wheels[-1]) as archive:
        names = archive.namelist()
    for entry in expected_entries:
        if not any(name.startswith(entry) for name in names):
            print(f"wheel is missing expected entry: {entry}")
            return 1
    return 0


def main() -> int:
    binary = build_cli_binary()
    if build_python_artifacts() != 0:
        return 1
    inject_cli_into_wheel(binary)
    return verify_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
