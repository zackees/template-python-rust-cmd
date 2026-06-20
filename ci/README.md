# `ci/`

Repo automation. Two structured sub-packages plus a small set of
named release-flow scripts.

## Layout

```
ci/
├── gates/                 # workspace-state checks (run by ./ci.sh)
│   ├── __init__.py
│   ├── loc.py             # LOC budget gate (warn 1000 / fail 1500)
│   ├── fmt.py             # cargo fmt --check
│   ├── clippy.py          # cargo clippy -D warnings
│   ├── ruff.py            # ruff check + format --check
│   ├── build.py           # cargo check --workspace (FATAL in `all`)
│   ├── test.py            # cargo test + maturin develop + pytest
│   ├── action_yaml.py     # composite-action structural check
│   └── action_surface.py  # subcommand-vs-binary surface check
├── hooks/                 # agent-intent guards (run by Claude Code)
│   ├── tool_guard.py
│   ├── readme_guard.py
│   ├── loc_guard.py
│   └── check-on-start.py
├── build_wheel.py         # release-flow: stage binary + maturin build
└── publish.py             # release-flow: twine upload (guarded)
```

## Two halves: gates vs. hooks

| Concern                                | Home                       |
|----------------------------------------|----------------------------|
| Runs on every CI cycle                 | `ci/gates/*.py`            |
| Runs only during a Claude/Codex session| `ci/hooks/*.py`            |
| Workspace-wide LOC budget              | `ci/gates/loc.py`          |
| Per-edit LOC budget                    | `ci/hooks/loc_guard.py`    |
| README presence + size                 | `ci/hooks/readme_guard.py` |
| Bare cargo/uv shape ban                | `ci/hooks/tool_guard.py`   |

If a rule would fire on a `git push` from a terminal the same way it
would fire on a Claude edit, write it as a gate. If it needs to see
what tool is about to run, write it as a hook. See [zccache#835 rule 9](https://github.com/zackees/zccache/issues/835).

## Release-flow scripts

`build_wheel.py` and `publish.py` are NOT gates. They're named entry
points that opt INTO the full maturin context — see [zccache#835 rule
5](https://github.com/zackees/zccache/issues/835). The `tool_guard`
hook recognizes them by name and allows `uv run` without
`--no-project --script` from inside them.

## Conventions

- Every gate file exposes a single `def run() -> int`.
- Every hook file is invoked as `uv run --no-project --script
  ci/hooks/<name>.py`.
- No multi-line shell in `.github/workflows/ci.yml` — if you can't fit
  a CI step on one line as `./ci.sh <gate>`, the logic belongs as a
  gate.
- Release-flow scripts use shebang `#!/usr/bin/env -S uv run --script`
  with PEP 723 inline-deps; gates and hooks use `import` from the
  dispatcher's venv (no shebang needed).

## Where the dispatcher lives

`ci.py` at the repo root is the PEP 723 dispatcher; `ci.sh` is the
thin bash wrapper that calls it with `--no-project --script`. Don't
duplicate that flag combination in CI snippets — always route through
`./ci.sh <gate>`.
