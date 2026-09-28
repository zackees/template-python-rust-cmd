# `template-py`

PyO3 extension crate that turns the `template` amalgam's Rust API into
a Python extension module. Built as a `cdylib` named `_native`, loaded
into Python as `template_python_rust_cmd._native`. Depends on
`template` (with the `json` ship feature) — never on
`template-core`/`template-json` directly (see `crates/README.md`'s
dependency-direction diagram).

## Responsibilities

- `#[pymodule]` / `#[pyfunction]` decorators.
- Python-friendly value conversion (Rust `String` → Python `str`,
  etc.).
- Thin translation over `template` — no domain logic.

If a behavior change needs to land in both the CLI and the Python API,
it goes in `template-core` (reached through `template`). This crate
just exposes it.

## Build

The soldr PEP 517 backend handles the heavy lifting — no direct
`maturin` invocation anywhere in this repo (`ci.toml`'s `[allow]
tools`, `ci.yml#6` round 1 `PKG-003`):

```bash
uv sync              # installs the project via the soldr backend (dev profile)
uv build --wheel     # release-shaped wheel build via the same backend
```

`pyproject.toml` declares `build-backend = "soldr"` and pins this
crate's manifest path via `[tool.maturin]` — soldr drives a pinned
maturin under the hood, so that section's *keys* stay maturin's own
config shape even though nothing invokes maturin directly:

```toml
[tool.maturin]
manifest-path = "crates/template-py/Cargo.toml"
module-name = "template_python_rust_cmd._native"
python-source = "src"
features = ["pyo3/extension-module"]
```

That `features` entry is crucial — `pyo3/extension-module` is the
build flag that lets the dylib not link against libpython at compile
time (it loads symbols at runtime instead). Combined with this
workspace's `abi3-py310` feature on the `pyo3` dependency, one wheel
per platform covers every supported CPython (`ci.toml`'s `[python]
abi3 = "cp310"`).

## Module name vs. crate name

- Crate: `template-py` (workspace member, name in `Cargo.toml`)
- Library: `_native` (`[lib].name`, becomes the dylib filename)
- Python import: `template_python_rust_cmd._native` (set by
  `module-name` in `[tool.maturin]`)

The three are intentionally different because the Rust crate name, the
dylib filename, and the Python import path serve different audiences.

## No Rust test harness

`[lib] test = false, doctest = false`: `#[pymodule]`/`#[pyfunction]`
code needs a live Python interpreter to exercise meaningfully, which
`cargo test -p template-py` cannot provide (it would just fail to
link). `tests/test_bindings.py` (Python side) is this crate's real
test suite, run against the built extension.

## Surface contract

`_native` has NO pure-Python fallback (`ci.toml`'s packaging check,
`PKG-005`): `src/template_python_rust_cmd/bindings.py` imports it
directly, unconditionally. If the extension isn't built, importing the
package fails loudly — that's the point.
