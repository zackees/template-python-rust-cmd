# `template-cli`

The bare Rust binary shipped with the Python package. Built into
`target/release/template-cli{,.exe}` (or `$CARGO_TARGET_DIR/release/`
when the wheel-build path runs — see `ci/build_wheel.py` for the pin),
then **injected directly into the wheel** at
`template_python_rust_cmd-<ver>.data/scripts/` by
`ci/build_wheel.py::inject_cli_into_wheel()`. Pip extracts the binary
straight into the venv's `Scripts/` (Win) or `bin/` (POSIX) on install
— no Python launcher in front of it. See #7 / #2 for why.

## Responsibilities

- argv parsing
- subcommand dispatch
- exit-code policy (0 ok, 1 user error, 2 unexpected)
- stdout for primary output, stderr for diagnostics
- thin translation of domain results into render-ready output

That's the whole list. Everything else (the actual logic) lives in
`template-core`.

## Surface contract

The subcommands this binary exposes are part of the **composite action
contract** — `action.yml` at the repo root shells out to them. Two CI
gates enforce this:

- `ci/gates/action_yaml.py` checks the action file's structure.
- `ci/gates/action_surface.py` checks that every subcommand
  referenced by `action.yml` shows up in `template-cli --help`.

Add a subcommand → update `action.yml` → both gates re-validate. If
you remove one, the cleanup step is the same in reverse.

## Why the binary is packaged into the wheel

A Python user doing `pip install template-python-rust-cmd` gets the
`template-cli` binary on PATH (the wheel ships it as a raw script in
`.data/scripts/`; pip handles the extraction). They don't need to
install Rust, and they don't need a separate distribution channel for
the binary. The wheel is one artifact for both deliverables;
`ci/build_wheel.py::verify_artifacts()` enforces that the script entry
is present alongside the PyO3 extension.

## Cross-compilation

CI builds on each platform's native runner (see the matrix in
`.github/workflows/ci.yml`). For local cross-builds, install the
target with `rustup target add <triple>` and pass `--target` to
`cargo build`. The `linux-x86-musl` and `linux-arm-musl` matrix
entries need `ziglang` (provisioned via `uv run --with ziglang`
inside `ci/build_wheel.py`).

## Linting

Both `cargo clippy -D warnings` and `cargo fmt --check` run via
`./ci.sh clippy` and `./ci.sh fmt`. Failing either fails the gate;
no `#[allow(...)]` without a justification comment.
