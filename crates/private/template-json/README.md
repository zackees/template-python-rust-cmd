# `template-json`

Hand-rolled JSON encoding of `template-core`'s version banner. This
crate exists to prove one specific shape from
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6): **an
optional capability is a crate, wired into the public `template`
amalgam with plain `dep:` feature gating — never a
`#[cfg(feature = ...)]` branch inside shared logic.**

`publish = false`: see `crates/private/README.md` for the rules every
crate under `crates/private/` follows.

## What belongs here

- The one thing this crate does: `version_banner_json()`, a minimal
  JSON encoding of `template_core::version_banner()`.
- Its own hand-rolled string-escaping helper.
- Unit tests for both.

## What does NOT belong here — and why "no new third-party deps" is load-bearing

This crate has exactly one dependency: `template-core` (a path dep,
same workspace). **No `serde`, no `serde_json`, nothing from
crates.io.** That's deliberate, not an oversight: the point of this
crate existing at all is to demonstrate that turning a capability
on/off (`template`'s `json` feature) costs exactly one crate's worth of
compile time — not a third-party dependency tree. If this template
ever needs *real* JSON (arbitrary structured data, not one fixed
string), that is a decision for whatever consumes this amalgam, made
explicitly — not something that sneaks in here because the string
concatenation got awkward.

## The escaper

`escape_json_string` handles the JSON string-escape set this crate's
one payload can plausibly contain: `"`, `\`, and control characters
(encoded as `\n`/`\r`/`\t` or `\u00XX`). It is not a general-purpose
JSON encoder and must not grow into one in place — see above.

## Public surface

```rust
pub fn version_banner_json() -> String;
```

That's the entire public surface. `template`'s `[features] json =
["dep:template-json"]` re-exports it as `template::version_banner_json`
when the amalgam is built with `--features json` — one of the exactly
two ship sets `ci.toml`'s `[rust] ship` allows (`[]` and `["json"]`).

## Testing

Unit tests live under `#[cfg(test)] mod tests` — `template-json:lib`
in `ci.toml`'s `[rust.tests].binaries`. `[lib] doctest = false`, same
as every crate under `crates/private/`. Run with `soldr cargo test
--workspace --locked`.
