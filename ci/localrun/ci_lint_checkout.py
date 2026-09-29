"""Clone/fetch the pinned `ci_lint` checkout used by every local command.

`ci.toml`'s `linter` field (`zackees/ci.yml@<sha>`) is the single source
of truth for which `ci_lint` commit precheck runs -- the same pin
`.github/workflows/ci-precheck.yml` and `ci.yml` check out in CI
(`CT-004`). Locally we keep one gitignored checkout at `.ci-lint/` (the
same directory CI would produce if it ran here) and fast-path to a no-op
when it is already at the pinned commit, so a warm `precheck` run pays no
network cost at all.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import tomllib

CI_LINT_REMOTE = "https://github.com/zackees/ci.yml.git"
_LINTER_RE = re.compile(r"^([\w.-]+/[\w.-]+)@([0-9a-fA-F]{40})$")


class CiLintCheckoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckoutResult:
    path: Path
    sha: str
    was_cold: bool  # True: a clone/fetch actually ran; False: already warm at `sha`.
    seconds: float


def pinned_sha(repo_root: Path) -> str:
    """Read `ci.toml`'s `linter = "owner/repo@<40-hex-sha>"` field."""

    ci_toml_path = repo_root / "ci.toml"
    try:
        raw = ci_toml_path.read_bytes()
    except OSError as exc:
        raise CiLintCheckoutError(f"cannot read {ci_toml_path}: {exc}") from exc
    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise CiLintCheckoutError(f"cannot parse {ci_toml_path}: {exc}") from exc
    linter = doc.get("linter")
    if not isinstance(linter, str):
        raise CiLintCheckoutError(f"{ci_toml_path} has no string `linter` field")
    m = _LINTER_RE.match(linter)
    if not m:
        raise CiLintCheckoutError(
            f"{ci_toml_path} `linter = {linter!r}` does not match 'owner/repo@<40-hex-sha>'"
        )
    return m.group(2)


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={"GIT_TERMINAL_PROMPT": "0"},
    )


def ensure_ci_lint(repo_root: Path) -> CheckoutResult:
    """Ensure `repo_root/.ci-lint` is a checkout of the `ci.toml`-pinned SHA.

    Warm path (already at the pinned SHA): one `git rev-parse HEAD`, no
    network. Cold path: `git init` + `git fetch --depth 1 <sha>` +
    `git checkout FETCH_HEAD` -- GitHub.com serves arbitrary reachable
    commit SHAs over the smart HTTP protocol, so this works without a
    branch name.
    """

    start = time.monotonic()
    sha = pinned_sha(repo_root)
    ci_lint_dir = repo_root / ".ci-lint"

    if (ci_lint_dir / ".git").is_dir():
        current = _run(["git", "rev-parse", "HEAD"], cwd=ci_lint_dir)
        if current.returncode == 0 and current.stdout.strip() == sha:
            return CheckoutResult(
                ci_lint_dir, sha, was_cold=False, seconds=time.monotonic() - start
            )

    ci_lint_dir.mkdir(parents=True, exist_ok=True)
    if not (ci_lint_dir / ".git").is_dir():
        init = _run(["git", "init", "-q", "-b", "ci-lint-pin"], cwd=ci_lint_dir)
        if init.returncode != 0:
            raise CiLintCheckoutError(
                f"git init failed in {ci_lint_dir}: {init.stderr}"
            )
        remote = _run(
            ["git", "remote", "add", "origin", CI_LINT_REMOTE], cwd=ci_lint_dir
        )
        if remote.returncode != 0:
            raise CiLintCheckoutError(
                f"git remote add failed in {ci_lint_dir}: {remote.stderr}"
            )

    fetch = _run(["git", "fetch", "--depth", "1", "origin", sha], cwd=ci_lint_dir)
    if fetch.returncode != 0:
        raise CiLintCheckoutError(
            f"git fetch of zackees/ci.yml@{sha} failed: {fetch.stderr.strip()}"
        )
    checkout = _run(
        ["git", "checkout", "-q", "--detach", "FETCH_HEAD"], cwd=ci_lint_dir
    )
    if checkout.returncode != 0:
        raise CiLintCheckoutError(
            f"git checkout of {sha} failed: {checkout.stderr.strip()}"
        )

    return CheckoutResult(
        ci_lint_dir, sha, was_cold=True, seconds=time.monotonic() - start
    )
