# Architecture

## Goal

Ship one Python wheel that exposes:

- a Python import surface backed by `PyO3` (`template_python_rust_cmd._native`)
- a command surface backed by a compiled Rust executable (`template-cli`,
  packaged at `template_python_rust_cmd._bin/`)

A consumer installs a single distribution and gets both deliverables.
A maintainer maintains one workspace and one CI matrix to feed both.

## CI Architecture

This template implements the canonical Rust+Python CI shape from
[`zackees/zccache#835`](https://github.com/zackees/zccache/issues/835).
Five load-bearing pieces:

1. **`./ci.sh` + `ci.py`.** Bash wrapper + PEP 723 dispatcher. Every
   gate invocation goes through here so the `--no-project --script`
   flag combo (which suppresses the maturin auto-build trap) lives in
   one place.
2. **`ci/gates/`.** Workspace-state checks. Each file exposes
   `def run() -> int`. Canonical ordering in `ci.py::GATE_ORDER`.
3. **`ci/hooks/`.** Agent-intent guards wired through
   `.claude/settings.json`. Only fires during Claude/Codex sessions.
4. **`.github/workflows/ci.yml`.** Thin orchestration — one runner per
   platform, every step is `./ci.sh <gate>`. Final `report-failures`
   step collects step outcomes.
5. **`action.yml` + `action/cleanup/action.yml`.** Composite action
   contract. Validated by `ci/gates/action_yaml.py` (structural) +
   `ci/gates/action_surface.py` (runtime binary surface match).

## Crate Responsibilities

### `crates/template-core`

- pure Rust domain logic
- no Python-specific concerns
- reusable from both the binary and the bindings crate
- the unit of behavior consistency between CLI and Python

### `crates/template-cli`

- argument parsing
- command execution
- stdout/stderr policy
- exit-code policy
- thin translation layer over `template-core`
- **subcommand surface is part of the composite-action contract** —
  `ci/gates/action_surface.py` verifies `action.yml`'s shell snippets
  only reference subcommands actually present in `--help`

### `crates/template-py`

- `PyO3` module definitions (`#[pymodule]`, `#[pyfunction]`)
- Python-friendly value conversion
- GIL boundary management
- thin translation layer over `template-core`

### `src/template_python_rust_cmd`

- package version and re-exports (`__init__.py`)
- Python wrapper around the extension (`bindings.py`)
- CLI shim that finds and execs the packaged native binary (`cli.py`)
- typing stub for the PyO3 surface (`_native.pyi`)

## Hook / Gate Split

| Concern                                | Home                       |
|----------------------------------------|----------------------------|
| Repo-state checks (every CI cycle)     | `ci/gates/*.py`            |
| Agent-intent checks (Claude sessions)  | `ci/hooks/*.py`            |
| File size budget (workspace-wide)      | `ci/gates/loc.py`          |
| File size budget (per-edit)            | `ci/hooks/loc_guard.py`    |
| README presence + size                 | `ci/hooks/readme_guard.py` |
| Bare cargo / unsafe `uv run` shape     | `ci/hooks/tool_guard.py`   |

## Non-goals

- duplicating core logic in Python
- embedding CLI-only behavior inside the `PyO3` module without an API
  use case
- maintaining separate CI infrastructure for the Python and Rust sides
- inline shell logic in `.github/workflows/ci.yml`
- gates that hard-couple to the agent's session (those are hooks)
