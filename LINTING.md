# Linting Policy

This file describes the intended linting contract for the scaffold.

## Rust

Expected checks:

- `cargo fmt --all --check`
- `cargo clippy --workspace --all-targets -- -D warnings`

## Python

Expected checks:

- `uv run ruff check src tests ci`

## Agent Maintenance Rule

If new tooling is introduced:

- wire it into [ci/lint.py](/C:/Users/niteris/dev/template-python-rust-cmd/ci/lint.py)
- update [README.md](/C:/Users/niteris/dev/template-python-rust-cmd/README.md)
- explain why it belongs here instead of the language-native defaults
