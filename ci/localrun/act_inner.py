"""`python3 ci/local.py act-inner`: runs INSIDE the bosn `act` stack container.

Never invoked directly -- `bosn.toml`'s `[task.act-run]` is the only
caller (`ci/local.py act`, on the host, triggers it via `bosn run --task
act-run`). Reads `.act-local/request.json` (written by the host step,
visible here because the repo is bind-mounted at `/work` == the host's
checkout root), builds the clang-patched runner image if it is not
already present (zackees/ci.yml#6 section 11's D7: `catthehacker/ubuntu
:act-24.04` has no `clang`, which setup-soldr's linker shim needs), runs
`act` once per requested lane against the host Docker engine (this
container's bind-mounted `/var/run/docker.sock`), labels and removes the
sibling job containers it creates, then runs the ACT-001 cache audit
against the machine-scoped cache-server volume and writes
`.act-local/result.json` for the host step to read back.

Known gap (see README "GITHUB_TOKEN and cross-repo checkouts"):
`ci.yml`'s `Checkout ci-lint (zackees/ci.yml, pinned)` step uses
`actions/checkout` with an explicit `repository:` override, which
requires a non-empty `token` input even for a public repo -- act does
not auto-populate `github.token` the way real GitHub Actions does, and
this tool never fetches or embeds a credential (worker contract: no
secrets). `_run_lane` below forwards `GITHUB_TOKEN` via act's `-s` flag
*only if it is already present in this process's environment* -- the
same "anonymous by default" pattern zccache's and clud's act stacks
document -- but bosn 0.1.3's `run --task` has no host-env-forwarding
flag, so today there is no supported way to get a token into this
container without writing it into `bosn.toml` (which the worker
contract also forbids). This is a real, reproduced local-only gap; see
the README for the recommended fix.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ci.localrun.cache_audit import audit as audit_cache
from ci.localrun.cache_audit import render as render_audit
from ci.localrun.ci_toml_lite import CiTomlLiteError, read_cache_section
from ci.localrun.sizes import parse_size

WORK = Path("/work")
ACTION_CACHE = Path("/root/.cache/act")
CACHE_SERVER = Path("/root/.cache/actcache")
ARTIFACT_SERVER = Path("/tmp/act-artifacts")
DOCKERFILE_RUNNER = WORK / "ci" / "docker" / "act" / "Dockerfile.runner"
WORKFLOW = ".github/workflows/ci.yml"


def _ensure_runner_image(tag: str) -> float:
    start = time.monotonic()
    inspect = subprocess.run(
        ["docker", "image", "inspect", tag], capture_output=True, check=False
    )
    if inspect.returncode == 0:
        return time.monotonic() - start  # warm: image already present
    build = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(DOCKERFILE_RUNNER),
            "-t",
            tag,
            str(DOCKERFILE_RUNNER.parent),
        ],
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(
            f"docker build of the runner image ({tag}) failed (exit {build.returncode})"
        )
    return time.monotonic() - start


def _run_lane(
    lane: str, *, event_path: Path, runner_tag: str, run_id: str
) -> tuple[float, int]:
    ARTIFACT_SERVER.mkdir(parents=True, exist_ok=True)
    cmd = [
        "act",
        "pull_request",
        "-W",
        WORKFLOW,
        "-j",
        lane,
        "-e",
        str(event_path),
        "-P",
        f"ubuntu-24.04={runner_tag}",
        "--pull=false",
        "--rm",
        "--action-cache-path",
        str(ACTION_CACHE),
        "--cache-server-path",
        str(CACHE_SERVER),
        "--artifact-server-path",
        str(ARTIFACT_SERVER),
        "--container-options",
        f"--init --label template.act-run={run_id}",
    ]
    # Anonymous by default (matches zccache's/clud's act stacks): forward
    # GITHUB_TOKEN only if this process's own environment already has it.
    # Never fetched, read, or logged by this tool -- see the module
    # docstring's "Known gap".
    if os.environ.get("GITHUB_TOKEN"):
        cmd += ["-s", "GITHUB_TOKEN"]
    start = time.monotonic()
    result = subprocess.run(cmd, cwd=str(WORK), check=False)
    return time.monotonic() - start, result.returncode


def _cleanup_containers(run_id: str) -> None:
    ids = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label=template.act-run={run_id}"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    if ids:
        print(
            f"[act-inner] removing {len(ids)} job container(s) for run {run_id}",
            file=sys.stderr,
        )
        subprocess.run(["docker", "rm", "-f", *ids], capture_output=True, check=False)


def main(argv: list[str] | None = None) -> int:
    del argv
    request_path = WORK / ".act-local" / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    lanes: list[str] = request["lanes"]
    event_path = WORK / request["event_path"]
    run_id: str = request["run_id"]
    runner_tag: str = request["runner_tag"]

    result: dict[str, object] = {
        "ok": True,
        "lanes": [],
        "runner_image_build_seconds": None,
    }
    try:
        result["runner_image_build_seconds"] = _ensure_runner_image(runner_tag)
    except RuntimeError as exc:
        print(f"[act-inner] {exc}", file=sys.stderr)
        result["ok"] = False
        (WORK / ".act-local" / "result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return 1

    try:
        for lane in lanes:
            seconds, exit_code = _run_lane(
                lane, event_path=event_path, runner_tag=runner_tag, run_id=run_id
            )
            succeeded = exit_code == 0
            result["lanes"].append(
                {
                    "id": lane,
                    "seconds": seconds,
                    "exit_code": exit_code,
                    "succeeded": succeeded,
                }
            )
            if not succeeded:
                result["ok"] = False
    finally:
        _cleanup_containers(run_id)

    try:
        cache_cfg = read_cache_section(WORK)
        budget_bytes = parse_size(cache_cfg.budget)
        if budget_bytes is None:
            raise CiTomlLiteError(
                f"ci.toml [cache].budget {cache_cfg.budget!r} does not parse"
            )
        audit_result = audit_cache(
            CACHE_SERVER, budget_bytes=budget_bytes, retired_families=cache_cfg.retired
        )
        rendered = render_audit(audit_result)
        print(rendered)
        result["cache_audit"] = {
            "ok": audit_result.ok,
            "disk_bytes": audit_result.disk_bytes,
            "budget_bytes": audit_result.budget_bytes,
            "findings": list(audit_result.findings),
            "rendered": rendered,
        }
        if not audit_result.ok:
            result["ok"] = False
    except CiTomlLiteError as exc:
        print(f"[act-inner] cache audit could not run: {exc}", file=sys.stderr)
        result["ok"] = False

    (WORK / ".act-local" / "result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return 0 if result["ok"] else 1
