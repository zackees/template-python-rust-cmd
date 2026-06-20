"""Runtime check that the composite action's surface matches the built binary.

The contract a downstream consumer cares about when they pin
`uses: zackees/template-python-rust-cmd@v1` is:

  - The binary the action points at exists and is executable.
  - Every subcommand the action's shell snippets call against shows up
    in `--help`.

That contract is independent of the full release pipeline — once the
binary is built, this gate is a <1 s subprocess sweep. Way cheaper than
a real `uses: ./` end-to-end build per matrix entry. See [zccache#835
rule 10](https://github.com/zackees/zccache/issues/835).

Heuristic: we look at every `run:` shell step in `action.yml`, extract
tokens that look like `template-cli <subcommand>` invocations, and
verify each `<subcommand>` is mentioned in `template-cli --help`. False
negatives are possible (e.g., a step that builds the subcommand name
dynamically) but the simple grep covers the common case and stops the
typo class of regressions.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# `yaml` is guarded so the contract test in `tests/test_gates.py` can
# import this module without pyyaml installed in the pytest venv. The
# PEP 723 inline-deps path on `ci.py` always provides pyyaml when this
# gate actually runs via `./ci.sh action_surface`.
try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / "action.yml"
BINARY_NAME = "template-cli.exe" if sys.platform == "win32" else "template-cli"


def _binary_path() -> Path | None:
    # Prefer the staged location used by the wheel; fall back to debug
    # for local dev (`cargo build`).
    candidates = [
        ROOT / "src" / "template_python_rust_cmd" / "_bin" / BINARY_NAME,
        ROOT / "target" / "release" / BINARY_NAME,
        ROOT / "target" / "debug" / BINARY_NAME,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _subcommands_from_action(path: Path) -> list[str]:
    assert yaml is not None  # guarded by run(); narrow for type-checkers
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = ((data or {}).get("runs") or {}).get("steps") or []
    pattern = re.compile(r"\btemplate-cli\s+([A-Za-z][A-Za-z0-9_-]*)")
    found: list[str] = []
    for step in steps:
        run_block = (step or {}).get("run")
        if not isinstance(run_block, str):
            continue
        for match in pattern.finditer(run_block):
            sub = match.group(1)
            # Skip flags accidentally captured (shouldn't happen with the
            # pattern above, but defensive).
            if sub.startswith("-"):
                continue
            found.append(sub)
    return sorted(set(found))


def run() -> int:
    if yaml is None:
        print(
            "action_surface: PyYAML not available. Run via `./ci.sh action_surface` so the PEP 723 inline-deps path provides it.",
            file=sys.stderr,
        )
        return 1

    if not ACTION.is_file():
        # No action.yml means nothing to check. action_yaml gate will
        # have failed first if there's supposed to be one.
        print("action_surface: no action.yml; skipping")
        return 0

    binary = _binary_path()
    if binary is None:
        # The `build` gate runs `cargo check` (not `cargo build`), so the
        # template-cli binary may not be materialized in CI. Skip with a
        # warning rather than fail — the structural contract is already
        # covered by action_yaml, and runtime surface validation is
        # best-effort against whatever build is available locally.
        print(
            "action_surface: no template-cli binary found "
            "(src/template_python_rust_cmd/_bin/, target/release/, "
            "target/debug/). Skipping runtime surface check. Run "
            "`cargo build -p template-cli` or `./test` to materialize "
            "the binary and re-run."
        )
        return 0
    if not shutil.which(str(binary)) and not binary.exists():
        print(f"action_surface: {binary} not executable", file=sys.stderr)
        return 1

    try:
        proc = subprocess.run(
            [str(binary), "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"action_surface: failed to run {binary} --help: {exc}", file=sys.stderr)
        return 1

    if proc.returncode != 0:
        print(
            f"action_surface: {binary} --help exited {proc.returncode}\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return 1

    help_text = (proc.stdout + "\n" + proc.stderr).lower()
    subs = _subcommands_from_action(ACTION)

    if not subs:
        # action.yml exists but doesn't shell out to template-cli — nothing
        # to check at the runtime level. action_yaml has the static checks.
        print("action_surface: no template-cli subcommands referenced in action.yml")
        return 0

    missing = [s for s in subs if s.lower() not in help_text]
    if missing:
        print(
            f"action_surface: subcommand(s) referenced in action.yml but not in `{binary.name} --help`: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    print(f"action_surface: ok ({len(subs)} subcommand(s) verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
