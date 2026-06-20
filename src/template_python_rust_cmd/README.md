# `template_python_rust_cmd`

The actual Python package. Imported as
`import template_python_rust_cmd` after a `pip install`.

## Public modules

| Module        | Purpose                                                                 |
|---------------|-------------------------------------------------------------------------|
| `bindings`    | Python wrapper around the PyO3 extension. Public API surface.           |
| `cli`         | Thin shim; locates `_bin/template-cli` and execs it. Used by the script entry point in `pyproject.toml`. |
| `__init__`    | Package version (`__version__`) and re-exports.                         |

## Internal modules

| Module        | Purpose                                                                 |
|---------------|-------------------------------------------------------------------------|
| `_native`     | Built by maturin from `crates/template-py`. Never import directly from outside this package — go through `bindings`. |
| `_native.pyi` | Optional typing stub for IDEs.                                          |
| `_bin/`       | Holds the packaged `template-cli{,.exe}` binary at install time. Staged by `ci/build_wheel.py` and removed afterward. |

## Wrapping the extension

```python
from template_python_rust_cmd._native import version_banner as _vb

def version_banner() -> str:
    """Return the human-readable version banner from the Rust core."""
    return _vb()
```

Why wrap instead of re-export? So the Python surface stays stable
even if the underlying PyO3 decorator's signature changes (e.g., a
new keyword argument added at the Rust layer). The wrapper is the
unit of API compatibility.

## CLI delegation

```python
def main() -> int:
    binary = packaged_binary_path()
    return subprocess.call([str(binary), *sys.argv[1:]])
```

`cli.main` is the entry point declared in
`pyproject.toml::project.scripts`. It's deliberately tiny — argv
parsing, exit codes, and behavior all live in the native binary; the
Python shim just hands control over.

## Why both an extension AND a binary?

Two different consumption stories:

- **In-process API.** A Python program wants to call into Rust
  without the cost of spawning a subprocess. → Use `bindings.py`.
- **Command surface.** A user (or shell script, or CI step) wants to
  run `template-cli foo --bar`. → Use the `template-python-rust-cmd`
  console script that delegates to the binary.

`template-core` makes both surfaces honor the same domain behavior.
