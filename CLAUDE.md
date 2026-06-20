# CLAUDE.md

Guidance for Claude Code (and any agent) working in this repository.

This is the **canonical hybrid Rust + Python template**. Practices that
land here propagate to every downstream consumer seeded by
`gh repo create --template zackees/template-python-rust-cmd`. Bias
toward keeping things tight and load-bearing; the leverage is high.

## Essential Rules

1. **Always run gates through `./ci.sh <gate>`.** Never paste
   `uv run python ci/gates/...` or `cargo clippy` directly into a
   command. The `ci/hooks/tool_guard.py` PreToolUse hook blocks bare
   forms and tells you why.
2. **Reserve full `uv run` (without `--no-project --script`) for named
   build entry points: `./test`, `./build`, `ci/build_wheel.py`,
   `./publish`, `./install`.** Everything else needs the protective
   flags — see `ci.sh` for the rationale.
3. **Every directory must have a `README.md` of ≥ 50 lines.** Enforced
   by `ci/hooks/readme_guard.py` on every edit.
4. **Source files ≤ 1000 lines (warn) / ≤ 1500 (fail).** Enforced both
   on every CI run (`ci/gates/loc.py`) and per-edit
   (`ci/hooks/loc_guard.py`). Split convention:
   `foo.rs` → `foo/mod.rs` + per-domain submodules with `pub use`
   re-exports in `mod.rs`.
5. **Logic lives in Python under `ci/`; YAML stays thin.** Every CI
   step is `run: ./ci.sh <gate>`. No multi-line shell embedded in
   `.github/workflows/ci.yml`.
6. **`build` is the only fatal gate.** A failing build halts the rest
   of the run because every downstream gate would produce noise
   against an uncompiled tree.

## Commands

```bash
./install                # verify toolchain shape (no maturin build)
./ci.sh fmt              # one gate
./ci.sh all              # every gate, continue past failures
./ci.sh --list           # show registered gates
./test                   # cargo test + maturin develop + pytest
./lint                   # convenience: fmt + clippy + ruff
```

For the full design rationale see
[zackees/zccache#835](https://github.com/zackees/zccache/issues/835).

## Hooks vs Gates

| Concern                                | Home                       |
|----------------------------------------|----------------------------|
| Repo-state checks (`git push` catches it) | `ci/gates/*.py`         |
| Agent-intent checks (only during sessions)| `ci/hooks/*.py`         |
| LOC budget across the workspace        | `ci/gates/loc.py`          |
| LOC growth on this edit                | `ci/hooks/loc_guard.py`    |
| README presence + size                 | `ci/hooks/readme_guard.py` |
| Bare cargo / unsafe `uv run` shape     | `ci/hooks/tool_guard.py`   |

If a rule would fire equally well on a `git push` from a terminal as
from a Claude edit, write it as a gate. If it needs to know what tool
is about to run, write it as a hook.

## Repo Shape

- `crates/template-core` — reusable Rust library logic
- `crates/template-cli` — bare Rust binary (the packaged CLI)
- `crates/template-py` — `PyO3` wrapper crate
- `src/template_python_rust_cmd/` — thin Python surface, packaging glue,
  Python CLI shim
- `ci/` — automation (see `ci/README.md`)
- `action.yml`, `action/cleanup/action.yml` — composite action contract

## Working Rules

- Grow `template-core` first; expose through `template-cli` and
  `template-py`. Don't let them diverge on core behavior.
- The wheel exposes `template_python_rust_cmd._native` (PyO3) AND a
  packaged `template-cli` binary under
  `src/template_python_rust_cmd/_bin/`. `ci/build_wheel.py` enforces
  both are present.
- When changing user-visible commands, update [README.md](./README.md),
  [UPDATE.md](./UPDATE.md), [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md),
  and any affected `ci/gates/<name>.py`.
- The release pipeline stages the compiled `template-cli` binary into
  `src/template_python_rust_cmd/_bin/` during the build, verifies the
  resulting wheel contains both native deliverables, and removes the
  staged binary afterward so the worktree stays clean.

## Where to ask questions

- Design rationale → [zackees/zccache#835](https://github.com/zackees/zccache/issues/835)
- Architecture → [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- Release flow → [docs/RELEASE.md](./docs/RELEASE.md)
- Linting policy → [LINTING.md](./LINTING.md)
