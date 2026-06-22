# `src/`

The Python source layout for the wheel. Single package:
`template_python_rust_cmd`, declared in `pyproject.toml` as the
maturin `python-source`.

## Layout

```
src/template_python_rust_cmd/
├── __init__.py        # package version + re-exports
├── _native.pyi        # typing stub for the PyO3 surface
└── bindings.py        # Python wrapper around the extension module
```

The `template-cli` native binary is NOT shipped under this package
directory. It is injected into the wheel's
`<name>-<ver>.data/scripts/` directory at build time
(`ci/build_wheel.py`) and pip drops it straight into the venv's
`Scripts/` (Windows) or `bin/` (POSIX) directory at install time —
no Python wrapper sits in front of it. See
`template_python_rust_cmd/README.md` for the rationale (issue #2,
items 1 + 10).

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
- `__init__.py` — package version, public re-exports. Don't import
  `_native` directly here; route through `bindings.py`.
- `_native.pyi` — optional typing stub mirroring the PyO3 surface.
  Keep it in sync with `crates/template-py/src/lib.rs`.

## What you should NOT edit here

- `_native*.pyd` / `_native*.so` / `_native*.dylib` — built by
  maturin, gitignored.
- Anything implementing domain logic — that belongs in `template-core`.

## Build modes

| Mode               | Command                                            | What's materialized                |
|--------------------|----------------------------------------------------|------------------------------------|
| In-place (dev)     | `uv run maturin develop --uv --profile dev`        | `_native*.pyd` next to `bindings.py`|
| Release wheel      | `uv run python ci/build_wheel.py`                  | wheel under `dist/`                |
| Sdist              | (included in `build_wheel.py`)                     | tarball under `dist/`              |
