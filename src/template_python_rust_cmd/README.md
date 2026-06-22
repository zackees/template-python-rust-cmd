# `template_python_rust_cmd`

The actual Python package. Imported as
`import template_python_rust_cmd` after a `pip install`.

## Public modules

| Module        | Purpose                                                                 |
|---------------|-------------------------------------------------------------------------|
| `bindings`    | Python wrapper around the PyO3 extension. Public API surface.           |
| `__init__`    | Package version (`__version__`) and re-exports.                         |

## Internal modules

| Module        | Purpose                                                                 |
|---------------|-------------------------------------------------------------------------|
| `_native`     | Built by maturin from `crates/template-py`. Never import directly from outside this package — go through `bindings`. |
| `_native.pyi` | Optional typing stub for IDEs.                                          |

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

## CLI delivery (no Python shim)

The `template-cli` binary on PATH after `pip install` is the
cargo-built executable itself, **not** a Python launcher. It is
injected into the wheel's `<name>-<ver>.data/scripts/` directory by
`ci/build_wheel.py`'s post-processing step. Pip drops files in
`.data/scripts/` straight into the venv's `Scripts/` (Windows) or
`bin/` (POSIX) directory verbatim — `.exe` files are NOT wrapped.

Why no Python shim? On Windows, `[project.scripts]` generates a pip
console-script `.exe` whose `os.execv` is emulated as `CreateProcess`
+ parent exit. The Python shim returns to cmd.exe **before** the
spawned native binary finishes flushing stdout, so the next shell
prompt races ahead of `template-cli`'s output. Shipping the binary
as a raw wheel script bypasses the Python launcher entirely. See
[fbuild#747](https://github.com/FastLED/fbuild/pull/747) and
[issue #2](https://github.com/zackees/template-python-rust-cmd/issues/2)
items (1) + (10).

If you want to invoke the CLI from Python code, do it through
`subprocess`:

```python
import shutil
import subprocess

subprocess.run([shutil.which("template-cli"), "--help"], check=True)
```

## Why both an extension AND a binary?

Two different consumption stories:

- **In-process API.** A Python program wants to call into Rust
  without the cost of spawning a subprocess. → Use `bindings.py`.
- **Command surface.** A user (or shell script, or CI step) wants to
  run `template-cli foo --bar`. → Use the `template-cli` binary
  installed by the wheel's raw-script mechanism.

`template-core` makes both surfaces honor the same domain behavior.
