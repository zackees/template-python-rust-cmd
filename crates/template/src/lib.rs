//! `template`: the public API amalgam for `template-python-rust-cmd`.
//!
//! This is the only crate in the workspace published to crates.io. It
//! carries **no logic of its own** — every symbol below is a `pub use`
//! re-export from a private crate under `crates/private/`, wired through
//! Cargo features so a consumer opts into exactly the ship set they need.
//! `ci.toml`'s `[rust] ship = [[], ["json"]]` names the only two feature
//! sets this crate is ever compiled or tested with; both are exercised by
//! `tests/api/main.rs`, this crate's one integration test target.
//!
//! The `json` feature gates exactly one thing: whether the optional
//! `dep:template-json` re-export below is visible. There is no
//! behavioral branch anywhere in this crate — `#[cfg(feature = "json")]`
//! only decides whether a name exists, never what it does.
//!
//! `[lib] test = false`: this crate has no unit-test harness of its own —
//! `template-core`, `template-json`, and `template-platform` each own
//! their unit tests once, and this crate only re-exports their public
//! surface. Doctests on the items below still run (this workspace uses
//! the 2024 edition's merged-doctest binary), so keep doc examples here
//! accurate: they are this amalgam's API-surface documentation.

/// A short banner combining the core crate's version with the running
/// host's OS name.
///
/// ```
/// let banner = template::version_banner();
/// assert!(!banner.is_empty());
/// ```
pub use template_core::version_banner;

/// The version banner encoded as a minimal JSON object. Present only when
/// this crate is built with the `json` feature (`dep:template-json`).
#[cfg(feature = "json")]
pub use template_json::version_banner_json;
