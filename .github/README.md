# `.github/`

GitHub-specific metadata. Kept deliberately thin per
[zackees/zccache#835 rule 6](https://github.com/zackees/zccache/issues/835):
any future CI step is a single line — `run: ./ci.sh <gate>` or `run:
python3 ci/<script>.py ...` — never multi-line shell. The actual logic
lives in `ci/gates/*.py` so the same bytes run on a developer laptop.

## Layout

```
.github/
└── workflows/
    └── README.md      # see that file — there is no ci.yml here right now
```

## No workflow on this branch

[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) round 1
deleted the previous `.github/workflows/ci.yml`: it ran an 8-entry
native matrix with bare `cargo`/`maturin` calls, no `setup-soldr`, and
queued a retired `macos-13` runner for 24h on every single run (0 of
27 historical runs ever succeeded). Rather than patch a workflow shape
this round's crate/packaging restructure had already made stale, it
was removed outright. A later round adds it back, generated to match
`ci.toml`'s `[platforms]`/`[suites]`/`[flow.*]` declarations and gated
by a `ci-precheck.yml` (`workflow_call` only). Until then:

- `./ci.sh all` locally is the equivalent of what that workflow will
  run.
- Every push to a PR against this repo currently has **no required
  check** — this is expected and temporary, not a regression to chase
  down.

## Workflow shape (planned)

When it returns, `ci.yml` will be the **only** workflow with
`pull_request`/`push: main`/`schedule`/`workflow_dispatch` triggers.
Its first job calls `ci-precheck.yml` (stdlib `python3`, no tool
installs, fail-fast) through `workflow_call`; every other job
`needs:` it. Every `run:` step is one line — a gate name via
`./ci.sh <gate>` or a direct `python3 ci/<script>.py ...` call. See
`ci.toml` at the repo root for the exact platform/suite/tag contract
that workflow will implement, and
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) §2 for
the precheck's check groups.

## Why this folder stays intentionally small

The historic anti-pattern is multi-line shell embedded in YAML —
unlintable, untestable, only validates when CI runs. Pushing logic
into `ci/gates/<name>.py` makes each gate `import ci.gates.fmt;
ci.gates.fmt.run()`-testable from `tests/test_gates.py`. The future
workflow file only has to know which gates/suites exist, not what they
do.

## Adding a new gate (for when the workflow returns)

1. Write the gate at `ci/gates/<name>.py` with `def run() -> int`,
   using `soldr` for any Rust/wheel command.
2. Register it in `ci.py::GATE_ORDER`.
3. Once `.github/workflows/ci.yml` exists again, add a step there. Not
   before — see "No workflow on this branch" above.
