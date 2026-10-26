"""Cancel merge-queue runs a newer queue run for the same PR replaced.

    python3 ci/cancel_superseded.py [--dry-run]

The `cancel-superseded` job of every `merge_group` run of ci.yml
(zackees/ci.yml#409, GEN-022). A queue ref carries the base commit,
`gh-readonly-queue/main/pr-<N>-<sha>`, so no concurrency group pairs a PR's
rebuilt queue run with the one main's movement replaced, and the old run
keeps holding runners. The newest queue run for a PR is the live one, so
every older in-flight queue run of this workflow for the same PR is
cancelled. Ported from zackees/clud's `ci/cancel_superseded.py` (#2048),
itself from obs-rust/obs-studio (#986).

Needs GITHUB_REPOSITORY, GITHUB_RUN_ID and a GITHUB_TOKEN with
`actions: write`. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen

QUEUE_RE = re.compile(r"(?:^|/)gh-readonly-queue/[^/]+/pr-(\d+)-[0-9a-f]+$")
LIVE = ("queued", "in_progress", "waiting", "pending", "requested")


@dataclass(frozen=True)
class Run:
    """The fields of a workflow run this script reads."""

    run_id: int
    head_branch: str
    status: str
    created_at: str

    @staticmethod
    def from_json(doc: dict[str, str | int | None]) -> Run:
        return Run(
            run_id=int(doc["id"] or 0),
            head_branch=str(doc.get("head_branch") or ""),
            status=str(doc.get("status") or ""),
            created_at=str(doc.get("created_at") or ""),
        )


def queue_pr(ref: str) -> int | None:
    """The PR number of a merge-queue ref, else None."""
    match = QUEUE_RE.search(ref)
    return int(match.group(1)) if match else None


def superseded(runs: list[Run], current: Run) -> list[int]:
    """Ids of in-flight queue runs for current's PR that started before it."""
    pr = queue_pr(current.head_branch)
    if pr is None:
        return []
    return sorted(
        {
            run.run_id
            for run in runs
            if run.run_id != current.run_id
            and run.status in LIVE
            and queue_pr(run.head_branch) == pr
            and run.created_at < current.created_at
        }
    )


def _api(path: str, method: str = "GET") -> dict[str, object]:
    request = Request(
        f"https://api.github.com/{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(request, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    repo = os.environ["GITHUB_REPOSITORY"]
    current_doc = _api(f"repos/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    current = Run.from_json(current_doc)  # type: ignore[arg-type]
    workflow = current_doc["workflow_id"]
    runs: list[Run] = []
    for status in LIVE:
        listing = _api(
            f"repos/{repo}/actions/workflows/{workflow}/runs"
            f"?event=merge_group&status={status}&per_page=100"
        )
        runs += [Run.from_json(doc) for doc in listing.get("workflow_runs", [])]  # type: ignore[union-attr]
    stale = superseded(runs, current)
    print(
        f"PR #{queue_pr(current.head_branch)}: cancelling {len(stale)} superseded queue run(s): {stale}"
    )
    for run_id in stale:
        if args.dry_run:
            continue
        try:
            _api(f"repos/{repo}/actions/runs/{run_id}/cancel", method="POST")
        except HTTPError as error:
            # A run that finished meanwhile can no longer be cancelled (409).
            print(f"run {run_id}: cancel returned {error.code}; leaving it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
