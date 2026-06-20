# Linting Policy

The CI gates that lint the repo, in canonical order.

## Rust

Two gates, both via `./ci.sh`:

| Gate              | Command                                                                |
|-------------------|------------------------------------------------------------------------|
| `./ci.sh fmt`     | `cargo fmt --all -- --check`                                           |
| `./ci.sh clippy`  | `cargo clippy --workspace --all-targets -- -D warnings`                |

Both run on every push and locally. Failing format is fixable with
`cargo fmt --all`; failing clippy points at a real issue (a denied
warning, an unused-result, etc.).

## Python

One gate covering lint + format:

| Gate              | Command                                                                |
|-------------------|------------------------------------------------------------------------|
| `./ci.sh ruff`    | `ruff check src tests ci ci.py` + `ruff format --check src tests ci ci.py` |

`ruff` is provisioned at script-time via `uv run --no-project --with
ruff>=0.8`, so it never triggers a maturin build to lint a few `.py`
files.

## LOC Budget

| Gate              | Threshold                          |
|-------------------|------------------------------------|
| `./ci.sh loc`     | warn > 1000, fail > 1500 (per file)|

Split convention printed on every failure:
`foo.rs` → `foo/mod.rs` + per-domain submodules, with `pub use`
re-exports in `mod.rs` so the public path is unchanged. The
per-edit half lives in `ci/hooks/loc_guard.py`.

## Agent Maintenance Rule

If you add new tooling:

- write the gate at `ci/gates/<name>.py` with `def run() -> int`
- register it in `ci.py::GATE_ORDER`
- add a step to `.github/workflows/ci.yml`
- update [README.md](./README.md) and this file
- explain in the gate's docstring why this gate belongs here instead
  of the language-native default

## What's intentionally NOT here

- **`mypy` / `pyright`.** Type-checking the thin Python surface adds
  more noise than signal for a template; downstream consumers that
  grow real Python should add a gate. Pattern: `ci/gates/pyright.py`
  with `subprocess.run(["uv", "run", "--no-project", "--with",
  "pyright", "pyright", "src", "tests"])`.
- **`dylint`.** Rust dylints are heavy (large dependency graph) and
  the canonical template doesn't depend on any. Downstream consumers
  add `ci/gates/dylint.py` if they want it; the Docker-for-Rust gate
  shape (zccache#835 rule 11) is the right amplifier when they do.
