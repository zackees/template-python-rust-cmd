"""CI helper package.

Two structured sub-packages:

  - `ci.gates.*` — workspace-state checks invoked by `./ci.sh <gate>`;
    runs on every CI cycle and on developer laptops.
  - `ci.hooks.*` — agent-intent guards wired through `.claude/settings.json`;
    runs only during a Claude/Codex session.

Release-flow helpers (`build_wheel.py`, `publish.py`) live alongside
the gates package and are the documented opt-in to the full maturin
context. See `ci/README.md` for the directory map and
[zackees/zccache#835](https://github.com/zackees/zccache/issues/835)
for the design rationale.
"""
