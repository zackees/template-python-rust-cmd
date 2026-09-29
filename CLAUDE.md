# CLAUDE.md

Guidance for Claude Code (and any agent) working in this repository.

This is the **canonical hybrid Rust + Python template**, and the fleet
reference repo for the `rust-pypi-app` CI profile
([zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)).
Practices that land here propagate to every downstream consumer seeded
by `gh repo create --template zackees/template-python-rust-cmd`, AND
feed back into `ci.toml`'s schema and `ci-lint` in `zackees/ci.yml`.
Bias toward keeping things tight and load-bearing; the leverage is high
in both directions.

## Essential Rules

1. **Always run gates through `./ci.py <gate>`.** Never paste `soldr
   cargo clippy ...` or `uv run python ci/gates/...` directly into a
   command. The `ci/hooks/tool_guard.py` PreToolUse hook blocks bare
   forms and tells you why.
2. **Never call bare `cargo`/`rustc`/`rustup`/`maturin`/`pip` for Rust
   or wheel work — use `soldr`** (`soldr cargo <cmd>`, `soldr wheel`,
   the soldr PEP 517 backend via `uv build`/`uv sync`). This is a fleet
   rule (`RUST-001`/`PKG-003` in `zackees/ci.yml`), not just a local
   convention; `soldr` invocations always pass `tool_guard.py`.
3. **Reserve full `uv run`/`uv sync` (without `--no-project --script`)
   for named build entry points: `./test`, `./install`.** Everything
   else needs the protective flags — see `ci.py` for the rationale.
4. **Every directory must have a `README.md` of ≥ 50 lines.** Enforced
   by `ci/hooks/readme_guard.py` on every edit.
5. **Source files ≤ 1000 lines (warn) / ≤ 1500 (fail).** Enforced both
   on every CI run (`ci/gates/loc.py`) and per-edit
   (`ci/hooks/loc_guard.py`). Split convention:
   `foo.rs` → `foo/mod.rs` + per-domain submodules, with `pub use`
   re-exports in `mod.rs` so the public path is unchanged.
