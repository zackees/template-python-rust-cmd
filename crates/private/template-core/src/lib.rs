//! Shared domain layer for the template scaffold.
//!
//! `publish = false`: this crate is never published on its own. It is
//! compiled and unit-tested exactly once, in this workspace, and the
//! public [`template`](../template) amalgam crate re-exports its API
//! surface with `pub use`.
//!
//! This crate reaches the OS in exactly one way: `crate::platform::*`
//! (the single-line alias below). No `#[cfg(target_os = ...)]`,
//! `#[cfg(windows)]`, `#[cfg(unix)]`, or `cfg!(...)` appears anywhere in
//! this crate — see `crates/private/template-platform` for why.

// The one line every platform-reaching consumer crate needs, per #6's
// facade contract: alias the platform crate, never name it inline at each
// call site.
pub(crate) use template_platform as platform;

/// A short banner combining this crate's own version with the running
/// host's OS name, sourced entirely through [`platform::host`].
pub fn version_banner() -> String {
    format!(
        "template-core v{} on {}",
        env!("CARGO_PKG_VERSION"),
        platform::host::os_name(),
    )
}

/// Entry point shared by every surface (`template-cli`, `template-py`)
/// that just wants to print the banner and exit successfully.
pub fn run_cli() -> anyhow::Result<()> {
    println!("{}", version_banner());
    Ok(())
}

// DELIBERATE VIOLATION (round 2F, run 3): a host `#[cfg]` outside the one
// allowed selector file (crates/private/template-platform/src/lib.rs) and
// outside its platforms/** tree. Must fail the `platform_boundary` Dylint
// Deny lint even though dylint-output-cache restores via an exact hit here
// (unchanged Cargo.lock) -- a restored cache must never hide a newly
// introduced violation in freshly checked-out source. Split across lines so
// ci-lint's cheap single-line LAYOUT-001 regex (`ci_lint/rules/layout.py`,
// `RUST_CFG_RE.search(line) and any(sel in line ...)`) does not also catch
// it on the same physical line -- this run specifically exercises Dylint's
// own pre-expansion, whitespace-collapsing scan
// (`dylints/platform_boundary/src/lib.rs`'s `compact` string), which is
// exactly why the fleet runs both a cheap static check AND Dylint on every
// PR (soldr#3284's lesson, ci.yml#6 §1). Reverted after run 3.
#[cfg(
    windows
)]
pub fn windows_only_marker() -> &'static str {
    "windows-only"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_banner_contains_the_crate_version() {
        assert!(version_banner().contains(env!("CARGO_PKG_VERSION")));
    }

    #[test]
    fn version_banner_contains_a_known_host_os() {
        let banner = version_banner();
        assert!(
            ["windows", "linux", "macos"]
                .iter()
                .any(|os| banner.contains(os)),
            "banner {banner:?} did not name a known host OS",
        );
    }

    #[test]
    fn run_cli_succeeds() {
        assert!(run_cli().is_ok());
    }
}
