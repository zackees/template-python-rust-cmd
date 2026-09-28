"""Dylint lane orchestration: one Linux job checks every declared target.

zackees/ci.yml#6 §2/§3/§5, and its third comment ("Use case to test:
cross-target Dylint must be cached and fast", D1-D8). This script is the
single `run:` line the `dylint` job in `.github/workflows/ci.yml` calls; it
does the per-target looping so the workflow YAML stays one line per step
(CLAUDE.md rule 6 / `GEN-005`).

Target source: `ci.toml`'s `[platforms]` table, read directly with stdlib
`tomllib` -- NOT `plan.json`'s `dylint_targets` field. Round 1's planner
narrows `dylint_targets` to the flow's *build* platform selection (just
`linux-x64` on an untagged PR), which is right for the build/test lane but
wrong for Dylint: ci.yml#6 says Dylint always covers every declared
platform, tagged or not, because it is a cheap pre-expansion/type check,
not a full cross build. Falling back to `[platforms]` directly is the
explicit brief instruction for this round ("or ci.toml [platforms] until
2A lands") and is reported as a planner finding, not silently patched
around.

Never invokes bare `cargo`/`rustc`/`rustup` -- every Dylint invocation goes
through `soldr` (RUST-001/RUST-002).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The one platform id whose target the `ubuntu-24.04` runner natively
# compiles for; every other declared platform is a cross check-only pass.
# Keep in sync with ci.toml's `linux-x64` entry.
HOST_PLATFORM_ID = "linux-x64"


@dataclass(frozen=True)
class DylintTarget:
    """One declared platform's Dylint identity (ci.toml `[platforms]`)."""

    platform_id: str
    triple: str
    is_host: bool


@dataclass(frozen=True)
class DylintPassResult:
    """One `soldr cargo dylint` invocation's outcome, for the step summary
    and the D1-D8 evidence table. Typed per AGENTS.md's benchmark-data rule
    (no raw dicts for measurement records)."""

    shape: str
    targets: tuple[str, ...]
    command: tuple[str, ...]
    seconds: float
    returncode: int

    def to_json_dict(self) -> dict[str, object]:
        return {
            "shape": self.shape,
            "targets": list(self.targets),
            "command": list(self.command),
            "seconds": round(self.seconds, 3),
            "returncode": self.returncode,
        }


def _load_platforms(repo: Path) -> list[DylintTarget]:
    ci_toml_path = repo / "ci.toml"
    with ci_toml_path.open("rb") as fh:
        data = tomllib.load(fh)
    platforms = data.get("platforms", {})
    if not isinstance(platforms, dict) or not platforms:
        raise SystemExit(f"ci/dylint.py: ci.toml has no [platforms] table at {ci_toml_path}")
    out: list[DylintTarget] = []
    for platform_id, entry in sorted(platforms.items()):
        triple = entry["target"]
        out.append(DylintTarget(platform_id=platform_id, triple=triple, is_host=(platform_id == HOST_PLATFORM_ID)))
    if not any(t.is_host for t in out):
        raise SystemExit(f"ci/dylint.py: ci.toml [platforms] has no '{HOST_PLATFORM_ID}' entry")
    return out


def _run(cmd: list[str]) -> tuple[int, float]:
    print(f"+ {' '.join(cmd)}", flush=True)
    start = time.monotonic()
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return proc.returncode, time.monotonic() - start


def _prepare_targets(cross: list[DylintTarget]) -> int:
    """`soldr dylint prepare --target T` for every cross target: fetches
    the prebuilt nightly rust-std for T. Never builds std or a toolchain
    from source (RUST-009)."""
    for target in cross:
        rc, seconds = _run(["soldr", "dylint", "prepare", "--target", target.triple])
        print(f"prepare --target {target.triple}: {seconds:.1f}s rc={rc}")
        if rc != 0:
            return rc
    return 0


def _run_sequential(host: DylintTarget, cross: list[DylintTarget]) -> list[DylintPassResult]:
    results: list[DylintPassResult] = []
    host_cmd = ["soldr", "cargo", "dylint", "--workspace"]
    rc, seconds = _run(host_cmd)
    results.append(DylintPassResult("sequential", (host.triple,), tuple(host_cmd), seconds, rc))
    if rc != 0:
        return results
    for target in cross:
        cmd = ["soldr", "cargo", "dylint", "--workspace", "--", "--target", target.triple]
        rc, seconds = _run(cmd)
        results.append(DylintPassResult("sequential", (target.triple,), tuple(cmd), seconds, rc))
        if rc != 0:
            return results
    return results


def _run_multi_target(host: DylintTarget, cross: list[DylintTarget]) -> list[DylintPassResult]:
    """D6 candidate: host artifacts (proc-macros, build scripts) compile
    once for every target in a single invocation, rather than once per
    sequential pass (see the clud macOS-vs-Windows half-cost hint in
    ci.yml#6 comment 3)."""
    cmd = ["soldr", "cargo", "dylint", "--workspace", "--"]
    for target in cross:
        cmd += ["--target", target.triple]
    rc, seconds = _run(cmd)
    all_triples = tuple([host.triple] + [t.triple for t in cross])
    return [DylintPassResult("multi-target", all_triples, tuple(cmd), seconds, rc)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--shape", choices=["sequential", "multi-target"], default="sequential")
    parser.add_argument("--results-out", default=None, help="write DylintPassResult[] JSON here")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    platforms = _load_platforms(repo)
    host = next(t for t in platforms if t.is_host)
    cross = [t for t in platforms if not t.is_host]
    print(f"dylint lane: host={host.triple} cross={[t.triple for t in cross]} shape={args.shape}")

    rc = _prepare_targets(cross)
    if rc != 0:
        print("ci/dylint.py: soldr dylint prepare failed; see log above", file=sys.stderr)
        return rc

    if args.shape == "multi-target":
        results = _run_multi_target(host, cross)
    else:
        results = _run_sequential(host, cross)

    total_seconds = sum(r.seconds for r in results)
    print(f"dylint lane: {len(results)} pass(es), {total_seconds:.1f}s total")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(f"\n### Dylint lane ({args.shape})\n\n")
            fh.write("| targets | seconds | rc |\n|---|---|---|\n")
            for r in results:
                fh.write(f"| {', '.join(r.targets)} | {r.seconds:.1f} | {r.returncode} |\n")
            fh.write(f"\n**total**: {total_seconds:.1f}s\n")

    if args.results_out:
        Path(args.results_out).write_text(
            json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8"
        )

    return next((r.returncode for r in results if r.returncode != 0), 0)


if __name__ == "__main__":
    raise SystemExit(main())