6. **Logic lives in Python under `ci/`; YAML stays thin.** Every future
   CI step is a single line — `run: ./ci.py <gate>` or `run: python3
   ci/<script>.py ...` — never multi-line shell. (There is no
   `.github/workflows/ci.yml` on this branch right now — see "CI status
   on this branch" below.)
7. **`build` is the only fatal gate.** A failing build halts the rest
   of the run because every downstream gate would produce noise
   against an uncompiled tree.
8. **Host checks (`sys.platform`/`os.name`/`cfg(target_os)`) live in
   exactly two places**: `src/template_python_rust_cmd/platforms/` (Python)
   and `crates/private/template-platform/src/platforms/**` plus its one
   `cfg_select!` selector (Rust). Nowhere else — see `ci.toml`'s `[allow]
   platform-selector` / `platform-code`.

## CI status on this branch

`zackees/ci.yml#6` round 2 added the two workflows round 1 deferred:
`.github/workflows/ci-precheck.yml` (`workflow_call`, ≤ 30 s, no tool
installs — precheck's own gate group 2 rules) and
`.github/workflows/ci.yml` (the only entrypoint: `pull_request`,
`push: main`, `schedule`, `workflow_dispatch`). Round 3 added tag-selected
platform lanes and title-edit reuse. Jobs: `precheck` (now also computes
`ci_lint plan --reuse`'s platform-lane matrix + reuse map) → `fast`
(linux-x64 build/unit/wheel smoke; skipped when reused) + `dylint` (one
Linux job, host + every declared cross target; skipped when reused) +
`platform-build`/`platform-run` (tag-selected non-default platforms:
cross-compiled on Linux, executed with no Rust toolchain on each
platform's own runner) → `ci-ok` (the one required check, `if:
always()`, calls `ci_lint gate --reuse ... --event ...`). Every job's
display name carries its `ci_lint`-computed lane digest
(`fast [<digest>]`, `platform-run (<id>) [<digest>]`), which is also how
title-edit reuse matches an already-green job. `./ci.py all` still runs
locally and is what an agent should run before pushing — see "Commands"
below for the exact local precheck command.

## `ci.toml`

The repo's CI contract, checked by `ci-lint` (`zackees/ci.yml`, pinned by
commit SHA — see `ci.toml`'s `linter` field, which MUST match the SHA
`.github/workflows/ci-precheck.yml` and `ci.yml` check out into
`.ci-lint`, rule `CT-004`). It declares the six supported platforms, the
Rust workspace's public/private crate split and test-binary budget, the
Python packaging shape (soldr backend, `abi3-py310`, `bundle-bins`),
suites, flows, tags, and cache families. It does not generate YAML — it
bounds what the workflow may do and how it plans each run.

## Commands

```bash
./install                # verify uv + soldr + pinned toolchain (no wheel build)
./ci.py fmt               # one gate
./ci.py all               # every gate, continue past failures
./ci.py --list             # show registered gates
./test                    # soldr cargo test + uv sync (soldr backend) + pytest
./lint                    # convenience: fmt + clippy + ruff
```

## CI

### Local loop: `ci/local.py` (bosn -> act, zackees/ci.yml#6 §11)

```bash
python3 ci/local.py precheck                  # ~0.5s warm; ~1-2s cold (clones .ci-lint/ once)
python3 ci/local.py act                       # precheck, then fast+dylint via bosn -> act
python3 ci/local.py act --lanes fast          # just one lane
python3 ci/local.py act --title "[ci-full] …" # exercise a different tag selection
```

`precheck` wraps the exact command below, resolving `<ci.yml checkout>`
to a gitignored `.ci-lint/` clone/fetch of `ci.toml`'s `linter` pin
(no-op once already at that SHA — see `ci/localrun/ci_lint_checkout.py`):

```bash
PYTHONPATH=<ci.yml checkout> uv run --no-project --with pyyaml python3 -m ci_lint precheck --repo . --local
```

Run `python3 ci/local.py precheck` before every push that touches a
workflow, `ci.toml`, `Cargo.toml`, `pyproject.toml`, `bosn.toml`, or
`action.yml` — it is also the agent's PostToolUse hook on those paths
and its Stop hook (`.claude/settings.json` →
`ci/hooks/local_precheck_guard.py`), so this normally runs
automatically; run it by hand to iterate faster than the hook's
edit-triggered cadence.

`act` additionally requires `bosn`/`act`/`docker` on `PATH`: it runs the
selected `ci.yml` jobs for real, through the `bosn.toml` `act` stack
(pinned `act` 0.2.88 + a clang-patched runner image — see
`ci/docker/act/README.md` for zackees/ci.yml#6 D7), then audits the
local act cache store against `ci.toml [cache].budget`/`.retired`
(`ACT-001`, `ci/localrun/cache_audit.py`) so a local speedup can never
reward a cache family the remote policy forbids
(zackees/zccache#1760). A lane not in `ci.toml [local].lanes` (any
non-Linux platform) is reported "not covered locally", never as passed.
**Known gap:** a full green `act` run of `fast`/`dylint` needs a
`GITHUB_TOKEN` for `ci.yml`'s cross-repo `.ci-lint` checkout step, which
act (unlike real GitHub Actions) never auto-populates. This tool never
creates one; add your own PAT to a gitignored `.secrets` file at the
repo root (act's own default `--secret-file`) to opt in — see
`ci/localrun/README.md`'s "GITHUB_TOKEN and cross-repo checkouts".

The `dylint` job's own logic lives in `ci/dylint.py` (host + every
declared cross target, one Linux job — `soldr dylint prepare --target T`
then `soldr cargo dylint`, never a bare `cargo`/`cargo-dylint` call). The
`fast` job's logic lives in `ci/fast.py`. `.github/actions/soldr/` is the
ONLY `zackees/setup-soldr` call site (`ci.toml`'s
`[allow] setup-soldr.only-in`) — see its README before adding a lane that
needs a new setup-soldr input.

For the full design rationale see
[zackees/zccache#835](https://github.com/zackees/zccache/issues/835)
(the gates/hooks/entry-point shape) and
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) (the
crate layout, packaging, and `ci.toml` contract).

## Hooks vs Gates

| Concern                                | Home                       |
|----------------------------------------|----------------------------|
| Repo-state checks (`git push` catches it) | `ci/gates/*.py`         |
| Agent-intent checks (only during sessions)| `ci/hooks/*.py`         |
| LOC budget across the workspace        | `ci/gates/loc.py`          |
| LOC growth on this edit                | `ci/hooks/loc_guard.py`    |
| README presence + size                 | `ci/hooks/readme_guard.py` |
| Bare cargo/maturin / unsafe `uv run` shape | `ci/hooks/tool_guard.py` |
| Contract precheck on `.github/**`/`ci.toml`/`Cargo.toml`/`pyproject.toml`/`bosn.toml`/`action.yml` edits, and on every Stop | `ci/hooks/local_precheck_guard.py` |

If a rule would fire equally well on a `git push` from a terminal as
from a Claude edit, write it as a gate. If it needs to know what tool
is about to run, write it as a hook.

## Repo Shape

- `crates/template` — the public amalgam (published crate): `pub use`
  re-exports only, feature-gated `dep:` wiring
- `crates/template-cli` — the `template-cli` binary, bundled into the
  wheel via soldr
- `crates/template-py` — `PyO3` `_native` extension crate
- `crates/private/` — `publish = false` crates, each compiled and
  tested exactly once: `template-core` (domain logic),
  `template-json` (an optional feature, as a crate),
  `template-platform` (the host facade)
- `src/template_python_rust_cmd/` — Python package: bindings, package
  metadata, `platforms/` (host facade)
- `ci/` — automation (see `ci/README.md`)
- `action.yml`, `action/cleanup/action.yml` — composite action
  contract; every `run:` step is one line calling a script under
  `action/`

## Working Rules

- Grow `template-core` first; expose it through `template` (the
  amalgam), then `template-cli`/`template-py` pick it up automatically.
  Never let the CLI and the bindings diverge on core behavior.
- The wheel exposes `template_python_rust_cmd._native` (PyO3, no pure-
  Python fallback) AND ships the soldr-built `template-cli[.exe]` as a
  raw wheel script at `template_python_rust_cmd-<ver>.data/scripts/`
  (`[tool.soldr.pep517] bundle-bins`). Pip extracts that directly into
  the venv's `Scripts/` / `bin/` on install — no Python shim sits in
  front of it.
- When changing user-visible commands, update [README.md](./README.md),
  [UPDATE.md](./UPDATE.md), [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md),
  `ci.toml` (if the change affects platforms/suites/packaging), and any
  affected `ci/gates/<name>.py`.

## Where to ask questions

- Gates/hooks/entry-point design → [zackees/zccache#835](https://github.com/zackees/zccache/issues/835)
- Crate layout, packaging, `ci.toml` contract → [zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)
- Architecture → [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- Release flow → [docs/RELEASE.md](./docs/RELEASE.md)
- Linting policy → [LINTING.md](./LINTING.md)
