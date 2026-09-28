//! `template-cli`: the native binary bundled into the wheel.
//!
//! Depends on the `template` amalgam with the `json` ship feature set
//! (`ci.toml`'s `[rust] ship = [[], ["json"]]`), so both re-exports —
//! `version_banner` and `version_banner_json` — are real, compiled code
//! paths here, not just amalgam-crate test coverage.

fn main() -> anyhow::Result<()> {
    let json_requested = std::env::args().skip(1).any(|arg| arg == "--json");
    if json_requested {
        println!("{}", template::version_banner_json());
    } else {
        println!("{}", template::version_banner());
    }
    Ok(())
}
