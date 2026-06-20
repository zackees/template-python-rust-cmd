# `template-py`

PyO3 wrapper that turns `template-core`'s Rust API into a Python
extension module. Built as a `cdylib` named `_native`, loaded into
Python as `template_python_rust_cmd._native`.

## Responsibilities

- `#[pymodule]` / `#[pyfunction]` / `#[pyclass]` decorators.
- Python-friendly value conversion (Rust `String` ↔ Python `str`,
  Rust `Result` ↔ Python exceptions, etc.).
- Holding the GIL boundary where it matters.
- Thin translation over `template-core` — no domain logic.

If a behavior change needs to land in both the CLI and the Python API,
it goes in `template-core`. This crate just exposes it.

## Build

Maturin handles the heavy lifting:

```
uv run maturin develop --uv --profile dev   # in-place build for tests
uv run python ci/build_wheel.py             # release wheel
```

`pyproject.toml` declares `maturin` as the build backend and pins this
crate's manifest path:

```toml
[tool.maturin]
manifest-path = "crates/template-py/Cargo.toml"
module-name = "template_python_rust_cmd._native"
python-source = "src"
features = ["pyo3/extension-module"]
```

That `features` entry is crucial — `pyo3/extension-module` is the
build flag that lets the dylib not link against libpython at compile
time (it loads symbols at runtime instead). Without it, the wheel
breaks on any Python interpreter that wasn't compiled with the same
ABI.

## Module name vs. crate name

- Crate: `template-py` (workspace member, name in `Cargo.toml`)
- Library: `_native` (`[lib].name`, becomes the dylib filename)
- Python import: `template_python_rust_cmd._native` (set by
  `module-name` in `[tool.maturin]`)

The three are intentionally different because the Rust crate name,
the dylib filename, and the Python import path serve different
audiences.

## Surface contract

The public Python API lives in
`src/template_python_rust_cmd/bindings.py` and wraps this crate's
extension module. Don't expose `_native` directly to package
consumers; wrap each function so the package can evolve its surface
independently of PyO3 decorators.
