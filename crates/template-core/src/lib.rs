//! Shared domain layer for the template scaffold.

pub fn version_banner() -> &'static str {
    concat!("template-core ", env!("CARGO_PKG_VERSION"))
}

pub fn run_cli() -> anyhow::Result<()> {
    println!("{}", version_banner());
    Ok(())
}
