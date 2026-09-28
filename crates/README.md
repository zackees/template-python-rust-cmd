# `crates/`

The Rust workspace. Shaped by [zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)
(round 1) around one rule: **one published amalgam, several unpublished
crates that are each compiled and tested exactly once.**

## Layout

```
crates/
├── template/            # PUBLIC: the amalgam. pub use re-exports only.
├── template-cli/        # PUBLIC-ish: the `template-cli` binary. Bundled
│                         # into the wheel by soldr (bundle-bins).
├── template-py/         # PUBLIC-ish: the PyO3 `_native` extension.
└── private/              # publish = false. No [features]. No optional deps.
    ├── template-core/    # portable domain logic
    ├── template-json/    # a "feature" as a crate: hand-rolled JSON
    └── template-platform/ # the host-platform facade (see its README)
```

## Dependency direction (don't break this)

```
template-cli ──┐
               ├──► template ──┬──► template-core ──► template-platform
template-py ───┘               └──► template-json ──► template-core
```

`template` is the only crate `template-cli` and `template-py` depend
on — never `template-core`/`template-json` directly. `template` itself
carries no logic: it is `pub use` re-exports gated by Cargo features
(`json = ["dep:template-json"]`), so the private crates stay compiled
and unit-tested exactly once regardless of how many public surfaces
consume them.

## Why a public/private split

Before this round, `template-core`/`template-cli`/`template-py` were
flat siblings and `template-core` WAS the public surface. That meant
any new capability had to either bloat `template-core`'s own API or
grow a second public crate — no controlled way to ship an optional
capability without shipping its compile cost to every consumer.
`crates/private/*` fixes that: each private crate is `publish = false`,
declares no `[features]` of its own, and is wired into the public
surface with plain `dep:` feature gating on the `template` amalgam.
Adding a capability means adding a private crate and one line in
`template`'s `[features]` table — never a `#[cfg(feature = ...)]`
branch inside shared logic.

## The platform facade

`template-core` (and, transitively, everything else) reaches the OS
through exactly one door: `crate::platform::*`, aliased from
`template-platform`. See `crates/private/template-platform/README.md`
for the full pattern — it is the same shape soldr, zccache, and
kernal-api use, confined by `ci.toml`'s `[allow] platform-selector` /
`platform-code` and (eventually) a Dylint boundary check.

## Adding a new crate

1. `soldr cargo new --lib crates/private/<name>` (or the public
   `crates/<name>` if it genuinely needs its own published artifact —
   rare; prefer adding to `template`'s feature table instead).
2. Add `<name>` to `members` in the root `Cargo.toml`.
3. Use `version.workspace = true`, `edition.workspace = true`, and the
   other inherited package fields.
4. Private crates: `publish = false`, no `[features]`, no optional
   deps, `[lib] doctest = false`, and at least one real `#[test]`.
5. Add a README.md (this directory's `readme_guard` requires it).
6. Register the crate's test binary in `ci.toml`'s
   `[rust.tests].binaries` — an undeclared test binary is a precheck
   finding (`ci.yml#6` §2 group 7).

## Workspace conventions

- `Cargo.toml` at the repo root owns `version`, `edition`,
  `rust-version`, `license`, `repository`, `homepage`, and
  `[workspace.metadata.soldr] targets` (must match `ci.toml`'s
  `[platforms]`). Member crates inherit the package fields with
  `.workspace = true`.
- Shared deps go in `[workspace.dependencies]`; member crates pin
  with `{ workspace = true }`.
- Toolchain is pinned by `rust-toolchain.toml` at the repo root; do
  not override per-crate.
- Every Rust command goes through `soldr` (`soldr cargo ...`) — never
  bare `cargo`. See `ci/gates/*.py` for the canonical invocations.
