# template-python-rust-cmd

Canonical scaffold for a hybrid Rust + Python package with two native
deliverables:

- a Rust CLI binary (`template-cli`) shipped inside the Python wheel
- a `PyO3` extension module exposed to Python as a `.pyd` / `.so`

This repo is a **template** — every future hybrid Rust+Python project
seeded from `gh repo create --template zackees/template-python-rust-cmd`
inherits its crate layout, packaging shape, gates, hooks, and uv-run
discipline by construction. It is also the fleet **reference repo**
for the `rust-pypi-app` CI profile: [zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)
evolves that profile's `ci.toml` contract and `ci-lint` checker from
what actually works here, one measured round at a time. If you're
auditing the CI shape of a downstream consumer, or of the fleet
contract itself, the source of truth is here.

The gates/hooks/entry-point design rationale lives in
[`zackees/zccache#835`](https://github.com/zackees/zccache/issues/835)
(rules 1–10, summarized in [CLAUDE.md](./CLAUDE.md)); the crate layout
and packaging shape come from
[`zackees/ci.yml#6`](https://github.com/zackees/ci.yml/issues/6).

## CI contract

CI is declared, not scripted. The checked-in [`ci.toml`](./ci.toml)
(schema 3, profile `rust-pypi-app`) is the contract: platforms, crates,
suites, flows, tags and cache families. It does not generate YAML; it
bounds what `.github/workflows/ci.yml` (+ `ci-pre.yml`, the only two
workflow files) may do and decides what each run selects.

- **ci-lint precheck.** Every run starts with `ci-lint precheck` from
  [`zackees/ci.yml`](https://github.com/zackees/ci.yml), checked out at the
  exact commit pinned by `ci.toml`'s `linter` field (every workflow
  checkout of `zackees/ci.yml` uses the same SHA). It validates `ci.toml`
  and the workflows against fleet policy, then emits the run plan. The
  required check is the `CI OK` aggregator.
- **Tags.** Put a tag in the PR title (or commit subject) to change the
  selection on top of the flow (`pr`: `linux-x64`, `unit` + `smoke`):

  | Tag | Effect |
  |---|---|
  | `[ci-<platform>]`, e.g. `[ci-windows-arm64]` | add one platform lane |
  | `[ci-linux]` / `[ci-windows]` / `[ci-macos]` | add a platform group |
  | `[ci-full]` | all platforms + the `integration` suite |
  | `[ci-perf]` | add the non-gating `perf` suite |
  | `[ci-cache-save]` | allow a capped PR-scoped base cache save |
  | `[no-test]` | drop test suites (the PR is then not mergeable) |
  | `[release]` | release flow as a publish rehearsal |

- **Local loop.** `python3 ci/local.py precheck` runs the same precheck in
  seconds (the pre-push / agent Stop-hook gate);
  `python3 ci/local.py act` then runs the `fast` + `dylint` lanes locally
  through bosn -> act (`--lanes fast`, `--title "[ci-full] ..."`).

## Repo Layout

```text
.
├── ci.toml                     # the CI contract (see above)
├── Cargo.toml                  # Rust workspace root
├── pyproject.toml              # Python package + soldr build backend config
├── rust-toolchain.toml         # pinned Rust toolchain
├── action.yml                  # composite GitHub Action (root entry)
├── action/cleanup/action.yml   # paired post-job cleanup action
├── ci.py                       # canonical CI dispatcher (PEP 723, executable)
├── ci/
│   ├── gates/                  # repo-state checks (run on every push)
│   └── hooks/                  # agent-intent guards (Claude Code only)
├── .claude/settings.json       # hook wiring for Claude Code
├── crates/
│   ├── template/                # PUBLIC amalgam: pub use re-exports only
│   ├── template-cli/            # the template-cli binary
│   ├── template-py/             # PyO3 _native extension
│   └── private/                  # publish = false; compiled/tested once
│       ├── template-core/        # domain logic
│       ├── template-json/        # an optional feature, as a crate
│       └── template-platform/    # the host-platform facade
├── src/template_python_rust_cmd/
│   ├── __init__.py             # package version + public imports
│   ├── _native.pyi             # typing stub for the PyO3 surface
│   ├── bindings.py             # Python wrapper around the extension
│   └── platforms/               # host-platform facade (Python side)
│   # template-cli is NOT under the package — the soldr PEP 517 backend
│   # bundles it into the wheel's <name>-<ver>.data/scripts/ directory
│   # (`[tool.soldr.pep517] bundle-bins`), and pip drops it straight
│   # into the venv's Scripts/ (Win) or bin/ (POSIX) on install.
├── tests/                      # pytest fixtures + gate contract tests
└── docs/
    ├── ARCHITECTURE.md
    └── RELEASE.md
```

## Development Flow

```bash
./install        # verify uv, soldr, and the pinned toolchain
./ci.py fmt       # one gate
./ci.py all       # every gate, continue past failures
./test            # soldr cargo test + uv sync (soldr backend) + pytest
```

The dispatcher's flag discipline (`uv run --no-project --script`) is
load-bearing — see [`ci.py`](./ci.py) for the rationale. Bare `uv run`
on a soldr-backed project walks up to `pyproject.toml` and triggers a
full wheel build *before* your script starts, blowing up a 200 ms gate
into a multi-minute cold compile. The wrapper exists to keep that flag
combo in one place. Every Rust/wheel command goes through `soldr` —
never bare `cargo`/`maturin` (`ci/hooks/tool_guard.py` enforces this
for agent sessions; the future `ci-lint` precheck enforces it for
everyone).

## CI Surface

`./ci.py all` runs every gate registered in `ci.py::GATE_ORDER`:

| Gate              | What it does                                                              |
|-------------------|-----------------------------------------------------------------------------|
| `loc`             | Workspace LOC budget (warn > 1000, fail > 1500).                          |
| `fmt`             | `soldr cargo fmt --all -- --check`.                                        |
| `clippy`          | `soldr cargo clippy --workspace --all-targets --locked -D warnings`.       |
| `ruff`            | `ruff check` + `ruff format --check` over Python sources.                  |
| `build`           | `soldr cargo check --workspace --all-targets --locked`. **Fatal** — halts `all` on fail. |
| `test`            | `soldr cargo test --workspace --locked` + `uv sync` + `pytest`.            |
| `backend_smoke`   | `uv build --wheel` through the soldr PEP 517 backend (Linux-only).         |
| `action_yaml`     | Structural check of `action.yml` + `action/cleanup/action.yml`.            |
| `action_surface`  | Subcommands referenced from `action.yml` exist in `template-cli --help`.   |

`build` is the only fatal gate: a failing build would make every later
gate produce noise instead of signal. See [zccache#835 rule 7](https://github.com/zackees/zccache/issues/835).

## Packaging Intent

The wheel contains:

- the PyO3 extension module at `template_python_rust_cmd._native`
  (`abi3-py310` — one wheel per platform, no per-CPython-version
  matrix), and
- the `template-cli[.exe]` binary at
  `template_python_rust_cmd-<ver>.data/scripts/`, staged by the soldr
  backend's `bundle-bins` — pip extracts this straight into the venv's
  `Scripts/` (Windows) or `bin/` (POSIX) directory on install, with no
  Python wrapper in front of it. See
  [#7](https://github.com/zackees/template-python-rust-cmd/pull/7) for
  why we avoid `[project.scripts]` (Windows `os.execv` is emulated and
  races the shell prompt ahead of the child's stdout).

`uv build` (sdist + wheel) and `uv sync` (project install) both go
through the same backend; there is no separate `build_wheel.py`
script and no post-build wheel surgery. Publishing to PyPI is not
implemented on this branch — mock trusted-publish support is a later
`zackees/ci.yml#6` round's work (see `docs/RELEASE.md`).

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
Every `run:` step in both `action.yml` files is one line calling a
Python script under `action/` — no inline shell logic.

## Dylint cache reuse across commits

The `dylint` job's `dylint-output-cache` (compiled lint libraries plus
the checked `target/` tree, restored/saved through
`.github/actions/soldr`) now survives across commits, not just
same-commit reruns — [zackees/ci.yml#1](https://github.com/zackees/ci.yml/issues/1),
fixed by [zackees/setup-soldr#540](https://github.com/zackees/setup-soldr/issues/540)/`v0.9.82`.
Evidence, log excerpts, and the before/after key shape are recorded in
[`.github/actions/soldr/README.md`](./.github/actions/soldr/README.md).
