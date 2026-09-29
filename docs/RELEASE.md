# Release Flow

## Status: OIDC mock publish implemented (zackees/ci.yml#6 round 5)

[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) round 1
removed `ci/publish.py` (the guarded `twine upload` wrapper) and
`./publish` along with it — that flow depended on `ci/build_wheel.py`'s
manual wheel-injection step, which is also gone (the soldr PEP 517
backend bundles `template-cli` into the wheel directly via `[tool.soldr.
pep517] bundle-bins`). Round 5 implements the real replacement: `ci.toml`
`[publish]` (`auth = "oidc"`, `mode = "mock"`) OIDC-trusted publish that
proves the identity and stops before any upload — no tokens, ever, and
there is still no `ci/publish.py`: `.github/workflows/ci.yml`'s
`publish` job calls `python3 -m ci_lint publish oidc-check` directly.
Don't reintroduce a `twine`-based path — this profile is OIDC-only.

### The release graph, end to end

| Trigger | Flow | What runs |
| --- | --- | --- |
| `[release]` in a PR title | `flow.release`, `publish = "rehearsal"` | Every platform's release-profile wheel + the linux-x64 sdist, every native install smoke, `release-verify` (`ci-lint release verify`). **No** `publish` job, **no** `id-token` — a rehearsal only (issue #6 §7). |
| `workflow_dispatch` with `sha` on `main` | `flow.release`, `publish = "mock"` | Same graph, plus `release-guard` (the exact-SHA guard: HEAD must equal `inputs.sha` and be reachable from `main`, checked before any build) and `publish` (mints the OIDC token, asserts its claims — repository/ref/environment/event_name/workflow_ref/aud — prints PASS/FAIL per claim, then "mock publish: stopping before upload"; the raw token is never printed or logged). |
| `schedule` (nightly) | `flow.nightly` (`extends = "release"`) | Same release-profile wheel matrix (warms every target's caches, per issue #6 §6), but `publish = "none"` — no `release-verify`, no `publish` job. |

`release-linux-x64` builds the one platform `plan.platform_lanes`
excludes by construction (`[flow.pr]`'s own default fast-lane platform);
`platform-build`/`platform-run` build the other five at release profile
via a `--profile release` toggle, same jobs the PR/main flows already
use at dev profile.

**Known limitation** (reported upstream — see the worker report for the
round-5 PR that found it): the wheel is built directly from the working
tree, not from the sdist. `uv build`'s sdist-then-wheel-from-sdist path
(PKG-004's ideal — see "What you CAN do locally today" below) fails
reproducibly: maturin's sdist builder trims the workspace `Cargo.toml`
it writes into the sdist to the Cargo dependency graph reachable from
`[tool.maturin] manifest-path`, dropping `template-cli` (a `bundle-bins`
sibling with no Cargo dependency edge to the extension crate) even
though its files are copied in via `[tool.maturin] include`. `soldr
build --bin template-cli ... --manifest-path <extracted-sdist>/crates/
template-py/Cargo.toml` then fails with `package ID specification
'template-cli' did not match any packages`. `ci/release.py`'s `build`
subcommand works around this with two separate `uv build --sdist` /
`uv build --wheel` calls (the same direct-from-tree wheel path `ci/
fast.py`/`ci/platform_build.py` already use, just with `profile=release`
added) — both artifacts are real and independently valid, but this gives
up the stronger "wheel built from the sdist" claim until the upstream
soldr/maturin issue is fixed.

## What you CAN do locally today: build and inspect release artifacts

1. Confirm versions match in `pyproject.toml::project.version` and
   `Cargo.toml::workspace.package.version`.
2. `./ci.sh all` passes locally.
3. Build the sdist and wheel through the real backend:
   ```
   uv build
   ```
   This drives the soldr PEP 517 backend (never a direct `maturin`
   call — see `ci.toml`'s `[allow] tools`), which builds the PyO3
   `_native` extension, builds `template-cli` via `soldr build --bin`
   under the same target/profile/cache environment, and stages both
   into one wheel with a regenerated `RECORD`. No `ci/build_wheel.py`,
   no post-build zip surgery.
4. Also build the wheel **from the sdist** (proves the sdist alone —
   not just the working tree — produces a working wheel):
   ```
   uv build --wheel --sdist-fallback   # or: unpack dist/*.tar.gz and `uv build --wheel` inside it
   ```
5. Inspect the wheel with Python's `zipfile` module: confirm
   `*.data/scripts/template-cli` is present and its first bytes are an
   ELF header (`\x7fELF`) on Linux, that there is no `console_scripts`
   entry point, and that the wheel tag is `abi3` + the platform's
   manylinux/macOS/Windows tag as appropriate.
6. Install into a clean venv (not your dev `.venv` — see
   `ci.toml`'s cache/exceptions notes for where scratch venvs belong)
   and confirm `template-cli --version` runs, `shutil.which("template-cli")`
   resolves to that binary, and
   `template_python_rust_cmd._native.__file__` ends in `.abi3.so` /
   `.pyd`.

## Cross-platform wheels

Every declared platform in `ci.toml`'s `[platforms]` builds through
soldr's Linux cross-compilation (`soldr cargo build --target <triple>`
/ `soldr wheel --target <triple>`) — no native macOS/Windows Rust
toolchain needed to produce the artifact, though native install-smoke
still needs the real OS (see `ci.toml`'s `[flow.release]`). This
replaces the old per-native-runner matrix build.

## Surface validation

Before tagging, run the two action gates to confirm the composite
action contract still holds:

```
./ci.sh action_yaml
./ci.sh action_surface
```

These are fast (<5 s) and catch the typo class of regressions where
`action.yml`'s scripts (`action/*.py`) drift from the binary's real
subcommand/flag surface.

## Tagging and GitHub Releases

Still not implemented — no git tag, no GitHub Release, and the `publish`
job **never uploads anything** (it mints and asserts an OIDC token, then
stops — "mock publish: stopping before upload"). The real sequence,
once the fleet is ready for an actual upload: version bump → tag →
`workflow_dispatch` on `main` with the tagged merge commit's exact SHA →
every lane green, `release-verify` green → `publish` prints claim PASS
for every assertion → (eventually) a real trusted-publish upload. Until
then, treat any release as a manual, out-of-band process and record what
you did in the PR/issue, not in this file.

## Perf suite

`[ci-perf]` (or `flow.release`/`flow.nightly`'s `suites = "all"`) runs
the `perf` job: `ci/perf.py bench` builds a release-profile wheel,
installs it into a clean venv, times `template-cli --version` startup
and one PyO3 call (`template_python_rust_cmd.bindings.version_banner()`,
via `ci/perf_pyo3_bench.py` run by that venv's own python), and writes a
typed `BenchmarkFile` JSON. `ci/perf.py fetch-baseline` pulls the latest
successful `main`/nightly `perf-results` artifact through the REST API;
`ci-lint perf compare` reports every benchmark's delta either way and
only fails the job when `ci.toml [suites.perf].gating = true` **and** a
threshold is set (neither is true here — perf is informational).
`[ci-perf][no-test]` is the fast build+perf loop, never mergeable.
