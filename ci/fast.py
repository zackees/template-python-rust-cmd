"""Fast lane orchestration: linux-x64 build, unit tests, wheel smoke.

zackees/ci.yml#6 §3/§4. Each `.github/workflows/ci.yml` `fast` job step is
one line calling `python3 ci/fast.py <subcommand>` (CLAUDE.md rule 6 /
`GEN-005`); this module holds the logic so the workflow YAML stays thin.

Decisions this round made (see the PR body / worker report for evidence):
  - fmt and clippy stay separate soldr invocations (`./ci.sh fmt`, `./ci.sh
    clippy`), NOT folded into `soldr ci-test`'s bundled DAG. `soldr ci-test`
    also runs a host-only Dylint pass as part of that DAG; running it here
    would duplicate the dedicated `dylint` job's host pass with no shared
    cache (the two jobs run in parallel, so neither can warm the other's
    Actions cache mid-run). policy-rust.md is explicit: "Do not interpret
    the Dylint rule as permission to omit Clippy or formatting" — Clippy is
    Soldr-routed but its own required check, answering ci.yml#6's open
    question 3.
  - Build+test capture `--message-format=json` in a SEPARATE `--no-run`
    pass (`build-json`) so the file `ci_lint units`/`ci_lint tests size`
    read is pure JSON — cargo interleaves human test output with the
    compiler-message stream once tests actually execute.
  - The wheel build uses `uv build --wheel` (the plain PEP 517 frontend),
    not `soldr wheel`. Both were measured locally on this workspace, warm
    (2026-09-28): `uv build --wheel` 19.95s real (16.1s wheel build +
    template-cli bundling, dev profile, 23 HIT / 8 MISS then 6 HIT / 0
    MISS); `soldr wheel --release` 14.32s real (release profile). `soldr
    wheel` is ~28% faster here, but it does NOT go through the PEP 517
    protocol at all -- it bypasses `pyproject.toml`'s `build-backend`
    declaration entirely (it even prints "build-backend in pyproject.toml
    is not set to maturin", i.e. it expects a maturin-native project, not
    a PEP-517-fronted one) and drives its own internal maturin call
    directly. `PKG-004`'s requirement is specifically "build the wheel
    FROM the sdist through the PEP 517 frontend", which only `uv build`
    satisfies -- `soldr wheel` cannot be substituted regardless of its
    speed edge.

Never invokes bare `cargo`/`rustc`/`maturin`/`pip` (RUST-001/PKG-003) — see
`ci/gates/*.py` for the existing fmt/clippy/build/test gates this module
does not duplicate.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def cmd_build_json(args: argparse.Namespace) -> int:
    """Compile (no run) every declared test binary, capturing pure
    `--message-format=json` compiler-artifact records for
    `ci_lint units`/`ci_lint tests size`."""
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "soldr",
        "cargo",
        "test",
        "--workspace",
        "--locked",
        "--no-run",
        "--message-format=json",
    ]
    print(f"+ {' '.join(cmd)} > {out_path}", flush=True)
    with out_path.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=fh, check=False)
    return proc.returncode


def cmd_rust_test(_args: argparse.Namespace) -> int:
    """Actually run the workspace's declared test binaries. Reuses the
    `build-json` step's compile output (same lockfile, same flags), so
    this is normally a near-instant re-check plus execution."""
    return _run(["soldr", "cargo", "test", "--workspace", "--locked"])


def cmd_python_test(_args: argparse.Namespace) -> int:
    """Install the project through the real Soldr PEP 517 backend (builds
    `_native` and bundles `template-cli`), then run pytest against that
    installed artifact — not an in-place `cargo build`.

    `uv sync`'s isolated PEP 517 build environment installs its OWN copy
    of the `soldr` PyPI package (pinned by pyproject.toml's
    `requires = ["soldr==0.9.25"]`), which spawns a SEPARATE soldr binary
    from the one `.github/actions/soldr` already installed and started a
    broker for on PATH -- confirmed on real CI (run 36489839023, job
    109155586748: "the running broker was started from a different Soldr
    image", followed by "soldr root ownership is busy:
    .../setup-soldr-soldr (no daemon route claim to name the owner)").
    Two different soldr binaries cannot share one broker-owned root. This
    step therefore does NOT inherit the outer job's `SOLDR_*`/`ZCCACHE_*`
    workspace-state env vars (RUSTUP_HOME/CARGO_HOME/RUSTUP_TOOLCHAIN
    stay -- those select the toolchain, not a broker root), so the
    nested PEP 517 build resolves its own independent soldr session
    instead of contending for the already-claimed one."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SOLDR_", "ZCCACHE_"))}
    print("+ uv sync --frozen  (SOLDR_*/ZCCACHE_* stripped -- see docstring)", flush=True)
    rc = subprocess.run(["uv", "sync", "--frozen"], cwd=ROOT, env=env, check=False).returncode
    if rc != 0:
        return rc
    return _run(["uv", "run", "--no-sync", "pytest"])


def cmd_wheel_build(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = _run(["uv", "build", "--wheel", "--out-dir", str(out_dir)])
    if rc != 0:
        return rc
    wheels = sorted(out_dir.glob("*.whl"))
    if not wheels:
        print(f"ci/fast.py: uv build produced no .whl in {out_dir}", file=sys.stderr)
        return 1
    wheel_path = wheels[-1]
    print(f"wheel: {wheel_path}")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"wheel-path={wheel_path}\n")
    return 0


def cmd_wheel_install(args: argparse.Namespace) -> int:
    """Clean-venv install of the built wheel — proves the packaged
    artifact, not the source tree, imports and runs (`PKG-001`)."""
    wheels = sorted(Path(args.wheel_dir).glob("*.whl"))
    if not wheels:
        print(f"ci/fast.py: no wheel found in {args.wheel_dir}", file=sys.stderr)
        return 1
    wheel = wheels[-1]
    venv_dir = Path(args.venv)
    rc = _run(["uv", "venv", str(venv_dir), "--python", args.python])
    if rc != 0:
        return rc
    # Linux-only lane (ubuntu-24.04): no sys.platform/os.name branch needed
    # here — see ci.toml [allow] platform-code / CLAUDE.md rule 8.
    python_bin = venv_dir / "bin" / "python3"
    return _run(["uv", "pip", "install", "--python", str(python_bin), str(wheel)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build-json")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_build_json)

    p = sub.add_parser("rust-test")
    p.set_defaults(func=cmd_rust_test)

    p = sub.add_parser("python-test")
    p.set_defaults(func=cmd_python_test)

    p = sub.add_parser("wheel-build")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_wheel_build)

    p = sub.add_parser("wheel-install")
    p.add_argument("--wheel-dir", required=True)
    p.add_argument("--venv", required=True)
    p.add_argument("--python", default="3.11")
    p.set_defaults(func=cmd_wheel_install)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
