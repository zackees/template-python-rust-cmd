#!/usr/bin/env python3
"""`ci/local.py` -- the one entry point for the local CI loop.

zackees/ci.yml#6 section 11 ("bosn -> act: local CI is first class").

    python3 ci/local.py precheck              # ~seconds; the agent Stop-hook / pre-push gate
    python3 ci/local.py act                   # precheck, then the fast+dylint lanes via bosn -> act
    python3 ci/local.py act --lanes fast      # just one lane
    python3 ci/local.py act --title "[ci-full] ..."  # exercise a different tag selection

All logic lives in `ci/localrun/` (stdlib only, except where it shells
out to `uv run --no-project --with pyyaml` for `ci_lint` itself, which
needs PyYAML) -- this file is only argument parsing and dispatch, same
convention as `ci.py`/`ci/gates/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# pylint: disable-next=wrong-import-position
from ci.localrun.act_orchestrate import run_act  # noqa: E402

# pylint: disable-next=wrong-import-position
from ci.localrun.precheck import run_precheck  # noqa: E402


def _cmd_precheck(args: argparse.Namespace) -> int:
    return run_precheck(REPO_ROOT, title=args.title or "").exit_code


def _cmd_act(args: argparse.Namespace) -> int:
    return run_act(REPO_ROOT, lanes_arg=args.lanes, title=args.title or "")


def _cmd_act_inner(_args: argparse.Namespace) -> int:
    # Deliberately lazy: act_inner.py is only ever meant to run INSIDE the
    # bosn act-stack container (its own docstring), and importing it
    # eagerly at module load would pull that container-only code path
    # into every `ci/local.py` invocation, including plain `precheck`.
    # pylint: disable-next=import-outside-toplevel
    from ci.localrun.act_inner import main as act_inner_main

    return act_inner_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci/local.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_precheck = sub.add_parser(
        "precheck", help="ci_lint precheck --local (agent gate)"
    )
    p_precheck.add_argument(
        "--title", default=None, help="PR title to check tags against"
    )
    p_precheck.set_defaults(func=_cmd_precheck)

    p_act = sub.add_parser(
        "act", help="precheck, then run the Linux lanes through bosn -> act"
    )
    p_act.add_argument(
        "--lanes",
        default=None,
        help="comma-separated lane ids (default: ci.toml [local].lanes)",
    )
    p_act.add_argument(
        "--title", default=None, help="PR title driving the act event (tags -> plan)"
    )
    p_act.set_defaults(func=_cmd_act)

    p_inner = sub.add_parser(
        "act-inner", help=argparse.SUPPRESS
    )  # container-only, see ci/localrun/act_inner.py
    p_inner.set_defaults(func=_cmd_act_inner)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
