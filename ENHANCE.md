# Enhancement Notes

When growing the scaffold, the load-bearing decisions are:

## Where new logic goes

- **Reusable behavior** → `crates/template-core`. Both the CLI binary
  and the PyO3 bindings depend on this crate; growth here propagates
  to both consumers for free.
- **CLI commands** → `crates/template-cli`. Subcommands here become
  part of the composite action's surface contract — adding a
  subcommand means updating `action.yml`'s shell snippets and letting
  `ci/gates/action_surface.py` verify the binary still exports it.
- **Public Python API** → `src/template_python_rust_cmd/bindings.py`.
  Keep the wrapper thin: each function should be a near-1:1 reflection
  of the underlying `_native` call, with type annotations and a
  one-line docstring.
- **Native Rust boundary** → `crates/template-py/src/lib.rs`. PyO3
  decorators belong here, not in `template-core`.
- **CI logic** → `ci/gates/<name>.py`. Never in the workflow YAML.

## Where new infrastructure goes

- **New gate** → `ci/gates/<name>.py` exposing `def run() -> int`,
  registered in `ci.py::GATE_ORDER`.
- **New hook** → `ci/hooks/<name>.py` reading JSON from stdin,
  wired in `.claude/settings.json`.
- **New named build entry point** → script at repo root with shebang
  `#!/usr/bin/env bash` (route to `./ci.sh`) or
  `#!/usr/bin/env -S uv run --script` for inline Python; add its name
  to `ci/hooks/tool_guard.py::BUILD_ENTRY_POINTS` so the hook knows
  it's allowed to use full `uv run`.

## Invariants to preserve

- `template-cli` and `template-py` never diverge on core behavior.
- The Python CLI shim in `src/template_python_rust_cmd/cli.py` stays
  thin: it locates the packaged binary and delegates. No business
  logic.
- The wheel always contains both deliverables (PyO3 extension AND
  staged native binary). `ci/build_wheel.py::verify_artifacts()`
  enforces this — don't bypass it.
- The composite `action.yml` only references subcommands that exist
  in `template-cli --help`. `ci/gates/action_surface.py` checks this.

## When in doubt

Read [CLAUDE.md](./CLAUDE.md) for the essential rules, then
[UPDATE.md](./UPDATE.md) for the change checklist, then the relevant
gate's docstring for why the check exists.
