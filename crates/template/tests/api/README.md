# `crates/template/tests/api/`

`template`'s one integration-test target: `tests/api/main.rs`, which
Cargo's autodiscovery names `api` (the `tests/<name>/main.rs` layout,
same convention as `examples/<name>/main.rs` and
`benches/<name>/main.rs` — used here instead of a flat `tests/api.rs`
so a future growth in this test's helper code has somewhere to live
without cluttering `tests/`). This is `template:test:api` in
`ci.toml`'s `[rust.tests].binaries`.

## Why this is the amalgam's only test target

`template` itself has `[lib] test = false` — no unit-test harness,
because it carries no logic (see `crates/template/README.md`). Every
symbol it exports is already unit-tested once, in the private crate
that owns it. What this target proves instead is the **public API
surface**: that the re-exports actually exist, actually forward to the
right implementation, and actually compile under both of `ci.toml`'s
`[rust] ship` feature sets (`[]` and `["json"]`).

## What's tested here

- `version_banner` is re-exported and returns a non-empty string that
  names a known host OS (proves the `template-core` → `template-platform`
  chain reaches an actual value through the amalgam, not just that it
  compiles).
- Under `--features json` only (`#[cfg(feature = "json")]`):
  `version_banner_json` is re-exported, produces a JSON object, and
  that object's payload matches the plain banner.

## Running both ship sets

```bash
soldr cargo test -p template --locked                    # [] — 2 tests
soldr cargo test -p template --locked --features json    # ["json"] — 4 tests
```

A plain `soldr cargo test --workspace --locked` also runs this target
with `json` enabled, because `template-cli` depends on `template` with
`features = ["json"]` and Cargo's feature resolution unifies features
across a single test invocation. To exercise the `[]` set specifically
— which is what actually proves the feature is optional, not just
present — invoke `-p template` alone, as above.

## Adding a test here

Add the assertion to `main.rs` directly (single-file target; split
into `tests/api/<helper>.rs` + `mod` only if this genuinely outgrows
one file — unlikely for an API-surface smoke test). Gate anything that
depends on an optional feature with the matching `#[cfg(feature =
"...")]`, and update the "Running both ship sets" commands above if a
new feature is added to `template`.
