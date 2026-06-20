# `tests/`

Python-side test suite. Picked up by `pytest` per the configuration in
`pyproject.toml::[tool.pytest.ini_options]`.

## What lives here

| File              | What it tests                                                          |
|-------------------|------------------------------------------------------------------------|
| `test_bindings.py`| The PyO3 extension surface via `template_python_rust_cmd.bindings`.    |
| `test_cli.py`     | The Python CLI shim's binary-discovery logic.                          |
| `test_version.py` | Package `__version__` is non-empty and matches the manifest.           |
| `test_gates.py`   | Each gate registered in `ci.py::GATE_ORDER` is importable and exposes `def run() -> int`. The contract test for the gates infra itself. |

## What lives in `crates/*/tests/` instead

- Pure Rust unit tests live alongside the code under
  `#[cfg(test)] mod tests`.
- Rust integration tests live under `crates/<name>/tests/`.

Both run as part of `./ci.sh test` (which calls `cargo test
--workspace` then `pytest`).

## Conventions

- **No mocks of the extension module.** Test the real `_native` build.
  Mocking PyO3 functions defeats the point of having an extension.
- **Use `pytest.fixture` for binary discovery / temp dirs** rather
  than hardcoding paths. The CI matrix runs on 8 platforms; paths
  differ.
- **Mark slow tests with `@pytest.mark.slow`** and skip by default.
  The gate target should be sub-30s on a developer laptop; longer
  scenarios go in a separate workflow.
- **Async tests use `pytest-asyncio`** if the binding ever grows an
  async surface (not currently — but reserve the marker).

## Why the gate contract test exists

`tests/test_gates.py` asserts that:

1. Every name in `ci.py::GATE_ORDER` resolves to a module under
   `ci/gates/`.
2. Each module exposes `def run() -> int`.
3. Calling `run()` doesn't `raise` (it may return non-zero — that's
   fine; the test just verifies the contract shape).

This is what the issue's actionable TODO list calls for explicitly —
once the contract is locked, future gate additions can't accidentally
ship a broken signature.

## Running just the Python tests

```bash
uv run pytest                    # all
uv run pytest tests/test_cli.py  # one file
uv run pytest -k version         # by name
```

These need the maturin extension materialized first (`uv run maturin
develop --uv --profile dev`). The `test` gate handles that for you.
