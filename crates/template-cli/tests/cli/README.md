# `crates/template-cli/tests/cli/`

`template-cli`'s one integration-test target: `tests/cli/main.rs`,
which Cargo's autodiscovery names `cli` (the `tests/<name>/main.rs`
layout — see `crates/template/tests/api/README.md` for why this
template prefers it over a flat `tests/cli.rs`). This is
`template-cli:test:cli` in `ci.toml`'s `[rust.tests].binaries`.

## Why this runs the real binary, not library code

`template-cli`'s `[[bin]] test = false` — there is no in-process unit
harness for the bin target. This is deliberate: the whole point of
`template-cli` is that it's a shipped executable, and the only thing
worth proving is "the compiled binary, run as a subprocess, behaves
correctly" — the exact contract `tests/test_cli.py` (Python side)
checks against the *installed wheel's* binary. Testing library code
in-process would prove something adjacent, not the actual artifact.

## How it works

Every test spawns `env!("CARGO_BIN_EXE_template-cli")` — a Cargo-provided
compile-time constant pointing at the just-built binary for this test
run — via `std::process::Command`, then asserts on exit status and
stdout.

## What's tested here

- No arguments: exits 0, prints a non-empty banner.
- `--version`: exits 0, prints a non-empty banner (this binary doesn't
  special-case `--version` today; it's accepted and ignored the same
  as any other unrecognized flag — this test documents that behavior
  rather than assuming argv parsing that doesn't exist yet).
- `--json`: exits 0, prints a JSON object (`{...}`), exercising the
  `template` amalgam's `json` feature end to end through the actual
  binary, not just through `crates/template/tests/api/`.

## Relationship to the Python-side CLI test

`tests/test_cli.py` (repo root) checks the same `--version` contract
against the binary resolved from `PATH` after a real wheel install.
This target checks it against the binary Cargo just built. Both need
to pass — one proves the Rust binary's own behavior, the other proves
packaging didn't break on the way to a wheel.

## Adding a test here

Add the assertion to `main.rs` directly. If `template-cli` grows real
subcommands (`clap` or similar), also update `action.yml`'s smoke test
(`action/smoke_test.py`) and `crates/template-cli/README.md`'s
"Surface contract" section — `ci/gates/action_surface.py` checks that
`action.yml` only references subcommands the binary actually exposes.
