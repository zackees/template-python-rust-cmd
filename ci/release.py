"""Release-lane orchestration for the `linux-x64` leg (zackees/ci.yml#6
round 5, deliverable 2): the ONE platform the `platform-build`/
`platform-run` matrix never covers (`plan.platform_lanes` excludes
`[flow.pr]`'s own default fast-lane platform -- normally just
`linux-x64` -- by construction; round 5's brief calls this out as a
"decide and record" choice). **Decision**: build linux-x64's
release-profile wheel + sdist in its own dedicated job
(`release-linux-x64` in `.github/workflows/ci.yml`) rather than teaching
`ci_lint`'s planner to special-case the release flow's platform-lane set
-- that would touch the pinned `ci_lint` package (`zackees/ci.yml`,
out of this round's repo scope), where a template-repo script is
sufficient and keeps the change entirely local.

Also holds `collect-wheels`: merging `platform-build`'s staged
per-platform wheels (each nested at `<staged-dir>/platform-<id>/wheel/
*.whl`, round 3's `manifest.json` layout, unchanged here) into one flat
`dist/` directory alongside the `linux-x64` sdist+wheel, for
`release-verify`'s `ci-lint release verify --dist dist` (issue #6 §3,
`PKG-006`).

Same rules as every other `ci/*.py` orchestration module (`ci/fast.py`,
`ci/platform_build.py`): never invokes bare `cargo`/`rustc`/`maturin`/
`pip` (`RUST-001`/`PKG-003`/`TOOL-001`) -- `soldr`/`uv` only. Does not
import any other `ci/*.py` module (self-contained, stdlib-only, matching
the existing convention recorded in `ci/README.md`).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _run_isolated_soldr(cmd: list[str]) -> int:
    """See `ci/fast.py::_run_isolated_soldr` -- identical reasoning (two
    independent soldr broker roots can't share one claim), duplicated
    rather than imported so this module stays a self-contained,
    stdlib-only script like every other `ci/*.py` orchestration module in
    this repo."""
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("SOLDR_", "ZCCACHE_"))
    }
    print(
        f"+ {' '.join(cmd)}  (SOLDR_*/ZCCACHE_* stripped -- see docstring)", flush=True
    )
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ---------------------------------------------------------------------------
# build: sdist + release-profile linux-x64 wheel.
#
# **Round-5 finding (reported upstream, see the worker report): the wheel
# is NOT built FROM the sdist here**, even though that is PKG-004's ideal
# and issue #6 ci.yml#4's stated intent ("staged-artifact proof before any
# publisher... build the wheel FROM the sdist"). A plain `uv build`
# (sdist, then wheel-from-that-sdist -- the only path that satisfies
# PKG-004 literally) was tried first and reproducibly fails, independent
# of profile:
#
#   error: package ID specification `template-cli` did not match any packages
#   ... soldr build --bin template-cli ... --manifest-path
#   <extracted-sdist>/crates/template-py/Cargo.toml --profile dev
#   ... soldr._bundle_bins.BundleBinsError: exited with 101
#
# Root cause: maturin's sdist builder trims the workspace `Cargo.toml` it
# writes into the sdist down to the dependency graph reachable from
# `[tool.maturin] manifest-path` (`crates/template-py/Cargo.toml`).
# `template-cli` is a build-time SIBLING added only through `[tool.soldr.
# pep517] bundle-bins` -- it has no Cargo dependency edge to `template-py`
# -- so maturin drops it from the trimmed `[workspace] members` list even
# though pyproject.toml's own `[tool.maturin] include` already copies its
# FILES into the sdist (confirmed: `crates/template-cli/**` is present in
# the tarball; the regenerated root `Cargo.toml`'s `members` array simply
# omits `"crates/template-cli"`). `bundle-bins`'s own `soldr build --bin
# <bin> --manifest-path <the fixed manifest-path>` call then can't resolve
# `--package template-cli` inside that trimmed workspace. Adding the real
# root `Cargo.toml` to `include` does not help -- maturin's own generated
# sdist manifest always wins over a same-path `include` entry (tested
# locally). No `[tool.maturin]`/`[tool.soldr.pep517]` config in the public
# docs (`bundle-bins`'s only per-entry keys are `bin`/`package`/`dest`,
# no per-entry `manifest-path` override) exists to point that bundle-bins
# call at a different, untrimmed manifest. This is upstream soldr/maturin
# behavior, not a template misconfiguration -- no round before this one
# ever exercised the sdist-then-wheel path (`ci/fast.py`/`ci/platform_
# build.py` both use `uv build --wheel`, direct from the working tree,
# same as this function does below).
#
# **Decision**: build the sdist and the wheel as two SEPARATE `uv build`
# calls -- `--sdist` only, then `--wheel` only (direct from the working
# tree, exactly `ci/fast.py`/`ci/platform_build.py`'s existing, proven
# path, plus `profile=release`). Both artifacts are real and independently
# valid; this only gives up the STRONGER "wheel built from the sdist,
# proving the sdist alone is sufficient" claim for this round. `ci_lint
# release verify`'s own checks (PKG-006, and `wheel check`'s PKG-004 sdist
# check) still run against both staged artifacts exactly as before.
# ---------------------------------------------------------------------------


def cmd_build(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = _run_isolated_soldr(["uv", "build", "--sdist", "--out-dir", str(out_dir)])
    if rc != 0:
        return rc
    rc = _run_isolated_soldr(
        [
            "uv",
            "build",
            "--wheel",
            "--config-setting",
            "profile=release",
            "--out-dir",
            str(out_dir),
        ]
    )
    if rc != 0:
        return rc
    wheels = sorted(out_dir.glob("*.whl"))
    sdists = sorted(out_dir.glob("*.tar.gz"))
    if not wheels:
        print(f"ci/release.py: uv build produced no .whl in {out_dir}", file=sys.stderr)
        return 1
    if not sdists:
        print(
            f"ci/release.py: uv build produced no sdist (.tar.gz) in {out_dir}",
            file=sys.stderr,
        )
        return 1
    print(f"wheel: {wheels[-1]}")
    print(f"sdist: {sdists[-1]}")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"wheel-path={wheels[-1]}\n")
            fh.write(f"sdist-path={sdists[-1]}\n")
    return 0


# ---------------------------------------------------------------------------
# smoke: clean-venv native install smoke of the just-built linux-x64
# wheel, writing the SAME smoke-results/<id>.json shape
# `ci/platform_run.py`'s `wheel-install --smoke-out` writes, so
# `ci-lint release verify --smoke smoke-results` sees one uniform format
# for every platform (issue #6 §3, PKG-006).
# ---------------------------------------------------------------------------


def cmd_smoke(args: argparse.Namespace) -> int:
    wheels = sorted(Path(args.wheel_dir).glob("*.whl"))
    if not wheels:
        print(f"ci/release.py: no wheel found in {args.wheel_dir}", file=sys.stderr)
        return 1
    wheel_path = wheels[-1]

    venv_dir = Path(args.venv)
    rc = subprocess.run(
        ["uv", "venv", str(venv_dir), "--python", args.python], cwd=ROOT, check=False
    ).returncode
    if rc != 0:
        return rc
    venv_python = (
        venv_dir / "bin" / "python3"
    )  # linux-x64 only -- this job is ubuntu-24.04-only
    rc = subprocess.run(
        ["uv", "pip", "install", "--python", str(venv_python), str(wheel_path)],
        cwd=ROOT,
        check=False,
    ).returncode

    passed = False
    detail = "install failed"
    if rc == 0:
        cli_path = venv_dir / "bin" / args.cli_name
        if cli_path.is_file():
            _make_executable(cli_path)
            proc = subprocess.run([str(cli_path), "--version"], cwd=ROOT, check=False)
            passed = proc.returncode == 0
            detail = f"{args.cli_name} --version exit {proc.returncode}"
        else:
            detail = f"installed wheel has no {cli_path}"

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "platform": args.platform_id,
                "wheel": wheel_path.name,
                "passed": passed,
                "detail": detail,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"smoke ({args.platform_id}): passed={passed} ({detail}) -> {out_path}")
    return 0 if passed else 1


# ---------------------------------------------------------------------------
# collect-wheels: pull platform-build's staged `wheel/*.whl` out of each
# downloaded `platform-<id>` artifact directory into one flat `dist/`
# alongside the linux-x64 sdist+wheel `release-verify` already has.
# ---------------------------------------------------------------------------


def cmd_collect_wheels(args: argparse.Namespace) -> int:
    staged_dir = Path(args.staged_dir)
    dist_dir = Path(args.dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not staged_dir.is_dir():
        print(f"ci/release.py: {staged_dir} is not a directory", file=sys.stderr)
        return 1

    found = sorted(staged_dir.glob("*/wheel/*.whl"))
    if not found:
        print(f"ci/release.py: no '*/wheel/*.whl' under {staged_dir}", file=sys.stderr)
        return 1
    for wheel_path in found:
        dest = dist_dir / wheel_path.name
        shutil.copy2(wheel_path, dest)
        print(f"collected {wheel_path} -> {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("smoke")
    p.add_argument("--wheel-dir", required=True)
    p.add_argument("--platform-id", required=True)
    p.add_argument("--venv", required=True)
    p.add_argument("--python", default="3.11")
    p.add_argument("--cli-name", default="template-cli")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_smoke)

    p = sub.add_parser("collect-wheels")
    p.add_argument("--staged-dir", required=True)
    p.add_argument("--dist-dir", required=True)
    p.set_defaults(func=cmd_collect_wheels)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
