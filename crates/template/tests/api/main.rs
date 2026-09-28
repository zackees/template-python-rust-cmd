//! Public API surface test for the `template` amalgam.
//!
//! This is `crates/template`'s one integration-test link target
//! (`template:test:api` in `ci.toml`'s `[rust.tests].binaries`), and it
//! exercises both amalgam feature sets `ci.toml`'s `[rust] ship = [[],
//! ["json"]]` declares: run once with default (no) features and once
//! with `--features json`. The `#[cfg(feature = "json")]` test below
//! only runs — and only needs to compile — in the second invocation.

#[test]
fn version_banner_is_reexported_and_nonempty() {
    let banner = template::version_banner();
    assert!(!banner.is_empty());
}

#[test]
fn version_banner_names_a_known_host_os() {
    let banner = template::version_banner();
    assert!(
        ["windows", "linux", "macos"]
            .iter()
            .any(|os| banner.contains(os)),
        "banner {banner:?} did not name a known host OS",
    );
}

#[cfg(feature = "json")]
#[test]
fn json_feature_reexports_version_banner_json() {
    let json = template::version_banner_json();
    assert!(json.starts_with('{'));
    assert!(json.ends_with('}'));
    assert!(json.contains("version_banner"));
}

#[cfg(feature = "json")]
#[test]
fn json_payload_matches_the_plain_banner() {
    let banner = template::version_banner();
    let json = template::version_banner_json();
    assert!(json.contains(&banner));
}
