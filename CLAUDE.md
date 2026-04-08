# Agent Notes

Read this before making structural changes.

## Repo Shape

- `crates/template-core`: logic that should be reusable from both bindings and CLI
- `crates/template-cli`: the native command entrypoint
- `crates/template-py`: `PyO3` wrapper exposing a stable Python API
- `src/template_python_rust_cmd`: thin Python package surface, packaging glue, and Python CLI shim

## Working Rules

- Prefer growing `template-core` first, then expose it through the CLI and `PyO3`.
- Keep release behavior documented in [docs/RELEASE.md](/C:/Users/niteris/dev/template-python-rust-cmd/docs/RELEASE.md).
- When changing commands, update [README.md](/C:/Users/niteris/dev/template-python-rust-cmd/README.md), [UPDATE.md](/C:/Users/niteris/dev/template-python-rust-cmd/UPDATE.md), and any affected `ci/` script skeleton.
- The wheel should expose `template_python_rust_cmd._native`.
