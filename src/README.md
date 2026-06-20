# `src/`

The Python source layout for the wheel. Single package:
`template_python_rust_cmd`, declared in `pyproject.toml` as the
maturin `python-source`.

## Layout

```
src/template_python_rust_cmd/
├── __init__.py        # package version + re-exports
├── _native.pyi        # typing stub for the PyO3 surface
├── bindings.py        # Python wrapper around the extension module
├── cli.py             # Python entrypoint; delegates to the native binary
└── _bin/              # staged native executable (gitignored except .gitkeep)
```

## Why `src/`-layout instead of flat

Standard PEP 517 src-layout avoids the "accidentally importing
half-built package" failure mode where the working directory shadows
the installed package. Tools that read `pyproject.toml` (pytest, uv,
maturin) all support src-layout out of the box, so there's no friction
for it.

## What you can edit here

- `bindings.py` — the public Python API. Each function should be a
  near-1:1 reflection of an underlying `_native` call, with type
  annotations and a one-line docstring.
- `cli.py` — the Python CLI shim. Should stay tiny: locate the
  packaged binary, exec it, pass through the exit code. No business
  logic.
- `__init__.py` — package version, public re-exports. Don't import
  `_native` directly here; route through `bindings.py`.
- `_native.pyi` — optional typing stub mirroring the PyO3 surface.
  Keep it in sync with `crates/template-py/src/lib.rs`.

## What you should NOT edit here

- `_native*.pyd` / `_native*.so` / `_native*.dylib` — built by
  maturin, gitignored.
- `_bin/<binary>` — staged by `ci/build_wheel.py`, gitignored.
- Anything implementing domain logic — that belongs in `template-core`.

## Build modes

| Mode               | Command                                            | What's materialized                |
|--------------------|----------------------------------------------------|------------------------------------|
| In-place (dev)     | `uv run maturin develop --uv --profile dev`        | `_native*.pyd` next to `bindings.py`|
| Release wheel      | `uv run python ci/build_wheel.py`                  | wheel under `dist/`                |
| Sdist              | (included in `build_wheel.py`)                     | tarball under `dist/`              |
