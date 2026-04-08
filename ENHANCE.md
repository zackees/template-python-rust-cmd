# Enhancement Notes

When expanding the scaffold:

- define the public Python API in `src/template_python_rust_cmd/bindings.py`
- define the Rust library boundary in `crates/template-core`
- keep the Python CLI shim thin and explicit
- do not let `template-cli` and `template-py` diverge on core behavior
