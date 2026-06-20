# template-python-rust-cmd

Canonical scaffold for a hybrid Rust + Python package with two native
deliverables:

- a bare Rust command shipped into the Python install as the CLI backend
- a `PyO3` extension module exposed to Python as a `.pyd` / `.so`

This repo is a **template** — every future hybrid Rust+Python project
seeded from `gh repo create --template zackees/template-python-rust-cmd`
inherits its CI gates, hooks, and uv-run discipline by construction. If
you're auditing the CI shape of a downstream consumer, the source of
truth is here.

The design rationale lives in [`zackees/zccache#835`](https://github.com/zackees/zccache/issues/835).
Each rule (1–10) has a one-line summary in [CLAUDE.md](./CLAUDE.md);
the rules and where they're implemented are also covered in
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Repo Layout

```text
.
├── Cargo.toml                  # Rust workspace root
├── pyproject.toml              # Python package + maturin build config
├── rust-toolchain.toml         # pinned Rust toolchain
├── action.yml                  # composite GitHub Action (root entry)
├── action/cleanup/action.yml   # paired post-job cleanup action
├── ci.sh                       # canonical CI dispatcher (bash wrapper)
├── ci.py                       # PEP 723 dispatcher (called by ci.sh)
├── ci/
│   ├── gates/                  # repo-state checks (run on every push)
│   ├── hooks/                  # agent-intent guards (Claude Code only)
│   ├── build_wheel.py          # release-flow: stage CLI + maturin build
│   └── publish.py              # release-flow: twine upload (guarded)
├── .github/workflows/ci.yml    # 8-platform matrix; every step is ./ci.sh
├── .claude/settings.json       # hook wiring for Claude Code
├── crates/
│   ├── template-core/          # reusable Rust library logic
│   ├── template-cli/           # bare Rust binary
│   └── template-py/            # PyO3 bindings crate
├── src/template_python_rust_cmd/
│   ├── __init__.py             # package version + public imports
│   ├── _native.pyi             # typing stub for the PyO3 surface
│   ├── bindings.py             # Python wrapper around the extension
│   ├── cli.py                  # Python entry that delegates to the native binary
│   └── _bin/                   # packaged native executable location (gitignored)
├── tests/                      # pytest fixtures + gate contract tests
└── docs/
    ├── ARCHITECTURE.md
    └── RELEASE.md
```

## Development Flow

```bash
./install        # verify uv, rustup, and pinned toolchain
./ci.sh fmt      # one gate
./ci.sh all      # every gate, continue past failures
./test           # cargo test + maturin develop + pytest (full build)
./publish        # guarded twine upload (must set _ENABLED first)
```

The dispatcher's flag discipline (`uv run --no-project --script`) is
load-bearing — see [`ci.sh`](./ci.sh) for the rationale. Bare `uv run`
on a maturin-backed project walks up to `pyproject.toml` and triggers a
full wheel build *before* your script starts, blowing up a 200 ms gate
into a 5+ minute cold compile. The wrapper exists to keep that flag
combo in one place.

## CI Surface

`./ci.sh all` runs every gate registered in `ci.py::GATE_ORDER`:

| Gate              | What it does                                                              |
|-------------------|---------------------------------------------------------------------------|
| `loc`             | Workspace LOC budget (warn > 1000, fail > 1500).                          |
| `fmt`             | `cargo fmt --all -- --check`.                                             |
| `clippy`          | `cargo clippy --workspace --all-targets -D warnings`.                     |
| `ruff`            | `ruff check` + `ruff format --check` over src / tests / ci.               |
| `build`           | `cargo check --workspace --all-targets`. **Fatal** — halts `all` on fail. |
| `test`            | `cargo test --workspace` + `maturin develop` + `pytest`.                  |
| `action_yaml`     | Structural check of `action.yml` + `action/cleanup/action.yml`.           |
| `action_surface`  | Subcommands referenced from `action.yml` exist in `template-cli --help`. |

`build` is the only fatal gate: a failing build would make every later
gate produce noise instead of signal. See [zccache#835 rule 7](https://github.com/zackees/zccache/issues/835).

## Packaging Intent

The wheel contains:

- the PyO3 extension module at `template_python_rust_cmd._native`, and
- the packaged native executable used by the `template-python-rust-cmd`
  console script, staged into `src/template_python_rust_cmd/_bin/`
  during build and removed afterward (gitignored).

`./build_wheel.py` orchestrates the maturin build, verifies the wheel
contains both deliverables, and cleans up. `./publish.py` is the
guarded upload — it exits until `_ENABLED = True` is set.

## Composite Action

Downstream consumers can pin this repo as a composite action:

```yaml
- uses: zackees/template-python-rust-cmd@v1
  with:
    version: "0.1.0"
- uses: zackees/template-python-rust-cmd/action/cleanup@v1
  if: always()
```

The action installs the package via `uv tool install`, exposes
`template-cli` on PATH, and emits `binary-path` as an output. The
cleanup sibling step removes the install and prunes the uv cache.
