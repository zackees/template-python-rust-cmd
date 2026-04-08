# Architecture

## Goal

Ship one Python distribution that exposes:

- a Python import surface backed by `PyO3`
- a command surface backed by a compiled Rust executable

## Planned Responsibilities

### `crates/template-core`

- pure Rust domain logic
- no Python-specific concerns
- reusable from both the binary and bindings crate

### `crates/template-cli`

- argument parsing
- command execution
- stdout/stderr and exit-code policy
- thin translation layer over `template-core`

### `crates/template-py`

- `PyO3` module definitions
- Python-friendly value conversion
- thin translation layer over `template-core`

### `src/template_python_rust_cmd`

- package version and exports
- Python wrapper functions
- CLI shim that finds and executes the packaged native binary

## Non-goals

- duplicating core logic in Python
- embedding CLI-only behavior inside the `PyO3` module unless there is a direct API use case
