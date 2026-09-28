# Release Flow

## Status: publish is not implemented on this branch

[zackees/ci.yml#6](https://github.com/zackees/ci.yml/issues/6) round 1
removed `ci/publish.py` (the guarded `twine upload` wrapper) and
`./publish` along with it. That flow depended on `ci/build_wheel.py`'s
manual wheel-injection step, which is also gone — the soldr PEP 517
backend now bundles `template-cli` into the wheel directly
(`[tool.soldr.pep517] bundle-bins` in `pyproject.toml`). There is no
replacement publish script **yet**. The design in `ci.toml`'s
`[publish]` table (`auth = "oidc"`, `mode = "mock"`) is OIDC-trusted
publish that proves the identity and stops before any upload — no
tokens, ever. Implementing that mock is `zackees/ci.yml#6` round 5's
work. Until then, this repo has no publish path at all; don't
reintroduce a `twine`-based one to fill the gap — wait for the OIDC
mock, or ask in the tracking issue.

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

Not implemented on this branch either — no git tag, no GitHub Release,
no publish step exists yet in this repo's own automation. When the
OIDC mock lands (round 5), this section gets the real sequence:
version bump → tag → workflow-triggered release build → mock publish
proving the trusted-publisher identity → (eventually, once the fleet
is ready) a real upload. Until then, treat any release as a manual,
out-of-band process and record what you did in the PR/issue, not in
this file.
