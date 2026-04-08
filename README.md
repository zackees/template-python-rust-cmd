# template-python-rust-cmd

Scaffold for a mixed Python/Rust package with two native deliverables:

- a bare Rust command shipped into the Python install as the CLI backend
- a `PyO3` extension module exposed to Python as a `.pyd`/`.so`

This repository is intentionally a skeleton. It documents the shape, workflows, and ownership boundaries an AI agent should follow when growing the project.

## Target Layout

```text
.
├── Cargo.toml                        # Rust workspace root
├── pyproject.toml                    # Python package + maturin build config
├── rust-toolchain.toml               # pinned Rust toolchain
├── ci/                               # lint / test / build / publish entrypoints
├── crates/
│   ├── template-core/                # reusable Rust library logic
│   ├── template-cli/                 # bare Rust binary
│   └── template-py/                  # PyO3 bindings crate
├── src/template_python_rust_cmd/
│   ├── __init__.py                   # package version + public imports
│   ├── _native.pyi                   # optional typing stub for PyO3 surface
│   ├── bindings.py                   # Python wrapper around the extension module
│   ├── cli.py                        # Python entrypoint that delegates to the native binary
│   └── _bin/                         # packaged native executable location
├── tests/
│   ├── test_bindings.py
│   ├── test_cli.py
│   └── test_version.py
└── docs/
    ├── ARCHITECTURE.md
    └── RELEASE.md
```

## Development Flow

```powershell
./install
./lint
./test
./publish
```

What each command should eventually mean:

- `./install`: bootstrap Python and Rust tooling for the pinned versions
- `./lint`: run Rust format/lints plus Python linting
- `./test`: build the local extension, run Rust tests, then Python tests
- `./publish`: guarded upload entrypoint; it exits until `_ENABLED = True` is set in `ci/publish.py`

## Packaging Intent

The end state should produce:

- a wheel containing `template_python_rust_cmd._native`
- a wheel containing the packaged native executable used by `template-python-rust-cmd`
- an sdist that can rebuild both

The release pipeline stages the compiled `template-cli` binary into `src/template_python_rust_cmd/_bin/` during the build, verifies the resulting wheel contains both native deliverables, and removes the staged binary afterward so the worktree stays clean.

The Python CLI wrapper should stay thin. Business logic belongs in Rust, and the Python package should either:

- call into the `PyO3` module for in-process APIs, or
- delegate to the packaged native binary for command-oriented flows
