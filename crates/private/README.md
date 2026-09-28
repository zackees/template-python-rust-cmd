# `crates/private/`

Every crate under this directory is `publish = false`. None of them
declare `[features]` or optional dependencies. Each is compiled and
unit-tested exactly once, and each is reachable from the outside world
only through the public [`template`](../template) amalgam's `pub use`
re-exports.

## Why a directory, not just a naming convention

`ci.toml`'s `[rust] private = "crates/private/*"` glob is a structural
check, not a naming one: ci-lint can walk this one directory and
assert every member sets `publish = false` and carries no `[features]`
table, without having to guess which top-level `crates/*` entries are
"really" private by name alone. A crate that needs to stop being
private moves out of this directory (and becomes its own published
crate, or — far more commonly — folds into `template`'s feature table
instead of graduating on its own).

## Members

| Crate | What it owns |
|---|---|
| `template-core` | Portable domain logic. Reaches the OS only via `crate::platform::*`. |
| `template-json` | Hand-rolled JSON encoding of the version banner — the template's example of "a feature is a crate." |
| `template-platform` | The host-platform facade: one `cfg_select!` selector, a cfg-free facility surface, native code confined to `src/platforms/**`. |

## Rules every crate here follows

- `publish = false` in `[package]`.
- No `[features]` table, no optional dependencies. Feature gating
  lives one layer up, in the public `template` amalgam's `dep:`
  wiring — never inside a private crate's own logic.
- `[lib] doctest = false` — these crates have no public API surface
  worth documenting with doctests; that job belongs to `template`.
- At least one real `#[test]` under `#[cfg(test)] mod tests` (a crate
  with a lib harness and zero tests is a precheck finding — an empty
  harness proves nothing).
- No `#[cfg(target_os = ...)]` / `#[cfg(windows)]` / `#[cfg(unix)]` /
  `cfg!(...)` anywhere except inside `template-platform`'s own
  `src/platforms/**` (and the one selector in its `lib.rs`). Everything
  else reaches the OS via `template-platform`'s facade.

## What does NOT belong here

- Anything with its own `[features]` table — that's the public
  `template` crate's job.
- Anything that needs to be independently version-pinned by a
  downstream consumer — publish it as its own top-level `crates/<name>`
  instead.
- Binaries. `template-cli` (the one binary this workspace ships) lives
  at `crates/template-cli`, one level up, because it is itself part of
  the public surface (bundled into the wheel).

## Adding a member

See `crates/README.md`'s "Adding a new crate" section — the steps are
the same, plus: register the new crate's test binary in `ci.toml`'s
`[rust.tests].binaries`, and wire it into `template`'s `[features]`
table if it should be reachable from outside the workspace at all.
