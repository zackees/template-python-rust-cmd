# `template`

The public API amalgam. This is the **only** crate in the workspace
published to crates.io, and the **only** crate `template-cli` and
`template-py` depend on for domain behavior. It carries no logic of
its own — every symbol is a `pub use` re-export from a private crate
under `crates/private/`.

## Why an amalgam instead of publishing `template-core` directly

Before [zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)
round 1, `template-core` itself was the shared/public crate. That
collapses two different questions into one crate: "what does the
domain logic do" and "what does a consumer of this workspace see."
Splitting them means a capability (`template-json`) can be added,
compiled once, unit-tested once, and toggled on/off for consumers
without ever touching `template-core`'s own API or compile graph.

## Features are `dep:` wiring, nothing else

```toml
[features]
json = ["dep:template-json"]
```

That is the **entire** feature surface. `ci.toml`'s `[rust] ship = [[],
["json"]]` names the only two feature sets this crate is ever compiled
or tested with. The one `#[cfg(feature = "json")]` in `lib.rs` gates
whether `template_json::version_banner_json` is re-exported at
all — never a behavioral branch. If you find yourself writing
`#[cfg(feature = "...")]` around actual logic anywhere in this crate,
that logic belongs in a private crate instead, gated by the presence
or absence of its `dep:` line.

## Public surface

```rust
pub use template_core::version_banner;          // always
#[cfg(feature = "json")]
pub use template_json::version_banner_json;      // only with `json`
```

Doc examples on these re-exports are this crate's API documentation —
`[lib] test = false` (no unit-test harness of its own; each re-export
is unit-tested once in its owning private crate), but doctests still
run (this workspace's 2024 edition merges them into one binary), so
keep them accurate.

## Testing

`template:test:api` in `ci.toml`'s `[rust.tests].binaries` —
`tests/api/main.rs`, this crate's one integration-test target. It is
run twice in a full validation pass: once with no features (the `[]`
ship set) and once with `--features json` (the `["json"]` ship set),
so both entries in `ci.toml`'s `[rust] ship` list are exercised
end-to-end, not just compiled.

```bash
soldr cargo test -p template --locked                    # [] ship set
soldr cargo test -p template --locked --features json    # ["json"] ship set
```

## Adding a re-export

1. Implement the capability in a new or existing crate under
   `crates/private/` (see that directory's README for the rules).
2. If it's optional, add a Cargo feature here that's nothing but
   `dep:<crate>` — no other wiring.
3. Add the `pub use` (gated by `#[cfg(feature = ...)]` if optional),
   with a doc comment/example.
4. Extend `tests/api/main.rs` to exercise it.
5. If it changes the ship sets, update `ci.toml`'s `[rust] ship` and
   this README.
