//! PyO3 bindings for `template-python-rust-cmd`.
//!
//! Thin translation layer only: every function here just forwards to the
//! `template` amalgam (built with the `json` ship feature, same as
//! `template-cli`). Domain logic belongs in `template-core`/`template-json`,
//! never here — see `crates/template-py/README.md`.

use pyo3::prelude::*;

#[pyfunction]
fn version_banner() -> String {
    template::version_banner()
}

#[pyfunction]
fn version_banner_json() -> String {
    template::version_banner_json()
}

#[pymodule]
fn _native(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(version_banner, module)?)?;
    module.add_function(wrap_pyfunction!(version_banner_json, module)?)?;
    Ok(())
}
