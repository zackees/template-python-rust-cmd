//! `template-cli`: the native binary bundled into the wheel.
//!
//! Depends on the `template` amalgam with the `json` ship feature set
//! (`ci.toml`'s `[rust] ship = [[], ["json"]]`), so both re-exports —
//! `version_banner` and `version_banner_json` — are real, compiled code
//! paths here, not just amalgam-crate test coverage.
//!
//! ci.yml#41 leaf-crate probe (round M2-16): this file is the ONLY
//! source edited by this probe. `template-cli` is a true leaf --
//! nothing in the workspace depends on it -- so a correct
//! preserve-source-mtimes replay should recompile only this crate
//! (plus anything that cross-compiles/links it), leaving
//! template-platform, template-core, template-json, template, and
//! template-py as cache hits.

fn main() -> anyhow::Result<()> {
    let json_requested = std::env::args().skip(1).any(|arg| arg == "--json");
    if json_requested {
        println!("{}", template::version_banner_json());
    } else {
        println!("{}", template::version_banner());
    }
    Ok(())
}
