"""`python3 ci/local.py act`: the host-side bosn -> act driver.

Runs on the host (not inside a container). It does the cheap, docker-free
steps itself (precheck, event planning), then hands off to `bosn run
--task act-run`, which execs `python3 ci/local.py act-inner` inside the
bosn-managed `act` stack container defined in `bosn.toml` -- the only
place the pinned `act` binary and the Docker CLI live. That container
talks to the *host* Docker engine through a bind-mounted
`/var/run/docker.sock` (zccache's pattern: act's job containers are then
siblings on the host engine, not nested), so the runner-image build and
every job container it starts are visible to, and cleaned up against,
the same engine this process itself could reach directly.

zackees/ci.yml#6 section 11, rules 1-2: "Same entrypoint, same
precheck... Precheck is also the local gate" -- a violation stops this
function before `bosn run` (and therefore before act, and before any
Docker network or build cost) ever starts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from ci.localrun.ci_toml_lite import CiTomlLiteError, read_local_section
from ci.localrun.ci_lint_checkout import CiLintCheckoutError, ensure_ci_lint
from ci.localrun.event import EventPlanError, write_act_event
from ci.localrun.precheck import run_precheck

# The only ci.yml jobs act can run today: both are plain ubuntu-24.04
# jobs with no native-runner requirement. Anything else declared in
# ci.toml [local].lanes or requested via --lanes (a platform id, a
# suite tag, "precheck" itself) is reported "not covered locally" and
# never attempted -- rule 7's "never as passed".
RUNNABLE_LANES = frozenset({"fast", "dylint"})

ACT_LOCAL_DIR = ".act-local"
RUNNER_IMAGE_TAG = "template-python-rust-cmd-act-runner:24.04-clang"


class ActRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class LaneResult:
    id: str
    seconds: float
    exit_code: int
    succeeded: bool


def _parse_lanes(raw: str | None, declared: tuple[str, ...]) -> list[str]:
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return [lane for lane in declared if lane != "precheck"]


def run_act(repo_root: Path, *, lanes_arg: str | None, title: str) -> int:
    outcome = run_precheck(repo_root, title=title)
    if outcome.exit_code != 0:
        print(
            "[ci/local.py] act: STOPPED at precheck -- fix the violation(s) above before "
            "any Docker/act cost is spent (zackees/ci.yml#6 section 11, rule 2).",
            file=sys.stderr,
        )
        return outcome.exit_code

    try:
        local_cfg = read_local_section(repo_root)
    except CiTomlLiteError as exc:
        print(f"[ci/local.py] act: {exc}", file=sys.stderr)
        return 1

    requested = _parse_lanes(lanes_arg, local_cfg.lanes)
    runnable = [
        lane for lane in requested if lane in RUNNABLE_LANES and lane in local_cfg.lanes
    ]
    not_covered = [lane for lane in requested if lane not in runnable]
    for lane in not_covered:
        print(
            f"[ci/local.py] act: lane '{lane}' is NOT covered locally "
            f"(not one of {sorted(RUNNABLE_LANES)} declared in ci.toml [local].lanes) -- "
            f"reported as skipped, never as passed. Verify it on GitHub-hosted CI.",
            file=sys.stderr,
        )
    if not runnable:
        print(
            "[ci/local.py] act: no runnable lanes requested; nothing to do.",
            file=sys.stderr,
        )
        return 0

    try:
        checkout = ensure_ci_lint(repo_root)
        act_dir = repo_root / ACT_LOCAL_DIR
        event_path = write_act_event(
            repo_root, checkout, title=title, out_path=act_dir / "event.json"
        )
    except (CiLintCheckoutError, EventPlanError) as exc:
        print(f"[ci/local.py] act: {exc}", file=sys.stderr)
        return 1

    run_id = f"tmpl-act-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    request = {
        "lanes": runnable,
        "event_path": str(event_path.relative_to(repo_root)),
        "run_id": run_id,
        "runner_tag": RUNNER_IMAGE_TAG,
    }
    (act_dir / "request.json").write_text(
        json.dumps(request, indent=2), encoding="utf-8"
    )
    result_path = act_dir / "result.json"
    result_path.unlink(missing_ok=True)

    print(
        f"[ci/local.py] act: run {run_id}, lanes {runnable} -> bosn run --task act-run",
        file=sys.stderr,
    )
    bosn_start = time.monotonic()
    bosn_result = subprocess.run(
        ["bosn", "run", "--task", "act-run"],
        cwd=str(repo_root),
        env=dict(os.environ),
        check=False,
    )
    bosn_seconds = time.monotonic() - bosn_start
    print(
        f"[ci/local.py] act: bosn run --task act-run finished in {bosn_seconds:.1f}s, exit {bosn_result.returncode}",
        file=sys.stderr,
    )

    if not result_path.is_file():
        print(
            f"[ci/local.py] act: {result_path} was never written -- the container run did "
            f"not complete cleanly (bosn exit {bosn_result.returncode}). Treating as failed.",
            file=sys.stderr,
        )
        return bosn_result.returncode or 1

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    for lane in payload.get("lanes", []):
        status = "PASSED" if lane["succeeded"] else "FAILED"
        print(
            f"[ci/local.py] act: lane '{lane['id']}': {status} in {lane['seconds']:.1f}s (exit {lane['exit_code']})"
        )
    audit = payload.get("cache_audit")
    if audit:
        print(audit["rendered"])

    ok = bool(payload.get("ok")) and bosn_result.returncode == 0
    return 0 if ok else 1
