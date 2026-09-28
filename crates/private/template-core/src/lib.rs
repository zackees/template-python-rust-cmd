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
        "template-core {} ({})",
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
