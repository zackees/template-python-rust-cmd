# `template-core`

Pure Rust domain logic. No Python, no CLI surface, no I/O policy. This
is the crate the other two depend on — keep it clean.

## What belongs here

- Types that model the problem domain.
- Algorithms over those types.
- Pure functions and value-semantics structs.
- `Result<T, anyhow::Error>` (or a domain-specific error enum) as the
  error contract — never `panic!` on recoverable conditions.

## What does NOT belong here

- `clap` or any other argv parser — that's `template-cli`'s job.
- `pyo3` decorators or `PyResult` — that's `template-py`'s job.
- `println!` / `eprintln!` for user output — domain code returns
  values; the binary decides how to render them.
- Process exits, signal handling, locale negotiation.
- Direct filesystem or network I/O unless it's the actual subject of
  the domain.

## Why this crate is load-bearing

`template-cli` and `template-py` translate domain types into their
respective surfaces. If domain behavior lives anywhere else, the two
surfaces will drift — the CLI ships one bug fix, the bindings ship a
different one, and consumers see inconsistency. The whole point of the
workspace shape is to make divergence structurally hard.

## Public surface

Everything exported from `lib.rs` is the contract the other two crates
see. Be conservative:

- Mark items `pub` only when a consumer needs them.
- Prefer `pub use` re-exports over inline `pub mod` so the surface is
  greppable in one place.
- Match the `template-py` Python surface name-for-name where possible
  — `do_thing()` in `template-core` should be `do_thing()` in both
  the CLI and the bindings.

## Testing

Unit tests live next to their code under `#[cfg(test)] mod tests`.
Integration tests live in `crates/template-core/tests/`. Both run as
part of `./ci.sh test` (which calls `cargo test --workspace`).
