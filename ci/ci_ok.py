"""`CI OK` gate: the one required check `ci.yml` exposes.

zackees/ci.yml#6 §2/§6. The `ci-ok` job (`if: always()`, `needs:` every
other job) passes the precheck job's `plan` output and `toJSON(needs)`
into this script's environment (never interpolated into a `run:` line --
script-injection rule, same reason PR titles never are). This is the ONE
line that job's step calls; everything else lives here and in `ci_lint
gate`.

`ci_lint gate` decides mergeability: every planned job succeeded AND the
selection itself is mergeable (`plan.json`'s own `mergeable` field is
false for `[no-test]`/`[no-test-<suite>]` regardless of job outcomes --
see ci.toml `[tags]`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    plan_json = os.environ.get("CI_OK_PLAN_JSON")
    needs_json = os.environ.get("CI_OK_NEEDS_JSON")
    if not plan_json or not needs_json:
        print(
            "ci/ci_ok.py: CI_OK_PLAN_JSON and CI_OK_NEEDS_JSON must be set "
            "(the ci-ok job's step env:, never interpolated into run:)",
            file=sys.stderr,
        )
        return 2

    # Validate before writing -- a malformed upstream output should fail
    # here with a clear message, not inside ci_lint's own parsing.
    try:
        json.loads(plan_json)
        json.loads(needs_json)
    except json.JSONDecodeError as exc:
        print(f"ci/ci_ok.py: CI_OK_PLAN_JSON/CI_OK_NEEDS_JSON is not valid JSON: {exc}", file=sys.stderr)
        return 2

    plan_path = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ci-ok-plan.json"
    needs_path = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ci-ok-needs.json"
    plan_path.write_text(plan_json, encoding="utf-8")
    needs_path.write_text(needs_json, encoding="utf-8")

    cmd = [
        "python3",
        "-m",
        "ci_lint",
        "gate",
        "--repo",
        str(ROOT),
        "--plan",
        str(plan_path),
        "--needs",
        str(needs_path),
    ]
    print(f"+ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
