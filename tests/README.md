# `tests/`

Python-side test suite. Picked up by `pytest` per the configuration in
`pyproject.toml::[tool.pytest.ini_options]`.

## What lives here

| File              | What it tests                                                          |
|-------------------|------------------------------------------------------------------------|
| `test_bindings.py`| The PyO3 extension surface via `template_python_rust_cmd.bindings`.    |
| `test_cli.py`     | `template-cli` is on PATH after the project is installed (staged into the venv by the soldr backend's `bundle-bins`) and `template-cli --version` exits 0. **Does not skip** — a missing binary is a packaging-path failure, not an environment gap ([zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) round 1). Uses `template_python_rust_cmd.platforms.cli_binary_name()`, not an inline `os.name` check. |
| `test_version.py` | Package `__version__` is non-empty and matches the manifest.           |
| `test_gates.py`   | Each gate registered in `ci.py::GATE_ORDER` is importable and exposes `def run() -> int`. The contract test for the gates infra itself. |

## What lives in `crates/*/tests/` instead

- Pure Rust unit tests live alongside the code under
  `#[cfg(test)] mod tests` (`template-core`, `template-json`,
  `template-platform`).
- Rust integration tests live under `crates/template/tests/api/` and
  `crates/template-cli/tests/cli/`.

Both run as part of `./ci.sh test` (which calls `soldr cargo test
--workspace --locked`, then `uv sync`, then `pytest`).

## Conventions

- **No mocks of the extension module.** Test the real `_native` build.
  Mocking PyO3 functions defeats the point of having an extension.
- **Use `pytest.fixture` for binary discovery / temp dirs** rather
  than hardcoding paths. `ci.toml` declares six supported platforms;
  paths differ.
- **Mark slow tests with `@pytest.mark.slow`** and skip by default.
  The gate target should be sub-30s on a developer laptop; longer
  scenarios go in a separate workflow.
- **Async tests use `pytest-asyncio`** if the binding ever grows an
  async surface (not currently — but reserve the marker).
- **No `sys.platform`/`os.name` inline.** Import
  `template_python_rust_cmd.platforms` instead — see that module's
  README for why (`ci.toml`'s `[allow] platform-code`).

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
uv sync                          # installs the project via the soldr backend first
uv run --no-sync pytest                    # all
uv run --no-sync pytest tests/test_cli.py  # one file
uv run --no-sync pytest -k version         # by name
```

These need the `_native` extension (and, for `test_cli.py`,
`template-cli`) materialized first — `uv sync` does that through the
soldr PEP 517 backend (never a direct `maturin` call). The `test` gate
(`./test` / `ci/gates/test.py`) runs both steps for you.
