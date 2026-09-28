# `ci/`

Repo automation. Two structured sub-packages; the release-flow scripts
that used to live here (`build_wheel.py`, `publish.py`) were removed in
zackees/ci.yml#6 round 1 — see below.

## Layout

```
ci/
├── gates/                 # workspace-state checks (run by ./ci.sh)
│   ├── __init__.py
│   ├── loc.py             # LOC budget gate (warn 1000 / fail 1500)
│   ├── fmt.py             # soldr cargo fmt --check
│   ├── clippy.py          # soldr cargo clippy -D warnings
│   ├── ruff.py            # ruff check + format --check
│   ├── build.py           # soldr cargo check --workspace (FATAL in `all`)
│   ├── test.py            # soldr cargo test + uv sync (soldr backend) + pytest
│   ├── backend_smoke.py   # uv build --wheel through the soldr backend
│   ├── action_yaml.py     # composite-action structural check
│   └── action_surface.py  # subcommand-vs-binary surface check
└── hooks/                 # agent-intent guards (run by Claude Code)
    ├── tool_guard.py
    ├── readme_guard.py
    ├── loc_guard.py
    └── check-on-start.py
```

## Two halves: gates vs. hooks

| Concern                                | Home                       |
|----------------------------------------|----------------------------|
| Runs on every CI cycle                 | `ci/gates/*.py`            |
| Runs only during a Claude/Codex session| `ci/hooks/*.py`            |
| Workspace-wide LOC budget              | `ci/gates/loc.py`          |
| Per-edit LOC budget                    | `ci/hooks/loc_guard.py`    |
| README presence + size                 | `ci/hooks/readme_guard.py` |
| Bare cargo/maturin/uv shape ban        | `ci/hooks/tool_guard.py`   |

If a rule would fire on a `git push` from a terminal the same way it
would fire on a Claude edit, write it as a gate. If it needs to see
what tool is about to run, write it as a hook. See [zccache#835 rule 9](https://github.com/zackees/zccache/issues/835).

## What happened to `build_wheel.py` and `publish.py`

Removed in zackees/ci.yml#6 round 1 (this repository's `ci.toml`
contract, §13):

- **`build_wheel.py`** manually built `template-cli` via cargo, drove
  maturin for the PyO3 extension, then hand-patched the resulting
  wheel's zip/RECORD to inject the binary. That whole dance is now
  `[tool.soldr.pep517] bundle-bins` in `pyproject.toml`: the soldr PEP
  517 backend builds and stages `template-cli` itself, as part of the
  normal `uv build` / `uv sync` wheel build.
- **`publish.py`** wrapped `twine upload` behind a hand-flipped
  `_ENABLED` guard. This repo's release publish step will be a soldr
  OIDC-trusted-publish **mock** (proves the identity, stops before
  upload) — not yet implemented; see `docs/RELEASE.md` and
  zackees/ci.yml#6 round 5.

`ci/gates/*.py` must never call bare `cargo`/`rustc`/`maturin` — every
Rust or wheel command goes through `soldr` (`soldr cargo ...`, `soldr
wheel`, or the soldr PEP 517 backend via `uv build`/`uv sync`).

## Conventions

- Every gate file exposes a single `def run() -> int`.
- Every hook file is invoked as `uv run --no-project --script
  ci/hooks/<name>.py`.
- No multi-line shell in `.github/workflows/ci.yml` — if you can't fit
  a CI step on one line as `./ci.sh <gate>`, the logic belongs as a
  gate.
- Host checks (`sys.platform`, `os.name`) are banned in `ci/*.py`; if a
  gate needs one, it imports `template_python_rust_cmd.platforms`
  (see `ci/gates/action_surface.py` / `backend_smoke.py` for the
  pattern) rather than branching inline. `ci.toml`'s
  `[allow] platform-code` names this as one of the two allowed
  locations for host-branching code in this workspace.

## Where the dispatcher lives

`ci.py` at the repo root is the PEP 723 dispatcher; `ci.sh` is the
thin bash wrapper that calls it with `--no-project --script` (kept as
an owner-approved exception — see `ci.toml`'s `[[exceptions]]` and
https://github.com/zackees/template-python-rust-cmd/issues/15). Don't
duplicate that flag combination in CI snippets — always route through
`./ci.sh <gate>`.
