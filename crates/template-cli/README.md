# `template-cli`

The bare Rust binary shipped with the Python package. Depends on the
public `template` amalgam with the `json` ship feature set (`ci.toml`'s
`[rust] ship = [[], ["json"]]`) — never on `template-core`/`template-json`
directly (see `crates/README.md`'s dependency-direction diagram).

Built via `soldr cargo build -p template-cli` for local iteration; for
the shipped artifact, the soldr PEP 517 backend builds it and bundles
it into the wheel directly (`[tool.soldr.pep517] bundle-bins` in
`pyproject.toml`) — there is no post-build injection step anymore (the
former `ci/build_wheel.py`, removed in
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) round
1). It lands at `<name>-<ver>.data/scripts/template-cli[.exe]` inside
the wheel; pip extracts that straight into the venv's `Scripts/` (Win)
or `bin/` (POSIX) on install — no Python launcher in front of it. See
#7 / #2 for why.

## Responsibilities

- argv parsing (currently: `--json` selects the JSON-encoded banner;
  everything else falls through to the plain banner)
- stdout for primary output
- exit-code policy (always 0 today — this scaffold has no failure mode
  yet; a real subcommand should return non-zero on user error)
- thin translation of `template`'s re-exported domain results into
  render-ready output

That's the whole list. Everything else (the actual logic) lives in
`template-core`, reached only through `template`.

## Surface contract

The subcommands/flags this binary exposes are part of the **composite
action contract** — `action.yml` shells out to `template-cli
--version`/`--help` via `action/smoke_test.py`. Two CI gates enforce
this:

- `ci/gates/action_yaml.py` checks the action file's structure.
- `ci/gates/action_surface.py` checks that every subcommand referenced
  by `action.yml` shows up in `template-cli --help`.

## Why the binary is packaged into the wheel

A Python user doing `pip install template-python-rust-cmd` gets the
`template-cli` binary on PATH. They don't need to install Rust, and
they don't need a separate distribution channel for the binary. The
wheel is one artifact for both deliverables (`_native` + `template-cli`),
staged by soldr's `bundle-bins`.

## Testing

`template-cli:test:cli` in `ci.toml`'s `[rust.tests].binaries` —
`tests/cli/main.rs`, described in `tests/cli/README.md`. `[[bin]] test
= false`: the binary target itself carries no unit-test harness; its
behavior is proven by running the actual compiled executable.

## Cross-compilation

Every declared target in `ci.toml`'s `[platforms]` cross-compiles from
Linux through soldr: `soldr cargo check --workspace --locked --target
<triple>` (provisions target std automatically). No `rustup target
add`, no `ziglang` — that was the previous musl-via-Zig path; soldr's
catalogued cross toolchains replace it.

## Linting

Both `soldr cargo clippy --workspace --all-targets --locked -D
warnings` and `soldr cargo fmt --all -- --check` run via `./ci.sh
clippy` and `./ci.sh fmt`. Failing either fails the gate; no
`#[allow(...)]` without a justification comment.
