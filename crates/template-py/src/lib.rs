use pyo3::prelude::*;

#[pyfunction]
fn version_banner() -> &'static str {
    template_core::version_banner()
}

#[pymodule]
fn _native(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(version_banner, module)?)?;
    Ok(())
}
