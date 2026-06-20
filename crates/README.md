# `crates/`

The Rust workspace. Three crates share `template-core`'s logic; the
binary and the PyO3 bindings depend on it but never on each other.

## Layout

```
crates/
├── template-core/      # pure Rust domain logic; no Python concerns
├── template-cli/       # bare Rust binary; the packaged CLI backend
└── template-py/        # PyO3 wrapper; exposes Rust to Python
```

## Dependency direction (don't break this)

```
template-cli ──┐
               ├──► template-core
template-py ───┘
```

Anything that needs to behave the same in Python AND in the CLI lives
in `template-core`. The other two crates translate domain types into
their respective surfaces — argv parsing + exit codes for the CLI,
PyO3 conversions for the bindings.

## Adding a new crate

1. `cargo new --lib crates/<name>` (or `--bin` for an executable).
2. Add `<name>` to `members` in `Cargo.toml` at the repo root.
3. Use `version.workspace = true`, `edition.workspace = true`, and the
   other inherited package fields — the workspace owns version
   alignment with the Python wheel.
4. Add a README.md (this directory's `readme_guard` requires it).
5. The new crate is automatically picked up by `cargo check
   --workspace` (the `build` gate) and `cargo clippy --workspace` (the
   `clippy` gate). No CI changes needed.

## Workspace conventions

- `Cargo.toml` at the repo root owns `version`, `edition`,
  `rust-version`, `license`, `repository`, `homepage`. Member crates
  inherit them with `.workspace = true`.
- Shared deps go in `[workspace.dependencies]`; member crates pin
  with `{ workspace = true }`.
- Toolchain is pinned by `rust-toolchain.toml` at the repo root; do
  not override per-crate.

## Where new logic goes

- **Reusable domain logic** → `template-core`.
- **CLI subcommands** → `template-cli`. Adding a subcommand means
  updating `action.yml`'s shell snippets too (and
  `ci/gates/action_surface.py` will verify the binary surface
  matches).
- **Python-callable APIs** → `template-py`. Keep PyO3 decorators
  here, not in `template-core`.
