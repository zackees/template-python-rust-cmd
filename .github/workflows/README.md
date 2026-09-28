# `.github/workflows/`

**Empty on this branch.** [zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6)
round 1 deleted the previous `ci.yml` here — it ran an 8-entry native
matrix with bare `cargo`/`maturin`, no `setup-soldr`, no
`timeout-minutes`, `continue-on-error: true` on 8 of 9 gate steps, and
queued a retired `macos-13` runner for 24h on every run (0 of 27
historical runs ever succeeded; see the round's PR body for the
evidence). This directory intentionally has no workflow file right
now rather than one patched to limp along on the old crate layout.

## What comes back, and when

A later `zackees/ci.yml#6` round adds exactly two files here, per the
issue's design (§2 "Two workflows: precheck gates everything"):

- **`ci.yml`** — the only workflow with `pull_request`
  (`opened`/`synchronize`/`reopened`/`edited`), `push: main`,
  `schedule`, and `workflow_dispatch` triggers. Its first job calls
  `ci-precheck.yml` via `workflow_call`; every other job `needs:` it.
- **`ci-precheck.yml`** — `workflow_call` only. Runs on the system
  `python3` (no tool installs), parses and validates `ci.toml` and the
  repo against it, and emits `plan.json` — the exact lanes, platforms,
  suites, and cache mode for that run. `ci.yml`'s jobs read the plan
  through `fromJSON`; none of them contain their own selection logic.

No other workflow file is added. `ci.toml` (repo root) is the contract
those two files will implement — platforms, suites, flows, tags, and
cache families are all declared there, not hand-written into YAML.

## Local equivalent, right now

```
./ci.sh all
```

runs the same gate set (`ci.py::GATE_ORDER`) a future `ci.yml` step
would call — same bytes, same order, `build` fatal the same way. See
`docs/ARCHITECTURE.md` and `CLAUDE.md` for the fuller picture, and
`ci.toml`'s `[local]` table for the planned `bosn → act` local-runner
story (also not wired up yet).

## Step shape (once workflows return)

Every gate step will have the same one-line shape — no multi-line
shell, no `shell: pwsh|cmd|powershell`:

```yaml
- name: <gate>
  id: <gate>
  run: ./ci.sh <gate>
```

Actions pinned by full commit SHA with a version comment, every job
carrying `timeout-minutes`, runner labels explicit (`ubuntu-24.04`,
never `-latest`) — see `ci.toml`'s precheck group 2 in
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) for the
full list of what the future precheck will enforce.

## Adding a workflow

Don't, on this branch, without the orchestrating round's explicit
go-ahead — see `CLAUDE.md` in this repo and
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6): only
`ci.yml` and `ci-precheck.yml` are ever allowed here.
