#!/usr/bin/env bash
# Canonical CI dispatcher for this hybrid Rust+Python repo.
#
# WHY this exists (and not a bare `uv run python ci.py`):
#   With a maturin-backed pyproject.toml at the repo root, a bare `uv run`
#   walks up the tree, discovers pyproject.toml, and triggers a full maturin
#   wheel build *before* running anything. A 200 ms fmt-check blows up to a
#   5+ minute cold build. `--no-project` suppresses that discovery, and
#   `--script` reads PEP 723 inline deps from ci.py so the gate runs in an
#   isolated venv with just what it needs.
#
# Both flags are load-bearing. See zackees/zccache#835 rules 2-3 for the
# full rationale.
#
# Reserve full `uv run` (without these flags) for named build entry points
# like `./test`, `./build`, `ci/build_wheel.py` — places that genuinely
# need the maturin wheel + extension module materialized.

set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec uv run --no-project --script "$script_dir/ci.py" "$@"
