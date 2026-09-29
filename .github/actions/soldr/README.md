# `.github/actions/soldr`

The ONLY sanctioned `zackees/setup-soldr` call site in this repository.
`ci.toml`'s `[allow] setup-soldr.only-in` names this path; `ci-lint`
precheck group 4 (`TOOL-*`) rejects a direct `zackees/setup-soldr@…` step
anywhere else in `.github/workflows/**` — see
[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) §11 rule 3
("One sanctioned setup-soldr call site").

## Why a wrapper, not a direct call per job

Every lane in `ci.yml` (`fast`, `dylint`) needs `setup-soldr`, and every one
of them must pass the same three mandatory inputs
(`solo-toolchain-cache: false`, `cook-delta: false`, `save-cache: auto`) —
see `ci.toml`'s `[allow] setup-soldr.require`. Copy-pasting the call site
per job is exactly how zccache#1760 happened: a workflow edit re-enabled
`solo-toolchain-cache` on one call site while the others stayed compliant,
and nothing caught the drift until the cache footprint audit fired days
later. One wrapper makes the mandatory inputs structurally impossible to
omit — they are hardcoded in `runs.steps[0].with`, never exposed as this
action's own `inputs:`, so a caller cannot override them even by accident.

## Pinning

- `zackees/setup-soldr@c0b72703f3896ff66d4878b115365dceff3c7288` (`v0.9.81`,
  the newest tagged release as of 2026-09-28). `v0` (the major-version
  moving tag) currently resolves to the SAME commit
  (`67ed4018aca013f8388050ac9bc264244f9b742c` was an earlier `v0` snapshot;
  by the time this wrapper was written `v0.9.80` was newest and was chosen
  over pinning to a moving major tag, per `RUST-001`/`SEC-004`: every
  action reference is a full commit SHA with a version comment, never a
  branch or moving tag).
- `version: "0.9.25"` (the `soldr` binary itself) matches
  `pyproject.toml`'s `requires = ["soldr==0.9.25"]` — the PEP 517 backend's
  own pin — so the CLI used by `./ci.sh`/CI steps and the backend used by
  `uv build`/`uv sync` are the exact same Soldr release.

## Inputs

| Input | Forwards to | Used by |
|---|---|---|
| `dylint` | `dylint` | the `dylint` job: resolves the requested nightly, runs `soldr dylint prepare`, exports `SOLDR_DYLINT_SUCCESS_MARKER` / `SOLDR_DYLINT_CONFIGURED_*` |
| `dylint-toolchain` | `dylint-toolchain` | the `dylint` job: pinned to `nightly-2026-05-28` -- this workspace's auto-mapped nightly (`nightly-2026-02-28`) has no catalogued driver asset |
| `prebuild-deps` | `prebuild-deps` | the `dylint` job sets `none`: `soldr cook`'s stable-toolchain deps can't warm a nightly Dylint compile |
| `cross-target` | `cross-targets` | a cross-target Dylint or cross-build pass; exactly one triple per call |
| `ci-tests` | `ci-tests` | the `fast` job's `soldr ci-test` step: declares the linked-test-product cache exclusion |
| `prebuild-deps-flags` | `prebuild-deps-flags` | MUST match the job's actual profile — empty for dev/check/dylint, `--release` for the wheel build |
| `verify-compile-cache` | `verify-compile-cache` | set `error` only on the job proving D8 (does `dylint-driver` compile through zccache) |
| `compile-cache-stats` | `compile-cache-stats` | diagnostic verbosity |
| `cache-key-suffix` | `cache-key-suffix` | gives two jobs on the same target distinct cache identities when they must not share one key |

## Reading the Dylint success-marker contract (D4)

When `dylint: true`, `setup-soldr` exports `SOLDR_DYLINT_SUCCESS_MARKER`
(a file path) and `SOLDR_DYLINT_CONFIGURED_TOOLCHAIN` /
`_RUSTC_RELEASE` / `_RUSTC_COMMIT_HASH` as job-scoped environment
variables — they are visible to every later step in the same job, not just
this action's own steps (composite actions export via `GITHUB_ENV`). The
post step's `dylint-output-cache` save gate compares the file at
`$SOLDR_DYLINT_SUCCESS_MARKER`, trimmed, against this action's
`dylint-cache-identity` output (`<nightly>|<rustc-release>|<rustc-commit>`)
character for character. `soldr cargo dylint` / `soldr dylint prepare
--target` are expected to write that file on a successful run using the
short, `SOLDR_DYLINT_CONFIGURED_*`-supplied identity — see
`ci/dylint.py` and the `dylint` job in `ci.yml` for what happens when they
don't (ci.yml#1's short-vs-host-qualified nightly mismatch).

## What NOT to do

Do not add a second `uses: zackees/setup-soldr@…` step anywhere else in
this repository. If a lane needs a setup-soldr input this wrapper doesn't
forward, add it here as a new pass-through input — never as a parallel
call site.
